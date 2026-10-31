-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- control_request.lua: the page's Start / Stop / failure-test buttons answered by the Lua monitor without
-- starting Python (plan item 4, after manual_request.lua). Only the request files are written here, exactly
-- as agent.control_reply / auto_control / pair_auto.request / fault_control write them; the supervisor (Lua or
-- Python) reads them and does the work. Same order of checks, same codes, same file formats (canon.encode:
-- byte-exact JSON with float times; checksums = sha256 of sort_keys JSON like agent.checksum).
--
--   native_start  control_reply argument shape -> auto_control.start (revision under the control lock, speed
--                 pause, router policy + journal phase, preparation blocker, preparation snapshot) ->
--                 pair_auto.request (under the control lock) -> QUEUED pair intent. Auto is started only by an
--                 explicit owner click with the current control revision; the terms/readiness preflight stays
--                 with the supervisor (pair_auto.preflight), as in Python.
--   native_stop   auto_control.stop: router trial read, then under the control lock: revision rotated, pair
--                 intent 'off', pending manual click cancelled, durable stop latch native-stop.json.
--   fault_cancel  fault_control.cancel: cancel marker, nft table cleanup (own nonce only), result + history.
--   fault_start   only the refusals decided under the first control lock (FAULT-CONTROL-CHANGED,
--                 FAULT-STATE-CORRUPT, FAULT-ALREADY-ACTIVE); a start that would proceed goes to agent.py,
--                 which runs the kernel attestation, the nft rule and its watchdog worker.
--
-- FALLBACK (agent.py answers with the same request bytes) whenever this module cannot decide without waiting
-- or without a part that is not ported, and always BEFORE it has written anything:
--   a held control lock (never waited for in the event loop), a speed-test pause file, a failed router policy
--   read, preparation repairs that Auto would run first (auto_prepare), the legacy (non-pair) trial mode,
--   a HELD session that may be re-adopted (release_session), Stop while a failure-test intent exists (Stop then
--   also cleans the test up), any unexpected read error. fault_cancel is idempotent: it may fall back between
--   its locked steps (agent.py's cancel repeats the same writes with the same nonce).
local canon=require('canon')

local M={}
M.FALLBACK=setmetatable({},{__tostring=function() return 'FALLBACK' end})
M.MODE='router-probed-ipv4'
M.FAULT_TABLE='homensai_vpn_fault'
M.FAULT_MARKER='homensai-owned-fault-'
local NULL=canon.null
local START_BUSY={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,COMMITTED=true,['HELD-ON-RESERVE']=true,RESTORING=true,['RELEASE-PENDING']=true}
local TERMINAL={STOPPED=true,FAILED=true}
local READOPT={['PAIR-EXTERNAL-NETWORK-CHANGE']=true,['PAIR-EXTERNAL-CONFIG-CHANGE']=true,['PAIR-EXTERNAL-POLICY-CHANGE']=true,['SOURCE-ORDER-MISMATCH']=true}
-- preparation_control.AUTO_ACTIONS: a failed check with one of these codes is repaired by Start (Python).
M.AUTO_ACTIONS={['PREP-STOCK-VPN-BOOT']=true,['PREP-SOURCE-AUTOSTART']=true,['PREP-TARGET-AUTOSTART']=true,['PREP-WGCLIENT1-AUTOSTART']=true,
  ['PREP-OVPNCLIENT1-AUTOSTART']=true,['PREP-HNAT-CONFIG']=true,['PREP-SFE-BOOT']=true}

local FALL={}            -- unwinds to M.FALLBACK
local FaultError={}      -- fault_control.FaultError
FaultError.__index=FaultError
local function fallback() error(FALL,0) end
local function fault(code) error(setmetatable({code=code},FaultError),0) end
local function is_fault(e) return type(e)=='table' and getmetatable(e)==FaultError end

local function none(v) return v==nil or v==NULL end
local function hex(v,n) return type(v)=='string' and #v==n and string.find(v,'^[a-f0-9]+$')~=nil end
local function finite(v) local x=canon.number(v);return x~=nil and x==x and x~=math.huge and x~=-math.huge end
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local function only(arguments,allowed)
  for key in pairs(arguments) do if not allowed[key] then return false end end
  return true
end
-- Python truthiness of a decoded JSON value
local function truthy(v)
  if none(v) or v==false or v=='' then return false end
  local n=canon.number(v)
  if n~=nil then return n~=0 end
  if type(v)=='table' then return next(v)~=nil end
  return true
end
-- Python == of two decoded JSON scalars/tables (None, bool, numbers, strings)
local function same(a,b)
  if none(a) or none(b) then return none(a) and none(b) end
  if type(a)=='boolean' or type(b)=='boolean' then return a==b end
  local x,y=canon.number(a),canon.number(b)
  if x~=nil or y~=nil then return x~=nil and y~=nil and x==y end
  if type(a)=='table' or type(b)=='table' then return type(a)==type(b) and canon.encode(a)==canon.encode(b) end
  return a==b
end
M.same=same

function M.normalize_request_source(v)
  if v=='manual' or v=='test' or v=='programmatic' then return v end
  return 'unknown'
end
local label=M.normalize_request_source

-- deps.read raises on a symlink/oversize file (agent.read_json); nil text = missing = default
local function read_json(deps,path,default)
  local text=deps.read(path)
  if text==nil then return default end
  return canon.decode(text)
end
local function read_json_safe(deps,path,default)
  local ok,value=pcall(read_json,deps,path,default)
  if ok then return value end
  return default
end
local function write_json(deps,path,value) deps.write(path,canon.encode(value)) end

local function uuid_hex(deps)
  local text=deps.read('/proc/sys/kernel/random/uuid')
  local id=text and string.gsub(text,'[^0-9a-f]','') or ''
  if not hex(id,32) then error('uuid unavailable',0) end
  return id
end
M.uuid_hex=uuid_hex

-- auto_control.revision_locked(directory, rotate): caller holds the control lock
function M.revision_locked(deps,rotate)
  local path=deps.runtime..'/auto-control-revision.json'
  local record=read_json_safe(deps,path,canon.object())
  local revision=nil
  if canon.is_object(record) and count(record)==1 and record.revision~=nil then revision=record.revision end
  if rotate or not hex(revision,32) then
    revision=uuid_hex(deps)
    write_json(deps,path,canon.object({revision=revision}))
  end
  return revision
end

-- try-lock: busy -> FALLBACK (agent.py waits for it); the body's results otherwise
local function locked(deps,fn)
  local results={deps.try_lock(fn)}
  if not results[1] then fallback() end
  return unpack(results,2)
end

-- pcall wrapper: FALL -> M.FALLBACK; any other unexpected error -> M.FALLBACK as well (nothing was written
-- yet on these paths, agent.py then gives its exact answer)
local function guarded(fn)
  local ok,reply=pcall(fn)
  if ok then return reply end
  return M.FALLBACK
end

local function start_refused(code,extra)
  local reply=canon.object({accepted=false,blockers=canon.array({code})})
  for k,v in pairs(extra or {}) do reply[k]=v end
  return reply
end

------------------------------------------------------------------------------------------------------
-- native_start
------------------------------------------------------------------------------------------------------
-- deps: read, write, exists, now, try_lock, runtime, persist, native_policy() -> text|nil, journal() -> journal
--   (raises on an integrity failure), auto_blocker() -> code|nil, preparation(settings) -> snapshot,
--   read_state() -> pair state (raises), intent() -> pair intent (raises)
function M.start(deps,arguments)
  if arguments.control_revision==nil or not only(arguments,{control_revision=true,request_source=true}) then
    return start_refused('CONTROL-REVISION-STALE')
  end
  return guarded(function()
    local revision=arguments.control_revision
    local source=label(arguments.request_source)
    if not hex(revision,32) then return start_refused('CONTROL-REVISION-STALE') end
    local runtime=deps.runtime
    -- auto_control.start: the first locked check
    local first=locked(deps,function()
      if revision~=M.revision_locked(deps) then return start_refused('CONTROL-REVISION-STALE') end
      if deps.exists(runtime..'/speed-pause.json') then fallback() end  -- speed_pause.public(): agent.py decides
      return nil
    end)
    if first then return first end
    -- backend.policy() + journal_read(), outside the lock
    local text=deps.native_policy()
    if text==nil then fallback() end       -- CalledProcessError in Python: agent.py answers
    local ok,policy=pcall(canon.decode,text)
    if not ok then fallback() end
    local settings=canon.is_object(policy) and policy.settings or nil
    if not canon.is_object(settings) then return start_refused('START-STATE-UNVERIFIED') end
    local jok,journal=pcall(deps.journal)
    if not jok or not canon.is_object(journal) then return start_refused('JOURNAL-INTEGRITY-FAILED') end
    if START_BUSY[journal.phase] then return start_refused('TRANSACTION-IN-PROGRESS') end
    local blocker=deps.auto_blocker()
    if blocker then return start_refused(blocker) end
    -- auto_prepare: anything Start would repair first stays with agent.py
    local snapshot=deps.preparation(settings)
    for _,row in ipairs(snapshot and snapshot.checks or {}) do
      if row.state~='pass' and M.AUTO_ACTIONS[row.code] then fallback() end
    end
    if settings.pair_auto_mode~=M.MODE then fallback() end  -- the legacy certified-trial Start stays in Python
    -- pair_auto.request
    return locked(deps,function()
      if deps.exists(runtime..'/speed-pause.json') then fallback() end
      if revision~=M.revision_locked(deps) then return start_refused('CONTROL-REVISION-STALE') end
      local rok,state,old=pcall(function() return deps.read_state(),deps.intent() end)
      if not rok or not canon.is_object(state) or not canon.is_object(old) then return start_refused('PAIR-STATE-UNVERIFIED') end
      if next(state)~=nil and not TERMINAL[state.phase]
         and not (old.mode=='on' and old.revision==revision and old.id==state.id) then
        if state.phase=='HELD' and READOPT[state.recovery_error] then fallback() end  -- release_session: agent.py
        return start_refused('PAIR-RECOVERY-REQUIRED')
      end
      if old.mode=='on' and old.revision==revision then
        return canon.object({accepted=true,queued=true,already_requested=true})
      end
      local id=uuid_hex(deps)
      write_json(deps,runtime..'/pair-auto-control.json',canon.object({mode='on',revision=revision,time=canon.float(deps.now()),
        id=id,request_source=source}))
      -- Owner decision 31.10.2026: the owner's own Start is remembered on flash (boot_resume.lua)
      if source=='manual' then pcall(deps.write,deps.persist..'/'..require('boot_resume').MARKER,require('boot_resume').marker(deps.now())) end
      return canon.object({accepted=true,queued=true,mode='continuous-pair',proof_scope=M.MODE,external_lan_verified=false})
    end)
  end)
end

------------------------------------------------------------------------------------------------------
-- native_stop
------------------------------------------------------------------------------------------------------
-- deps: read, write, exists, now, try_lock, runtime, persist, native_policy(), terminalize() (pair_manual.
--   terminalize_pending_locked('CANCELLED','CONTROL-REVISION-STALE'); errors are ignored, as in Python)
function M.stop(deps,arguments)
  if not only(arguments,{request_source=true}) then return canon.object({error='RPC-UNEXPECTED-ARGS'}) end
  local runtime,persist=deps.runtime,deps.persist
  local ok,reply=pcall(function()
    -- agent.control_reply also cancels a failure test after the stop: that pair of steps stays with agent.py
    if deps.exists(runtime..'/fault-intent.json') then fallback() end
    -- the router trial, read before the lock; any doubt latches all trials
    local trial,unverified=nil,false
    local tok=pcall(function()
      local text=deps.native_policy()
      if text==nil then error('policy',0) end
      local internal=canon.decode(text)
      if not canon.is_object(internal) then error('policy',0) end
      local settings=internal.settings
      if settings==nil then settings=canon.object() end
      if not canon.is_object(settings) then error('policy',0) end
      local value=settings.native_trial
      if not none(value) and type(value)~='string' then error('invalid trial',0) end
      trial=(not none(value)) and value or nil
    end)
    if not tok then trial=nil;unverified=true end
    return locked(deps,function()
      local sok,result=pcall(function()
        local now=deps.now()
        local rok,rerr=pcall(M.revision_locked,deps,true)
        local revision_error=(not rok) and (rerr or 'revision') or nil
        if deps.exists(runtime..'/pair-auto-control.json') then
          local marker_row=read_json(deps,runtime..'/auto-control-revision.json',canon.object())
          if not canon.is_object(marker_row) then error('marker',0) end
          local marker=marker_row.revision
          if marker==nil then marker='unverified' end
          write_json(deps,runtime..'/pair-auto-control.json',canon.object({mode='off',revision=marker,time=canon.float(now),
            request_source=label(arguments.request_source)}))
        end
        pcall(deps.terminalize)
        local request=read_json_safe(deps,runtime..'/auto-control.json',canon.object())
        if not canon.is_object(request) then request=canon.object() end
        if unverified then trial=request.trial;if trial==NULL then trial=nil end end
        local changed=not unverified and not none(request.trial) and not same(request.trial,trial)
        local old=read_json_safe(deps,persist..'/native-stop.json',canon.object())
        if not canon.is_object(old) then old=canon.object() end
        local extra=unverified and {settings_unverified=true} or {}
        local previous=old.requested
        local requested=request.time
        if requested==nil then requested=0 end
        requested=finite(requested) and canon.number(requested) or math.huge
        local needs_global=unverified or not truthy(trial) or changed
        if revision_error==nil and not truthy(old.control_revision_failed) and next(old)~=nil
           and finite(previous) and canon.number(previous)>0
           and (old.all_trials==true or (not needs_global and same(old.trial,trial)))
           and canon.number(previous)>=requested then
          local reply=canon.object({queued=true,already_requested=true})
          for k,v in pairs(extra) do reply[k]=v end
          return reply
        end
        local floor=finite(previous) and previous or 0
        local at=(canon.number(floor)>now) and floor or canon.float(now)
        local record=canon.object({requested=at,trial=trial==nil and NULL or trial,request_source=label(arguments.request_source)})
        if revision_error~=nil then record.control_revision_failed=true end
        if needs_global or revision_error~=nil then record.all_trials=true end
        write_json(deps,persist..'/native-stop.json',record)
        if revision_error~=nil then error(revision_error,0) end
        local reply=canon.object({queued=true})
        for k,v in pairs(extra) do reply[k]=v end
        return reply
      end)
      if sok then return result end
      return canon.object({queued=false,code='STOP-UNCONFIRMED'})
    end)
  end)
  if ok then return reply end
  return M.FALLBACK
end

------------------------------------------------------------------------------------------------------
-- failure test (fault_control)
------------------------------------------------------------------------------------------------------
-- fault_control.load(): {} without an intent; FaultError FAULT-STATE-CORRUPT for a damaged one
function M.fault_load(deps)
  local envelope=read_json(deps,deps.runtime..'/fault-intent.json',canon.object())
  if not truthy(envelope) then return canon.object() end
  if not canon.is_object(envelope) then fallback() end  -- AttributeError in Python
  local data=envelope.data
  if not canon.is_object(data) or envelope.sha256~=canon.digest(data) then fault('FAULT-STATE-CORRUPT') end
  local nonce=data.nonce
  if nonce~=nil and type(nonce)~='string' then fallback() end  -- str(non-string): left to agent.py
  if not hex(nonce,32) then fault('FAULT-STATE-CORRUPT') end
  return data
end

-- fault_control.history()/event(): the bounded checksummed fault history on flash
function M.fault_event(deps,code,intent)
  local ok=pcall(function()
    local path=deps.persist..'/fault-history.json'
    local rows
    local envelope=read_json(deps,path,canon.object())
    if not truthy(envelope) then rows=canon.array()
    else
      if not canon.is_object(envelope) then error('history',0) end
      local data=envelope.data
      if not canon.is_array(data) or #data>100 or envelope.sha256~=canon.digest(data) then error('FAULT-HISTORY-CORRUPT',0) end
      rows=data
    end
    local profiles=intent.profiles
    if profiles==nil then profiles=canon.array() end
    if not canon.is_array(profiles) then error('profiles',0) end
    local first=canon.array();for i=1,math.min(8,#profiles) do first[i]=profiles[i] end
    local scope=intent.scope;if scope==nil then scope='profile' end
    local duration=intent.duration;if duration==nil then duration=NULL end
    rows[#rows+1]=canon.object({time=canon.float(deps.now()),code=code,profiles=first,scope=scope,duration=duration})
    local kept=canon.array();for i=math.max(1,#rows-99),#rows do kept[#kept+1]=rows[i] end
    write_json(deps,path,canon.object({data=kept,sha256=canon.digest(kept)}))
  end)
  if ok then return NULL end
  return 'FAULT-HISTORY-UNAVAILABLE'
end

-- Nft.contents(): table text, nil when absent; FAULT-NFT-QUERY-FAILED on another nft error
local function nft_contents(deps)
  local rc,text=deps.nft('list')
  if rc==0 then return text or '' end
  if rc==1 then return nil end
  if rc==124 or rc>=128 then fallback() end  -- TimeoutExpired in Python (not a FaultError): agent.py answers
  fault('FAULT-NFT-QUERY-FAILED')
end

-- Nft.cleanup(nonce): delete only our own table, under the lock, and confirm it is gone
local function nft_cleanup(deps,nonce)
  local text=nft_contents(deps)
  if text==nil then return true end
  if not string.find(text,M.FAULT_MARKER..nonce,1,true) then fault('FAULT-FOREIGN-TABLE') end
  local rc=locked(deps,function()
    local current=M.fault_load(deps)
    if next(current)==nil or current.nonce~=nonce then fault('FAULT-CLAIM-STALE') end
    return (deps.nft('delete'))
  end)
  if rc==124 or rc>=128 then fault('FAULT-COMMAND-UNCONFIRMED') end
  if rc~=0 then fault('FAULT-TIMEOUT-RULE-FAILED') end
  if nft_contents(deps)~=nil then fault('FAULT-CLEANUP-UNCONFIRMED') end
  return true
end

-- deps: read, write, now, try_lock, runtime, persist, nft(action 'list'|'delete') -> exit code, text
function M.fault_cancel(deps,arguments)
  if next(arguments)~=nil then return canon.object({queued=false,code='FAULT-FIELDS'}) end
  local ok,reply=pcall(function()
    local value=locked(deps,function()
      local v=M.fault_load(deps)
      if next(v)==nil then return v end
      write_json(deps,deps.runtime..'/fault-cancel.json',canon.object({nonce=v.nonce}))
      return v
    end)
    if next(value)==nil then return canon.object({queued=false,code='FAULT-NOT-ACTIVE'}) end
    nft_cleanup(deps,value.nonce)
    return locked(deps,function()
      local current=M.fault_load(deps)
      if next(current)==nil or current.nonce~=value.nonce then return canon.object({queued=true,cleaned=true,code='FAULT-CANCELLED'}) end
      write_json(deps,deps.runtime..'/fault-result.json',canon.object({nonce=value.nonce,cleaned=true,code='FAULT-CANCELLED',time=canon.float(deps.now())}))
      local history_error=M.fault_event(deps,'FAULT-CANCELLED',value)
      return canon.object({queued=true,cleaned=true,code='FAULT-CANCELLED',history_error=history_error})
    end)
  end)
  if ok then return reply end
  if is_fault(reply) then return canon.object({accepted=false,code=reply.code}) end
  return M.FALLBACK  -- held lock, timeout, read error: agent.py's cancel repeats the same idempotent steps
end

-- deps: read, try_lock, runtime, clock() (monotonic, the clock of the intent's monotonic_until)
function M.fault_start(deps,arguments)
  local ok,reply=pcall(function()
    return locked(deps,function()
      local marker=read_json(deps,deps.runtime..'/auto-control-revision.json',canon.object())
      if not canon.is_object(marker) then fallback() end
      local revision=count(marker)==1 and marker.revision or nil
      -- require_revision: the file read again
      local value=read_json(deps,deps.runtime..'/auto-control-revision.json',canon.object())
      if not hex(revision,32) or not canon.is_object(value) or count(value)~=1 or value.revision~=revision then fault('FAULT-CONTROL-CHANGED') end
      local old=M.fault_load(deps)
      local result=read_json(deps,deps.runtime..'/fault-result.json',canon.object())
      local cleaned=next(old)~=nil and canon.is_object(result) and result.nonce==old.nonce and result.cleaned==true
      if next(old)~=nil and not cleaned then
        local mono=deps.clock()
        local until_=old.monotonic_until
        if until_==nil then return canon.object({accepted=false,code='FAULT-ALREADY-ACTIVE'}) end  -- default mono+1
        if canon.number(until_)==nil then fallback() end
        if mono<canon.number(until_) then return canon.object({accepted=false,code='FAULT-ALREADY-ACTIVE'}) end
      end
      fallback()  -- the start itself (attestation, nft rule, watchdog) runs in agent.py
    end)
  end)
  if ok then return reply end
  if is_fault(reply) then return canon.object({accepted=false,code=reply.code}) end
  return M.FALLBACK
end

return M
