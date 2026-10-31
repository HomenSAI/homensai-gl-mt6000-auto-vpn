-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- instant_switch.lua: the write stage of native_switch.instant_manual in Lua (2.0.0-lua-alpha1).
--
--   lua instant_switch.lua <primary|reserve> [request.json]   one switch, one JSON line, exit 0 / 2
--   lua instant_switch.lua --dry-run                          read-only measurement, never writes
--
-- The Python supervisor keeps every decision and check before the write (light gate, diagnostic,
-- attestation before, pair_policy.transition, lease) and builds the APPLYING journal exactly as
-- instant_manual does; it writes /var/run/homensai-vpn/instant-request.json:
--   {"direction":"primary|reserve","control_revision":"<32 hex>","journal":{...APPLYING...},
--    "names":{"<section identity>":"<uci section name>",...},"tunnel_order":["<first>","<second>"]}
-- and runs this file in place of the reorder/apply/verify/journal part. Here, in order:
--   1. the request is checked; the current journal must be settled (light_gate rule);
--   2. journal APPLYING (fenced: control lock + control revision, like instant_manual);
--   3. uci reorder + one commit in-process with libuci, then gl_process_vpn aligned to the first rule
--      (process_policy.synchronization_script) - both fenced - and read back by content;
--   4. iptables-save once -> plan; iptables-restore --noflush through a pipe (fenced); read once more ->
--      verify + attest subset; conntrack -D of the old mark (unfenced, as in Python);
--   5. journal HELD-ON-RESERVE (fenced).
-- Failure before any write: journal ROLLED-BACK / FAILED-BEFORE-APPLY, as Python. After a write: the
-- journal keeps APPLYING with failure_code and the result says rollback_required; the Python supervisor
-- runs rollback_counted() exactly as after its own failure. Unsupported layouts are reported with
-- fallback="vendor-rebuild": Python decides (its apply() would run rtp2.sh there).
-- Every external call goes through the runner table (runner.lua on the router, fakes in tests).
local here=(arg and arg[0] and string.match(arg[0],'^(.*)/[^/]*$'))
if here then package.path=here..'/?.lua;'..package.path end

local canon=require('canon')
local fp=require('fast_policy')
local kernel=require('kernel')
local journal=require('journal')

local M={}
M.REQUEST='/var/run/homensai-vpn/instant-request.json'

local Refused={}
Refused.__index=Refused
Refused.__tostring=function(e) return e.code end
M.Refused=Refused
local function refuse(code) error(setmetatable({code=code},Refused),0) end
local function code_of(err)
  local code=type(err)=='table' and err.code or nil
  if type(code)=='string' and #code<=96 and string.find(code,'^[A-Z0-9_-]+$') then return code end
  return 'NATIVE-SYSTEM-001'
end

