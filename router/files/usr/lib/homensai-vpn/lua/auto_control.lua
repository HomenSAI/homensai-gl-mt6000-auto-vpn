-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- auto_control.lua: auto_control.py for the Lua supervisor (2.0.0-lua-alpha2).
--
-- control.lua (lua-core, alpha1) already owns control_lock / require_control_revision; this module ports the
-- rest of auto_control.py that hv-auto needs: current_revision/revision_locked (the RAM fence that Stop rotates),
-- effective_intent, valid_stop, action_context, manual_action_source, normalize_request_source and the
-- native_switch.stop_latch. UI entry points (start/stop/return_request/public_status) stay with the monitor.
-- File formats are the Python ones: auto-control-revision.json = {"revision":"<32 hex>"} exactly.
-- Everything external goes through env.run (runner.lua on the router, fakes in tests): run.fs.read,
-- run.fs.write_atomic, run.lock(fn,directory), run.require_revision(expected), run.wall().
local canon=require('canon')

local M={}
local NULL=canon.null

local Refused={}
Refused.__index=Refused
Refused.__tostring=function(e) return e.code end
M.Refused=Refused
function M.refuse(code) error(setmetatable({code=code},Refused),0) end
function M.is_refused(e) return type(e)=='table' and type(e.code)=='string' end  -- any coded refusal of the core

function M.isnone(v) return v==nil or v==NULL end
local isnone=M.isnone
function M.num(v) return canon.number(v) end
local num=M.num
function M.finite(v)
  local x=num(v)
  return x~=nil and x==x and x~=math.huge and x~=-math.huge
end
local finite=M.finite
function M.hex(v,n) return type(v)=='string' and #v==n and string.find(v,'^[a-f0-9]+$')~=nil end
function M.code_ok(v) return type(v)=='string' and #v<=96 and string.find(v,'^[A-Z][A-Z0-9_-]*$')~=nil end

-- agent.read_json(path, default): decoded value (canon types), default when the file is missing; a parse
-- error is raised (the Python ValueError).
-- status.json (the monitor's observation, read-only here, renamed into place on every write) is decoded once
-- per file version: the supervisor reads it several times per pass and a pure-Lua decode is not free.
local resident={}
-- decode_resident(path, text, key): the decoded value of this version of a resident file (status.json), shared
-- by read_json() and backend.status(): one pure-Lua decode per monitor write instead of one per reader. The
-- text decides (Lua strings are interned, so an unchanged file costs a pointer comparison); the file key only
-- lets read_json() skip reading an unchanged file.
-- The only top-level fields of the monitor's status.json that the supervisor reads (failure_diagnosis,
-- committed_recovery_decision, the pair/manual sample streaks; the same keys as the Python supervisor). The rest
-- (accounting, histories, events, speed tests: ~85 % of the file) is skipped without being built.
M.STATUS_KEYS={time=true,error=true,profiles=true,samples=true,vendor_observation=true,uplink_observation=true,
  observation_valid_for=true}
function M.decode_resident(path,text,key)
  local row=resident[path]
  if row and row.text==text then
    if key then row.key=key end
    return row.value
  end
  local value
  if string.sub(path,-12)=='/status.json' then value=canon.decode_keys(text,M.STATUS_KEYS)
  else value=canon.decode(text) end
  resident[path]={key=key,text=text,value=value}
  return value
end
function M.read_json(run,path,default)
  local keyfn=run.fs.key
  local key=nil
  if keyfn and string.sub(path,-12)=='/status.json' then
    key=keyfn(path)
    if key=='absent' then return default end
    local row=resident[path]
    if key and row and row.key==key then return row.value end
  end
  local text=run.fs.read(path)
  if text==nil then return default end
  if #text>4*1024*1024 then error('oversize state',0) end
  if key then return M.decode_resident(path,text,key) end
  return canon.decode(text)
end
function M.write_json(run,path,value) run.fs.write_atomic(path,canon.encode(value)) end
-- read_json that turns any read/parse error into `default` (Python: `except (OSError,ValueError): row={}`).
function M.read_json_safe(run,path,default)
  local ok,value=pcall(M.read_json,run,path,default)
  if ok then return value end
  return default
end

function M.uuid_hex()
  local f=io.open('/proc/sys/kernel/random/uuid','r')
  local id=f and f:read('*l') or nil
  if f then f:close() end
  id=id and string.gsub(id,'-','') or nil
  if not id or #id~=32 then
    id=string.format('%08x%08x%08x%08x',math.random(0,0x7fffffff),math.random(0,0x7fffffff),math.random(0,0x7fffffff),math.random(0,0x7fffffff))
  end
  return id
end

function M.normalize_request_source(value)
  if value=='manual' or value=='test' or value=='programmatic' then return value end
  return 'unknown'
end

-- action_context(runtime,persist,now): the latest well-formed start/stop record, as the Python.
function M.action_context(env,now)
  local run=env.run
  local rows={{env.runtime..'/auto-control.json','time','start'},{env.runtime..'/pair-auto-control.json','time','start'},
              {env.persist..'/native-stop.json','requested','stop'}}
  local best=nil
  for _,spec in ipairs(rows) do
    local ok,row=pcall(M.read_json,run,spec[1],canon.object({}))
    if ok and canon.is_object(row) then
      local action=spec[3]
      local skip=false
      if action=='start' and row.mode~='on' then
        if string.find(spec[1],'pair%-auto%-control%.json$') and row.mode=='off' then action='stop' else skip=true end
      end
      if not skip then
        local epoch=num(row[spec[2]])
        if epoch and finite(epoch) and epoch>0 and epoch<=now then
          if not best or epoch>best.control_time then
            best={control_action=action,control_source=M.normalize_request_source(row.request_source),control_time=epoch}
          end
        end
      end
    end
  end
  return best or {}
