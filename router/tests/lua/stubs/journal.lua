-- TEST STUB of lua-core journal.lua. Same API (digest/envelope/validate/note_phase/write/parse/read/settled),
-- a reduced validate(): phases, orders, hash; the real module carries the full validate_journal port.
local json=require('canon')
local M={}
M.PATH='/etc/homensai-vpn/native-transaction.json'
M.ROLLBACK_FAILURE_LIMIT=2
local Refused={};Refused.__index=Refused;Refused.__tostring=function(e) return e.code end
M.Refused=Refused
local function refuse(code) error(setmetatable({code=code},Refused),0) end
function M.is_refused(e) return type(e)=='table' and getmetatable(e)==Refused end
local PHASES={['ARMED']=1,['APPLYING']=1,['WAIT-CLIENT']=1,['COMMITTED']=1,['HELD-ON-RESERVE']=1,['RESTORING']=1,['ROLLED-BACK']=1,['RELEASE-PENDING']=1}
function M.digest(value,hash) return (hash or json.sha256)(json.encode(value)) end
function M.envelope(value,hash)
  local canonical=json.encode(value)
  return '{"schema":1,"data":'..canonical..',"sha256":"'..(hash or json.sha256)(canonical)..'"}'
end
function M.validate(value)
  if not json.is_object(value) then refuse('JOURNAL-INTEGRITY-FAILED') end
  local before,after=value.before or json.array({}),value.after or json.array({})
  if not json.is_array(before) or not json.is_array(after) or #before<2 or #before>400 or #before~=#after then refuse('JOURNAL-ORDER-INVALID') end
  for _,list in ipairs({before,after}) do for _,s in ipairs(list) do if type(s)~='string' or not string.find(s,'^[A-Za-z0-9_]+$') then refuse('JOURNAL-SECTION-INVALID') end end end
  if not PHASES[value.phase] then refuse('JOURNAL-PHASE-INVALID') end
  if type(value.hash)~='string' or #value.hash~=64 then refuse('JOURNAL-INTEGRITY-FAILED') end
  if value.rollback_failures~=nil and (type(value.rollback_failures)~='number' or value.rollback_failures>M.ROLLBACK_FAILURE_LIMIT) then refuse('JOURNAL-INTEGRITY-FAILED') end
  if value.phase~='ROLLED-BACK' and value.phase~='RELEASE-PENDING' then
    for _,name in ipairs({'tx','source','target','trial_nonce'}) do if type(value[name])~='string' then refuse('JOURNAL-INTEGRITY-FAILED') end end
    if value.source==value.target or value.started==nil or value.deadline==nil then refuse('JOURNAL-INTEGRITY-FAILED') end
  end
  return value
end
function M.note_phase(value,phase,now)
  local rows=value.phase_evidence
  if not json.is_array(rows) then rows=json.array({}) end
  if #rows==0 or rows[#rows].phase~=phase then rows[#rows+1]=json.object({phase=phase,time=json.float(json.number(now))}) end
  value.phase_evidence=rows
end
function M.write(env,value)
  M.validate(value)
  if type(value.phase)=='string' then M.note_phase(value,value.phase,env.now()) end
  env.fs.write_atomic(env.path or M.PATH,M.envelope(value,env.hash))
  return value
end
function M.parse(text,hash)
  local ok,envelope=pcall(json.decode,text)
  if not ok or not json.is_object(envelope) then refuse('JOURNAL-INTEGRITY-FAILED') end
  local data=envelope.data
  if envelope.schema~=1 or not json.is_object(data) or envelope.sha256~=M.digest(data,hash) then refuse('JOURNAL-INTEGRITY-FAILED') end
  return M.validate(data)
end
function M.read(env)
  local path=env.path or M.PATH
  if env.fs.unsafe and env.fs.unsafe(path) then refuse('JOURNAL-INTEGRITY-FAILED') end
  local ok,text=pcall(env.fs.read,path)
  if not ok then refuse('JOURNAL-INTEGRITY-FAILED') end
  if text==nil then return json.object({}) end
  return M.parse(text,env.hash)
end
function M.settled(journal)
  local phase=journal.phase
  return phase==nil or phase=='ROLLED-BACK' or phase=='COMMITTED' or phase=='HELD-ON-RESERVE'
end
return M