------------------------------------------------------------------------------------------------------
-- UCI order (Linux.reorder)
------------------------------------------------------------------------------------------------------
-- The `uci reorder` moves Linux.reorder issues to turn `current` into `desired`: {id=, index=<0-based>}.
function M.reorder_moves(current,desired)
  local cset,dset,ccount,dcount={},{},0,0
  for _,x in ipairs(current) do if not cset[x] then cset[x]=true;ccount=ccount+1 end end
  for _,x in ipairs(desired) do if not dset[x] then dset[x]=true;dcount=dcount+1 end end
  local same=ccount==dcount
  for x in pairs(dset) do if not cset[x] then same=false end end
  if #desired~=#current or not same then refuse('POLICY-IDENTITY-CHANGED') end
  local expected,moves={},{}
  for i=1,#current do expected[i]=current[i] end
  for index,identifier in ipairs(desired) do
    if expected[index]~=identifier then
      moves[#moves+1]={id=identifier,index=index-1}
      for k=1,#expected do if expected[k]==identifier then table.remove(expected,k);break end end
      table.insert(expected,index,identifier)
    end
  end
  return moves,expected
end

local function safe_section(name)
  return type(name)=='string' and #name>=1 and #name<=64 and string.find(name,'^[A-Za-z0-9_]+$')~=nil
end

-- Section names of route_policy in file order: libuci, else `uci -X show` (names of anonymous sections).
function M.section_names(run,cursor)
  local names={}
  if cursor then
    cursor:foreach('route_policy',nil,function(s) names[#names+1]=s['.name'] end)
  else
    for _,line in ipairs(fp.splitlines(kernel.decode(run.capture('uci_names')))) do
      local name=string.match(line,'^route_policy%.([^.=]+)=[^=]*$')
      if name then names[#names+1]=name end
    end
  end
  return names
end

-- Apply the moves: one libuci session and one commit (Python: one `uci` process per move + commit).
function M.uci_apply(run,cursor,moves,names)
  local resolved={}
  for i,move in ipairs(moves) do
    local section=names[move.id]
    if not safe_section(section) then refuse('UNSAFE-SECTION') end
    resolved[i]={section,move.index}
  end
  if #resolved==0 then return 0 end
  if cursor then
    for _,item in ipairs(resolved) do
      if not cursor:reorder('route_policy',item[1],item[2]) then refuse('POLICY-REORDER-UNVERIFIED') end
    end
    if not cursor:commit('route_policy') then refuse('POLICY-REORDER-UNVERIFIED') end
  else
    local lines={}
    for i,item in ipairs(resolved) do lines[i]='reorder route_policy.'..item[1]..'='..string.format('%d',item[2]) end
    lines[#lines+1]='commit route_policy'
    run.uci_batch(lines)
  end
  return #resolved
end

------------------------------------------------------------------------------------------------------
-- gl_process_vpn follows the first enabled VPN rule (process_policy.applied / synchronization_script)
------------------------------------------------------------------------------------------------------
local function policy_error() refuse('POLICY-IDENTITY-CHANGED') end
function M.mark(value)  -- process_policy.mark
  if type(value)~='string' then policy_error() end
  local x
  if string.find(value,'^0x[0-9a-fA-F]+$') and #value<=10 then x=tonumber(string.sub(value,3),16)
  elseif string.find(value,'^[0-9]+$') and #value<=10 then x=tonumber(value,10)
  else policy_error() end
  if not (x>0 and x<=0xffffffff) then policy_error() end
  return x
end
local function recognizes(system,bindings)  -- process_policy.recognizes (system_section + binding)
  if not (system and system['.type']=='rule_process' and system.enabled=='1' and system.from_type=='process_gid') then return false end
  local want=bindings[system.via]
  if want==nil then return false end
  local ok,value=pcall(M.mark,system.mark)
  return ok and value==want
end
local function sections_of(cursor)
  local rows={}
  cursor:foreach('route_policy',nil,function(s) rows[#rows+1]=s end)
  return rows
end
local function first_and_system(rows)
  local first,system
  for _,s in ipairs(rows) do
    if not first and s['.type']=='rule' and s.enabled=='1' and s.via~='novpn' then first=s end
    if not system and s['.name']=='gl_process_vpn' then system=s end
  end
  return first,system
end
function M.applied(rows,bindings)
  if bindings==nil then return true end
  local first,system=first_and_system(rows)
  if not (first and system and recognizes(system,bindings) and system.via==first.via) then return false end
  local ok1,a=pcall(M.mark,system.mark);local ok2,b=pcall(M.mark,first.mark)
  return ok1 and ok2 and a==b
end
-- Inside the fenced UCI session after the reorder: CAS both derived fields, one commit, read back.
function M.synchronize_process(run,cursor,bindings)
  if bindings==nil then return false end
  if not cursor then policy_error() end  -- libuci-lua is a package dependency; no CLI fallback here
  local rows=sections_of(cursor)
  if M.applied(rows,bindings) then return false end
  local first,system=first_and_system(rows)
  if not system or not recognizes(system,bindings) or not first or bindings[first.via]==nil
     or M.mark(first.mark)~=bindings[first.via] then policy_error() end
  if not cursor:set('route_policy','gl_process_vpn','via',first.via)
     or not cursor:set('route_policy','gl_process_vpn','mark',first.mark)
     or not cursor:commit('route_policy') then refuse('POLICY-REORDER-UNVERIFIED') end
  return true
end
local function bindings_of(value)
  local raw=value.process_bindings
  if raw==nil or raw==canon.null then return nil end
  local out={}
  for k,v in pairs(raw) do out[k]=v end
  return out
end

-- fast_policy.uci_rules from libuci, else from `uci show route_policy` text.
function M.read_rules(run)
  local cursor=run.uci_cursor()
  local order,local_tunnel,local_mark
  if cursor then order,local_tunnel,local_mark=fp.uci_rules_from_cursor(cursor)
  else order,local_tunnel,local_mark=fp.uci_rules(kernel.decode(run.capture('uci_show'))) end
  return {order=order,local_tunnel=local_tunnel,local_mark=local_mark,source=cursor and 'libuci' or 'uci-show'}
end

------------------------------------------------------------------------------------------------------
-- request
------------------------------------------------------------------------------------------------------
local function copy(value) return canon.decode(canon.encode(value)) end
local function list(value)
  if not canon.is_array(value) then refuse('MANUAL-REQUEST-INVALID') end
  local out={}
  for i=1,#value do
    if type(value[i])~='string' then refuse('MANUAL-REQUEST-INVALID') end
    out[i]=value[i]
  end
  return out
end

function M.check_request(request,direction)
  if not canon.is_object(request) or (direction~='primary' and direction~='reserve') or request.direction~=direction then
    refuse('MANUAL-REQUEST-INVALID')
  end
  local value=request.journal
  if not canon.is_object(value) or value.phase~='APPLYING' or value.manual_instant~=true
     or type(request.control_revision)~='string' or value.control_revision~=request.control_revision then
    refuse('MANUAL-REQUEST-INVALID')
  end
  local destination=direction=='primary' and 'source' or 'target'
  local context=value.pair_transition
  if not canon.is_object(context) or context.destination_role~=destination then refuse('MANUAL-REQUEST-INVALID') end
  if not canon.is_object(request.names) then refuse('MANUAL-REQUEST-INVALID') end
  for id,name in pairs(request.names) do
    if type(id)~='string' or not safe_section(name) then refuse('UNSAFE-SECTION') end
  end
  local tunnels=list(request.tunnel_order)
  if #tunnels~=2 or tunnels[1]==tunnels[2] then refuse('MANUAL-REQUEST-INVALID') end
  journal.validate(value)  -- the Python-built journal must pass the Lua checks before anything else
  return {journal=value,template=copy(value),before=list(value.before),after=list(value.after),
          names=request.names,tunnels=tunnels,revision=request.control_revision,destination=destination}
end

------------------------------------------------------------------------------------------------------
-- the switch
------------------------------------------------------------------------------------------------------
local function round3(x) return math.floor(x*1000+0.5)/1000 end

-- run: the runner table; request: decoded instant-request.json. Returns result table and exit code.
function M.switch(run,request,direction,env)
  env=env or {}
  local path=env.journal_path
  local started=run.clock()
  local stamps={}
  local function stamp(name) stamps[#stamps+1]=canon.array({name,canon.float(round3(run.clock()-started))}) end
  local result=canon.object({ok=false,direction=direction or canon.null})
  local ok,req=pcall(M.check_request,request,direction)
  if not ok then result.code=code_of(req);return result,2 end
  local value=req.journal
  local function jenv(template)
    return {fs=run.fs,path=path,now=run.wall,hash=run.sha256,template=template}
  end
  local current
  ok,current=pcall(journal.read,{fs=run.fs,path=path,hash=run.sha256})
  if not ok then result.code=code_of(current);return result,2 end
  if not journal.settled(current) then result.code='TRANSACTION-IN-PROGRESS';return result,2 end
  ok,current=pcall(run.fenced,req.revision,function() journal.write(jenv(req.template),value) end)
  if not ok then result.code=code_of(current);return result,2 end
  stamp('journal')
  result.tx=value.tx
  local wrote=false
  local swap=canon.object({changed=false})
  local success,err=pcall(function()
    -- UCI: identities in file order must be the journal's `before`
    local cursor=run.uci_cursor()
    local by_name={}
    for id,name in pairs(req.names) do by_name[name]=id end
    local current_ids={}
    for i,name in ipairs(M.section_names(run,cursor)) do
      current_ids[i]=by_name[name]
      if not current_ids[i] then refuse('POLICY-IDENTITY-CHANGED') end
    end
    if #current_ids~=#req.before then refuse('POLICY-IDENTITY-CHANGED') end
    for i=1,#current_ids do if current_ids[i]~=req.before[i] then refuse('POLICY-IDENTITY-CHANGED') end end
    local moves=M.reorder_moves(req.before,req.after)
    local bindings=bindings_of(value)
    run.fenced(req.revision,function()
      if M.uci_apply(run,cursor,moves,req.names)>0 then wrote=true end
      if M.synchronize_process(run,cursor,bindings) then wrote=true end
    end)
    -- read back by content: anonymous section names are not stable across a reload
    local fresh=run.uci_cursor()
    if fresh and not M.applied(sections_of(fresh),bindings) then policy_error() end
    local rules=M.read_rules(run)
    if rules.order[1]~=req.tunnels[1] or rules.order[2]~=req.tunnels[2] then refuse('POLICY-REORDER-UNVERIFIED') end
    stamp('reordered')
    -- kernel: one read -> plan; atomic restore; one read -> verify + attest
    local before=kernel.snapshot(run.capture('iptables_save'))
    local plan=kernel.prepare(rules,before)
    local after=before
    if plan.changed then
      local t0=run.clock()
      run.fenced(req.revision,function() wrote=true;run.restore(plan.payload) end)
      swap.swap_ms=canon.float(math.floor((run.clock()-t0)*10000+0.5)/10)
      swap.changed=true
      after=kernel.snapshot(run.capture('iptables_save'))
      kernel.verify(rules,after)
      swap.conntrack_deleted=run.conntrack_delete(plan.old_mark)  -- "nothing to delete" is not a failure
    end
    stamp('switched')
    local proof=kernel.attest_route(kernel.parse_mangle(after),rules.order)
    if proof.first~=req.tunnels[1] then refuse('KERNEL-POLICY-UNVERIFIED') end
    stamp('verified')
  end)
  result.kernel=swap
  if not success then
    local code=code_of(err)
    result.code=code
    if fp.is_unsupported(err) then result.fallback='vendor-rebuild' end
    value.failure_code=code
    if not wrote then
      value.phase='ROLLED-BACK';value.reason='FAILED-BEFORE-APPLY';value.restored_order=canon.array(req.before)
      value.finished=canon.float(run.wall())
    end
    -- unfenced, as instant_manual records a failure even after Stop
    local wok,werr=pcall(journal.write,jenv(req.template),value)
    if not wok then result.journal_error=code_of(werr) end
    result.rollback_required=wrote
    result.stages=canon.array(stamps)
    return result,2
  end
  value.phase='HELD-ON-RESERVE';value.reason='OPERATOR-MANUAL';value.confirmed=canon.float(run.wall())
  value.reserve_healthy=true
  value.instant_seconds=canon.float(round3(canon.number(value.confirmed)-canon.number(value.started)))
  local hok,herr=pcall(run.fenced,req.revision,function() journal.write(jenv(req.template),value) end)
  if not hok then
    result.code=code_of(herr);result.rollback_required=true;result.stages=canon.array(stamps)
    return result,2
  end
  stamp('held')
  result.ok=true;result.code=canon.null;result.phase='HELD-ON-RESERVE';result.stages=canon.array(stamps)
  result.instant_seconds=value.instant_seconds
  return result,0
end

------------------------------------------------------------------------------------------------------
-- read-only measurement (the first thing to run on the router)
------------------------------------------------------------------------------------------------------
function M.dry_run(run,env)
  env=env or {}
  local result=canon.object({})
  local t=run.clock()
  local function lap(name) local now=run.clock();result[name..'_ms']=canon.float(math.floor((now-t)*10000+0.5)/10);t=now end
  local ok,rules=pcall(M.read_rules,run);lap('uci_read')
  if not ok then result.rules_code=code_of(rules) else
    result.rules_source=rules.source;result.order=canon.array(rules.order)
  end
  local text=run.capture('iptables_save');lap('iptables_save')
  local snap=kernel.snapshot(text);lap('snapshot')
  if ok then
    local pok,plan=pcall(kernel.prepare,rules,snap);lap('plan')
    if pok then
      result.changed=plan.changed;result.payload_sha256=run.sha256(plan.payload);lap('sha256')
    else result.plan_code=code_of(plan) end
    local aok,proof=pcall(function() return kernel.attest_route(kernel.parse_mangle(snap),rules.order) end);lap('attest')
    result.attest=aok and 'verified' or code_of(proof)
  end
  local jok,value=pcall(journal.read,{fs=run.fs,path=env.journal_path,hash=run.sha256});lap('journal_read')
  result.journal=jok and (value.phase or 'none') or code_of(value)
  result.sha256_backend=canon.sha256_backend()
  result.memory=canon.object(run.memory())
  result.monotonic=canon.float(run.clock());result.wall=canon.float(run.wall())
  return result,0
end

------------------------------------------------------------------------------------------------------
-- CLI
------------------------------------------------------------------------------------------------------
function M.main(argv,run)
  run=run or require('runner')
  local result,code
  if argv[1]=='--dry-run' then
    result,code=M.dry_run(run)
  else
    local text=run.fs.read(argv[2] or M.REQUEST)
    local ok,request=pcall(canon.decode,text or '')
    if not ok then result,code=canon.object({ok=false,code='MANUAL-REQUEST-INVALID'}),2
    else result,code=M.switch(run,request,argv[1]) end
  end
  io.write(canon.encode(result),'\n')
  return code
end

local script=arg and arg[0]
if script and (script=='instant_switch.lua' or string.match(script,'/instant_switch%.lua$')) then
  os.exit(M.main(arg))
end

return M
