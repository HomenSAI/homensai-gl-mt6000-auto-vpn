-- journal.lua: envelope and digest of native_switch.journal_write, validate_journal refusals, note_phase.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local json=require('canon')
local journal=require('journal')

local function sample()
  return json.object({tx='t1',phase='APPLYING',before=json.array({'a','b'}),after=json.array({'b','a'}),
    hash=string.rep('0',64),source='s',target='r',trial_nonce='n',started=json.float(1761830400.25),
    deadline=json.float(1761830520),pid=json.null,trial=false,
    process_bindings=json.object({wgclient1=4096,ovpnclient2=45056}),note='\208\150/\226\128\168'})
end
-- Python: hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
local PY_DIGEST='c8cc8ccb5754d3915d50016e69b7aea497270a8014cedad09dedabafd62b0567'

local function memory_fs()
  local files={}
  return {files=files,read=function(path) return files[path] end,
          write_atomic=function(path,text) files[path]=text end}
end

t.test('digest equals native_switch.digest',function()
  t.eq(journal.digest(sample()),PY_DIGEST)
  t.eq(journal.envelope(sample()):sub(1,20),'{"schema":1,"data":{')
end)

t.test('write then read: note_phase and the same value',function()
  local fs=memory_fs()
  local value=sample()
  journal.write({fs=fs,now=function() return 1761830401.5 end,path='/j'},value)
  local back=journal.parse(fs.files['/j'])
  t.eq(back.phase,'APPLYING')
  t.eq(#back.phase_evidence,1);t.eq(back.phase_evidence[1].phase,'APPLYING')
  t.truthy(json.is_float(back.phase_evidence[1].time))
  t.eq(json.encode(back),json.encode(value))
  -- same phase again: no new evidence row; a new phase: one more
  back.phase='HELD-ON-RESERVE'
  journal.write({fs=fs,now=function() return 1761830402 end,path='/j'},back)
  local again=journal.parse(fs.files['/j'])
  t.eq(#again.phase_evidence,2);t.eq(json.encode(again.phase_evidence[2]),'{"phase":"HELD-ON-RESERVE","time":1761830402.0}')
end)

t.test('a changed byte or hash is an integrity failure',function()
  local text=journal.envelope(sample())
  t.code('JOURNAL-INTEGRITY-FAILED',journal.parse,(text:gsub('"tx":"t1"','"tx":"t2"')))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.parse,(text:gsub('"schema":1','"schema":1.0')))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.parse,text:sub(1,-2))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.parse,'[]')
  t.code('JOURNAL-INTEGRITY-FAILED',journal.read,{fs={read=function() return nil end,unsafe=function() return true end}})
  t.eq(next(journal.read({fs={read=function() return nil end}})),nil)  -- no journal: {}
end)

t.test('validate_journal refusal codes',function()
  local function with(changes)
    local v=sample()
    for k,x in pairs(changes) do if x=='nil' then v[k]=nil else v[k]=x end end
    return v
  end
  t.code('JOURNAL-ORDER-INVALID',journal.validate,with({before=json.array({'a'}),after=json.array({'a'})}))
  t.code('JOURNAL-SECTION-INVALID',journal.validate,with({before=json.array({'a','b-c'}),after=json.array({'b-c','a'})}))
  t.code('JOURNAL-ORDER-INVALID',journal.validate,with({after=json.array({'a','a'})}))
  t.code('JOURNAL-PHASE-INVALID',journal.validate,with({phase='DONE'}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({proof_scope='lan'}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({process_bindings=json.object({wgclient1=4096,ovpnclient2=4096})}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({process_bindings=json.object({wgclient1=json.float(4096),ovpnclient2=1})}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({hash='ABC'}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({started=true}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({deadline=json.float(1)}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({pid=1}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({trial='no'}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({target='s'}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({tx='bad tx'}))
  t.code('JOURNAL-INTEGRITY-FAILED',journal.validate,with({rollback_failures=3}))
  journal.validate(with({phase='ROLLED-BACK',tx='nil',source='nil',target='nil',trial_nonce='nil'}))
  journal.validate(with({monotonic_deadline=json.null,pid=1234,rollback_failures=2,proof_scope='router-probed-ipv4'}))
end)

t.test('delegated records are only copied from a Python-validated journal',function()
  local v=sample();v.pair_transition=json.object({direction='first'})
  t.code('JOURNAL-DELEGATED-UNVERIFIED',journal.write,{fs=memory_fs(),now=function() return 1 end},v)
  local template=sample();template.pair_transition=json.object({direction='first'})
  journal.write({fs=memory_fs(),now=function() return 1 end,template=template},v)
  template.pair_transition=json.object({direction='last'})
  t.code('JOURNAL-DELEGATED-UNVERIFIED',journal.write,{fs=memory_fs(),now=function() return 1 end,template=template},v)
end)

t.test('note_phase keeps the last 31 valid rows',function()
  local v=sample();local rows={}
  for i=1,40 do rows[i]=json.object({phase='P'..i,time=i}) end
  rows[40]=json.object({phase='bad phase',time=1})
  v.phase_evidence=json.array(rows)
  journal.note_phase(v,'APPLYING',99.5)
  t.eq(#v.phase_evidence,31);t.eq(v.phase_evidence[1].phase,'P10');t.eq(v.phase_evidence[31].phase,'APPLYING')
end)

t.run()
