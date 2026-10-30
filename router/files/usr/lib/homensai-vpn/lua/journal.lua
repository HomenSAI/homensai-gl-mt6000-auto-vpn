-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- journal.lua: the native transaction journal (/etc/homensai-vpn/native-transaction.json) of the Lua core.
--
-- Same file as native_switch.journal_write/journal_read: {"schema":1,"data":<journal>,"sha256":<hex>} where
-- the hash is sha256 of json.dumps(data, sort_keys=True, separators=(',',':')). A journal written here is
-- read by the Python recovery unchanged, and the other way round (tests/test_lua_fast_policy.py checks
-- both directions with the real Python code).
--
-- validate() ports the structural part of validate_journal(). Four nested records are checked by Python
-- modules that are not ported yet (vendor_profiles, pair_transition, restore_order_step/proof_source/
-- order_origin). The Lua writer therefore never invents them: each one must be byte-identical (canonical
-- JSON) to the record in a template that Python validated - the journal it wrote, or a prepared one.
-- Everything is injectable: hash (default canon.sha256), clock, file system.
local json=require('canon')

local M={}
M.PATH='/etc/homensai-vpn/native-transaction.json'
M.MAX_BYTES=1024*1024
M.ROLLBACK_FAILURE_LIMIT=2  -- native_switch.ROLLBACK_FAILURE_LIMIT
M.DELEGATED={'vendor_profiles','pair_transition','restore_order_step','restore_proof_source','restore_order_origin'}

local Refused={}
Refused.__index=Refused
Refused.__tostring=function(e) return e.code end
M.Refused=Refused
local function refuse(code) error(setmetatable({code=code},Refused),0) end
function M.is_refused(e) return type(e)=='table' and getmetatable(e)==Refused end

local PHASES={['ARMED']=1,['APPLYING']=1,['WAIT-CLIENT']=1,['COMMITTED']=1,['HELD-ON-RESERVE']=1,
              ['RESTORING']=1,['ROLLED-BACK']=1,['RELEASE-PENDING']=1}
local PROOF_SCOPES={['external-lan']=1,['router-hosted-ipv4']=1,['router-probed-ipv4']=1}

local function digest(value,hash) return (hash or json.sha256)(json.encode(value)) end
M.digest=digest  -- native_switch.digest

-- The bytes atomic_json() would write for this journal (key order of data does not matter to readers).
function M.envelope(value,hash)
  local canonical=json.encode(value)
  return '{"schema":1,"data":'..canonical..',"sha256":"'..(hash or json.sha256)(canonical)..'"}'
end

------------------------------------------------------------------------------------------------------
-- validate_journal(), structural part
------------------------------------------------------------------------------------------------------
local function is_str(v) return type(v)=='string' end
local function full(v,pattern,low,high)  -- re.fullmatch('[class]{low,high}')
  return is_str(v) and #v>=low and #v<=high and string.find(v,'^'..pattern..'+$')~=nil
end
local function hex(v,n) return full(v,'[a-f0-9]',n,n) end
local function is_int(v) return type(v)=='number' and v%1==0 end  -- canon: integral plain numbers are Python ints
local function finite_number(v)
  local x=json.number(v)
  return x~=nil and x==x and x~=math.huge and x~=-math.huge,x
end
local function has(value,key) return value[key]~=nil end  -- `key in value` (JSON null is canon.null, not nil)
local function list_set(list)
  local set,count={},0
  for _,item in ipairs(list) do if not set[item] then set[item]=true;count=count+1 end end
  return set,count
end
local function same_set(a,b)
  for k in pairs(a) do if not b[k] then return false end end
  for k in pairs(b) do if not a[k] then return false end end
  return true
end

local function valid_bindings(bindings)  -- process_policy.validate
  if bindings==nil or bindings==json.null then return true end
  if not json.is_object(bindings) then return false end
  local count,values,distinct=0,{},0
  for k,v in pairs(bindings) do
    count=count+1
    local name=is_str(k) and (string.match(k,'^wgclient([0-9]+)$') or string.match(k,'^ovpnclient([0-9]+)$'))
    if not name or #name>4 or not is_int(v) or not (v>0 and v<=0xffffffff) then return false end
    if not values[v] then values[v]=true;distinct=distinct+1 end
  end
  return count==2 and distinct==2
end