end

function M.manual_action_source(env,value,now)
  for _,name in ipairs({'pair-manual-control.json','manual-control.json'}) do
    local ok,row=pcall(M.read_json,env.run,env.runtime..'/'..name,canon.object({}))
    if ok and canon.is_object(row) and (row.state=='CLAIMED' or row.state=='APPLYING' or row.state=='WAIT-CLIENT') then
      local updated=num(row.updated~=nil and row.updated or row.updated_at)
      if updated and now-90<=updated and updated<=now then
        local pair
        if name=='pair-manual-control.json' then pair=row.selection
        else pair=canon.object({source=row.source_id,target=row.target_id}) end
        if canon.is_object(pair) and type(value.source)=='string' and type(value.target)=='string'
           and pair.source==value.source and pair.target==value.target then
          return M.normalize_request_source(row.request_source)
        end
      end
    end
  end
  return 'unknown'
end

function M.valid_stop(record)
  if not canon.is_object(record) then return false end
  if next(record)==nil then return true end
  local epoch=num(record.requested)
  if not epoch or not finite(epoch) or epoch<=0 then return false end
  if record.all_trials~=nil and type(record.all_trials)~='boolean' then return false end
  if record.control_revision_failed~=nil and type(record.control_revision_failed)~='boolean' then return false end
  return record.all_trials==true or (type(record.trial)=='string' and record.trial~='')
end

-- revision_locked(directory, rotate): caller holds the control lock.
function M.revision_locked(env,rotate)
  local path=env.runtime..'/auto-control-revision.json'
  local record=M.read_json_safe(env.run,path,canon.object({}))
  local revision=nil
  if canon.is_object(record) then
    local keys=0
    for _ in pairs(record) do keys=keys+1 end
    if keys==1 and record.revision~=nil then revision=record.revision end
  end
  if rotate or not M.hex(revision,32) then
    revision=M.uuid_hex()
    M.write_json(env.run,path,canon.object({revision=revision}))
  end
  return revision
end

function M.current_revision(env,rotate)
  return env.run.lock(function() return M.revision_locked(env,rotate) end,env.runtime)
end

-- native_switch.stop_latch(trial): rotate the revision and write the durable stop under the UI lock.
function M.stop_latch(env,trial)
  env.run.lock(function()
    local rok,rerr=pcall(M.revision_locked,env,true)
    local old=M.read_json_safe(env.run,env.persist..'/native-stop.json',canon.object({}))
    local previous=canon.is_object(old) and num(old.requested) or 0
    local now=env.run.wall()
    if previous and finite(previous) then now=math.max(now,previous) end
    local record=canon.object({requested=canon.float(now),trial=trial==nil and NULL or trial,all_trials=true})
    if not rok then record.control_revision_failed=true end
    M.write_json(env.run,env.persist..'/native-stop.json',record)
    if not rok then error(rerr,0) end
  end,env.runtime)
end

-- effective_intent(settings, stopped, request, now) -> enabled, stop_latched
function M.effective_intent(settings,stopped,request,now,deadline_fn)
  if not (canon.is_object(settings) and canon.is_object(stopped) and canon.is_object(request)) then return false,true end
  if not M.valid_stop(stopped) then return false,true end
  if stopped.control_revision_failed==true then return false,true end
  local enabled=settings.native_enabled=='1'
  local epoch=num(stopped.requested) or 0
  if stopped.all_trials==true then
    local stamp=num(request.time)
    if not (finite(epoch) and epoch>0 and request.mode=='on' and stamp and finite(stamp) and epoch<stamp and stamp<=now
            and type(request.trial)=='string' and request.trial~='' and request.trial==settings.native_trial) then
      return false,true
    end
  end
  local stop_latched=next(stopped)~=nil and stopped.trial==settings.native_trial
  if stop_latched and not (finite(epoch) and epoch>0) then return false,true end
  if next(request)==nil or request.trial~=settings.native_trial then return enabled,stop_latched end
  local ok,until_=pcall(deadline_fn,settings.native_until)
  if not ok then return false,true end
  local r_until,r_time=num(request["until"]),num(request.time)
  local valid=request.trial==settings.native_trial and r_until and finite(r_until) and r_until==until_
    and r_time and finite(r_time) and 0<r_time and r_time<=now and (request.mode=='on' or request.mode=='off')
  if not valid then return false,true end
  if request.mode=='off' or now>=r_until then return false,true end
  if stopped.trial==request.trial and (num(stopped.requested) or 0)>=r_time then return false,true end
  return true,false
end

-- A second flock-based lock on any file of ours (native-history.lock): the same technique as control.lua -
-- busybox flock(1) on the descriptor this process keeps open; released when the file closes.
function M.flock_file(path,fn)
  if not (type(path)=='string' and string.find(path,'^/[A-Za-z0-9_./-]+$') and not string.find(path,'..',1,true)) then
    M.refuse('HISTORY-PATH')
  end
  local file=io.open(path,'a')
  if not file then M.refuse('HISTORY-PATH') end
  local p=io.popen('for f in /proc/$$/fd/*; do if [ "$f" -ef '..path..' ]; then flock -x "${f##*/}" && echo ok; exit 0; fi; done; exit 97','r')
  local out=p and p:read('*a') or ''
  if p then p:close() end
  if out~='ok\n' then file:close();M.refuse('HISTORY-PATH') end
  local results={pcall(fn)}
  file:close()
  if not results[1] then error(results[2],0) end
  return unpack(results,2)
end

return M