local function check_delegated(value,template)
  for _,key in ipairs(M.DELEGATED) do
    if has(value,key) then
      if not template or not has(template,key) or json.encode(value[key])~=json.encode(template[key]) then
        refuse('JOURNAL-DELEGATED-UNVERIFIED')
      end
    end
  end
end

-- validate_journal(value) for the parts that need no other module. opts.template (writer side) pins the
-- delegated records; a reader (journal written and validated by Python) passes no template.
function M.validate(value,opts)
  opts=opts or {}
  if not json.is_object(value) then refuse('JOURNAL-INTEGRITY-FAILED') end
  local before=value.before;if before==nil then before=json.array({}) end
  local after=value.after;if after==nil then after=json.array({}) end
  if not json.is_array(before) or not json.is_array(after) or #before<2 or #before>400 or #before~=#after then
    refuse('JOURNAL-ORDER-INVALID')
  end
  for _,list in ipairs({before,after}) do
    for _,s in ipairs(list) do if not full(s,'[A-Za-z0-9_]',1,64) then refuse('JOURNAL-SECTION-INVALID') end end
  end
  local bset,bcount=list_set(before);local aset,acount=list_set(after)
  if bcount~=#before or acount~=#after or not same_set(bset,aset) then refuse('JOURNAL-ORDER-INVALID') end
  if not (is_str(value.phase) and PHASES[value.phase]) then refuse('JOURNAL-PHASE-INVALID') end
  local scope=value.proof_scope;if scope==nil then scope='external-lan' end
  if not (is_str(scope) and PROOF_SCOPES[scope]) then refuse('JOURNAL-INTEGRITY-FAILED') end  -- native_proof.matches
  if not valid_bindings(value.process_bindings) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if not hex(value.hash,64) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'vendor_identity') and not hex(value.vendor_identity,64) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'control_revision') and not hex(value.control_revision,32) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'vendor_profiles') then  -- shape only; profile_identity() itself stays in Python
    local proofs=value.vendor_profiles
    if not json.is_object(proofs) then refuse('JOURNAL-INTEGRITY-FAILED') end
    local count=0
    for role,proof in pairs(proofs) do
      count=count+1
      if (role~='source' and role~='target') or not json.is_object(proof) or proof.id~=value[role] then refuse('JOURNAL-INTEGRITY-FAILED') end
    end
    if count~=2 then refuse('JOURNAL-INTEGRITY-FAILED') end
  end
  for _,name in ipairs({'started','deadline','monotonic_deadline','lease_monotonic_until','confirmed','kernel_confirmed','finished'}) do
    local v=value[name]
    if not (name=='monotonic_deadline' and (v==nil or v==json.null)) and v~=nil then
      local ok,x=finite_number(v)
      if not ok or x<0 then refuse('JOURNAL-INTEGRITY-FAILED') end
    end
  end
  if has(value,'pid') and value.pid~=json.null and not (is_int(value.pid) and value.pid>1) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'rollback_failures') and not (is_int(value.rollback_failures) and value.rollback_failures>=0
      and value.rollback_failures<=M.ROLLBACK_FAILURE_LIMIT) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'rollback_package') and not full(value.rollback_package,'[0-9A-Za-z.+~%-]',1,64) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'trial') and type(value.trial)~='boolean' then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'manual_request_id') and not hex(value.manual_request_id,32) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'pair_transition') and value.pair_transition~=json.null and not json.is_object(value.pair_transition) then
    refuse('JOURNAL-INTEGRITY-FAILED')  -- pair_policy.metadata() stays in Python
  end
  if has(value,'kernel_before_fingerprint') and not hex(value.kernel_before_fingerprint,64) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if has(value,'restore_kernel_fingerprint') and (not hex(value.restore_kernel_fingerprint,64)
      or value.pair_transition==nil or value.pair_transition==json.null
      or not has(value,'restore_before_order') or not has(value,'restore_target_order')) then refuse('JOURNAL-INTEGRITY-FAILED') end
  for _,key in ipairs({'forward_policy_touched','rtp_dispatched','kernel_before_verified','restore_before_verified'}) do
    if has(value,key) and type(value[key])~='boolean' then refuse('JOURNAL-INTEGRITY-FAILED') end
  end
  if has(value,'restore_before_order') then
    local order=value.restore_before_order
    if not json.is_array(order) or #order~=#before then refuse('JOURNAL-INTEGRITY-FAILED') end
    for _,x in ipairs(order) do if not is_str(x) then refuse('JOURNAL-INTEGRITY-FAILED') end end
    if not same_set((list_set(order)),bset) then refuse('JOURNAL-INTEGRITY-FAILED') end
  end
  if has(value,'activation_reapply') then
    local same=#before==#after
    for i=1,#before do if before[i]~=after[i] then same=false end end
    local manual=value.manual_request_id
    if value.activation_reapply~=true or value.pair_transition==nil or value.pair_transition==json.null
       or not (manual==nil or manual==json.null) or not same then refuse('JOURNAL-INTEGRITY-FAILED') end
  end
  if value.phase~='ROLLED-BACK' and value.phase~='RELEASE-PENDING' then
    for _,name in ipairs({'tx','source','target','trial_nonce'}) do
      if not full(value[name],'[A-Za-z0-9_:.%-]',1,96) then refuse('JOURNAL-INTEGRITY-FAILED') end
    end
    if value.source==value.target or value.started==nil or value.deadline==nil then refuse('JOURNAL-INTEGRITY-FAILED') end
    if json.number(value.deadline)<json.number(value.started) then refuse('JOURNAL-INTEGRITY-FAILED') end
  end
  if opts.writer then check_delegated(value,opts.template) end
  return value
end

------------------------------------------------------------------------------------------------------
-- note_phase / write / read
------------------------------------------------------------------------------------------------------
local function valid_phase_name(p) return full(p,'[A-Z0-9_%-]',1,96) end

function M.note_phase(value,phase,now)  -- native_switch.note_phase
  local rows=value.phase_evidence
  if not json.is_array(rows) then rows={} end
  local kept={}
  for i=math.max(1,#rows-30),#rows do
    local r=rows[i]
    if json.is_object(r) then
      local keys=0
      for _ in pairs(r) do keys=keys+1 end
      local ok=finite_number(r.time)
      if keys==2 and valid_phase_name(r.phase) and ok then kept[#kept+1]=r end
    end
  end
  if #kept==0 or kept[#kept].phase~=phase then
    kept[#kept+1]=json.object({phase=phase,time=json.float(json.number(now))})  -- time.time() is a float
  end
  value.phase_evidence=json.array(kept)
end

-- journal_write(value): validate, note the phase, one atomic replace. env: fs.write_atomic(path,text),
-- now() (wall seconds), hash(text) (optional), path (optional), template (the Python-validated journal).
function M.write(env,value)
  M.validate(value,{template=env.template,writer=true})
  if valid_phase_name(value.phase) then M.note_phase(value,value.phase,env.now()) end
  env.fs.write_atomic(env.path or M.PATH,M.envelope(value,env.hash))
  return value
end

-- The journal from file text, as journal_read() returns it (refusal code on any doubt).
function M.parse(text,hash)
  if #text>M.MAX_BYTES then refuse('JOURNAL-INTEGRITY-FAILED') end
  local ok,envelope=pcall(json.decode,text)
  if not ok or not json.is_object(envelope) then refuse('JOURNAL-INTEGRITY-FAILED') end
  local data=envelope.data
  if not is_int(envelope.schema) or envelope.schema~=1 or not json.is_object(data)
     or envelope.sha256~=digest(data,hash) then
    refuse('JOURNAL-INTEGRITY-FAILED')
  end
  return M.validate(data)
end

-- journal_read(): {} (canon object) when there is no journal. env.fs.read(path) -> text|nil, and
-- env.fs.unsafe(path) -> true for a symlink, a non-file or a file above 1 MB (when the fs can tell).
function M.read(env)
  local path=env.path or M.PATH
  if env.fs.unsafe and env.fs.unsafe(path) then refuse('JOURNAL-INTEGRITY-FAILED') end
  local ok,text=pcall(env.fs.read,path)
  if not ok then refuse('JOURNAL-INTEGRITY-FAILED') end
  if text==nil then return json.object({}) end
  return M.parse(text,env.hash)
end

-- light_gate(): a new switch may start only from a settled journal.
function M.settled(journal)
  local phase=journal.phase
  return phase==nil or phase=='ROLLED-BACK' or phase=='COMMITTED' or phase=='HELD-ON-RESERVE'
end

return M
