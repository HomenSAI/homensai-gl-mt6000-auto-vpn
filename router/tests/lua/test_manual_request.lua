-- manual_request.lua (plan item 4): the click request in the Lua monitor, same order and codes as
-- pair_manual_reply/request/light_gate; FALLBACK (agent.py) for what it cannot decide without waiting.
-- Usage for the Python cross-check: lua test_manual_request.lua --row  prints one written QUEUED row.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local M=require('manual_request')

local REV=string.rep('a',32)
local PAIR=string.rep('b',32)
local TX=string.rep('c',32)
local NOW=1793420000.5

local function world(over)
  over=over or {}
  local files={}
  files['/run/native-status.json']=canon.encode(canon.object({state='OBSERVING',time=canon.float(NOW-3),
    source='wireguard:peer_1',target='openvpn:1_2'}))
  files['/etc/native-transaction.json']=canon.encode(canon.object({schema=1,sha256=string.rep('0',64),
    data=canon.object({phase='ROLLED-BACK',tx=TX})}))
  files['/run/pair-auto-control.json']=canon.encode(canon.object({mode='on',id=PAIR,revision=REV,time=canon.float(NOW-100)}))
  files['/proc/sys/kernel/random/uuid']='0123abcd-0123-4567-89ab-0123456789ab\n'
  for k,v in pairs(over.files or {}) do files[k]=v end
  local status=canon.object({profiles=canon.array({
    canon.object({id='wireguard:peer_1',time=canon.float(NOW-10),code=canon.null,dns_ok=true,https_success=3}),
    canon.object({id='openvpn:1_2',time=canon.float(NOW-10),code=canon.null,dns_ok=true,https_success=2})})})
  if over.status then status=over.status end
  local uci={pair_auto_mode='router-probed-ipv4',interval='60'}
  for k,v in pairs(over.uci or {}) do uci[k]=v end
  local deps={files=files,
    read=function(p) return files[p] end,
    write=function(p,text) files[p]=text end,
    now=function() return NOW end,runtime='/run',persist='/etc',
    config_text=function() return over.config or "config homensai_vpn 'main'\n\toption interval '60'\n" end,
    uci_get=function(o) return uci[o] end,
    status=function() return status end,
    read_state=function() return over.state or canon.object({phase='RUNNING',id=PAIR,revision=REV}) end,
    current_revision=function() return over.revision or REV end,
    try_lock=function(fn) if over.locked then return false end;return true,fn() end}
  return deps
end
local function args(direction,extra)
  local a=canon.object({direction=direction,control_revision=REV,request_source='manual'})
  for k,v in pairs(extra or {}) do a[k]=v end
  return a
end
local function code(reply) return reply.blockers and reply.blockers[1] end

if arg[1]=='--row' then
  local d=world()
  M.request(d,args('reserve'))
  io.write(d.files['/run/pair-manual-control.json'])
  os.exit(0)
end

t.test('accepted: one QUEUED row bound to the pair, the revision and the journal transaction',function()
  local d=world()
  local reply=M.request(d,args('reserve'))
  t.eq(reply.accepted,true);t.eq(reply.queued,true);t.eq(reply.completed,false)
  t.eq(reply.request_id,'0123abcd01234567' ..'89ab0123456789ab');t.eq(reply.control_revision,REV)
  local row=canon.decode(d.files['/run/pair-manual-control.json'])
  t.eq(row.state,'QUEUED');t.eq(row.pair,PAIR);t.eq(row.revision,REV);t.eq(row.direction,'reserve')
  t.eq(row.selection.tx,TX);t.eq(row.request_source,'manual');t.eq(row.code,canon.null)
  t.truthy(canon.is_float(row.requested) and canon.is_float(row.updated),'float times like time.time()')
end)

t.test('fields: unknown key, missing key, bad direction or revision',function()
  t.eq(code(M.request(world(),canon.object({direction='reserve'}))),'PAIR-MANUAL-FIELDS')
  t.eq(code(M.request(world(),args('reserve',{extra='x'}))),'PAIR-MANUAL-FIELDS')
  t.eq(code(M.request(world(),args('sideways'))),'PAIR-MANUAL-FIELDS')
  local a=args('reserve');a.control_revision='XYZ'
  t.eq(code(M.request(world(),a)),'PAIR-MANUAL-FIELDS')
end)

t.test('resume, fast switch off, held lock and speed pause go to agent.py',function()
  t.eq(M.request(world(),args('resume')),M.FALLBACK)
  t.eq(M.request(world({config="config homensai_vpn 'main'\n\toption fast_switch '0'\n"}),args('reserve')),M.FALLBACK)
  t.eq(M.request(world({locked=true}),args('reserve')),M.FALLBACK)
  t.eq(M.request(world({files={['/run/speed-pause.json']='{}'}}),args('reserve')),M.FALLBACK)
end)

t.test('light gate codes in pair_manual order',function()
  t.eq(code(M.request(world({uci={pair_auto_mode='off'}}),args('reserve'))),'PAIR-MODE-NOT-CONFIGURED')
  t.eq(code(M.request(world({files={['/run/pair-manual-control.json']='{"state":"QUEUED"}'}}),args('reserve'))),'PAIR-MANUAL-BUSY')
  t.eq(code(M.request(world({files={['/run/native-status.json']=canon.encode(canon.object({state='APPLYING',time=canon.float(NOW)}))}}),args('reserve'))),'PAIR-MANUAL-BUSY')
  t.eq(code(M.request(world({files={['/run/native-status.json']=canon.encode(canon.object({state='OBSERVING',time=canon.float(NOW-31),source='wireguard:peer_1',target='openvpn:1_2'}))}}),args('reserve'))),'PAIR-MANUAL-STALE')
  t.eq(code(M.request(world({files={['/etc/native-transaction.json']=canon.encode(canon.object({schema=1,data=canon.object({phase='WAIT-CLIENT'})}))}}),args('reserve'))),'TRANSACTION-IN-PROGRESS')
  local sick=canon.object({profiles=canon.array({canon.object({id='openvpn:1_2',time=canon.float(NOW-10),code='VPN-003',dns_ok=true,https_success=1})})})
  t.eq(code(M.request(world({status=sick}),args('reserve'))),'PAIR-MANUAL-TARGET-UNHEALTHY')
  t.eq(code(M.request(world({status=sick}),args('primary'))),'SOURCE-NOT-HEALTHY')
end)

t.test('under the lock: stale revision, pair not running, a pending row written meanwhile',function()
  t.eq(code(M.request(world({revision=string.rep('d',32)}),args('reserve'))),'CONTROL-REVISION-STALE')
  t.eq(code(M.request(world({state=canon.object({phase='STOPPED',id=PAIR,revision=REV})}),args('reserve'))),'CONTROL-REVISION-STALE')
end)

t.test('a broken file is a refusal, never an error',function()
  t.eq(code(M.request(world({files={['/run/native-status.json']='{broken'}}),args('reserve'))),'PAIR-MANUAL-REQUEST-UNCONFIRMED')
end)

t.test('valid_for and fast_switch_enabled follow the Python rules',function()
  t.eq(M.valid_for('60'),180);t.eq(M.valid_for('5'),90);t.eq(M.valid_for(nil),90);t.eq(M.valid_for('300'),900)
  t.eq(M.fast_switch_enabled(nil),false)
  t.eq(M.fast_switch_enabled("\toption fast_switch '1'\n"),true)
  t.eq(M.fast_switch_enabled("\toption fast_switch 0\n"),false)
end)

-- F-35: caller-supplied request id (pair_manual.request with client_request_id)
local CID='reserve-click-0002'
t.test('request id: a retry gets the stored acceptance back, never a second row or BUSY',function()
  local d=world()
  local first=M.request(d,args('reserve',{client_request_id=CID}))
  t.eq(first.accepted,true)
  local row=d.files['/run/pair-manual-control.json']
  d.files['/proc/sys/kernel/random/uuid']='ffffffff-0123-4567-89ab-0123456789ab\n'
  local again=M.request(d,args('reserve',{client_request_id=CID}))
  t.eq(again.accepted,true);t.eq(again.replayed,true);t.eq(again.request_id,first.request_id)
  t.eq(d.files['/run/pair-manual-control.json'],row)
  -- even after the row completed and a newer hold exists the retry is only a replay
  d.files['/run/pair-manual-control.json']='{"state":"COMPLETED"}'
  t.eq(M.request(d,args('reserve',{client_request_id=CID})).replayed,true)
  t.eq(d.files['/run/pair-manual-control.json'],'{"state":"COMPLETED"}')
end)

t.test('request id: a refusal is stored and replayed; a held lock leaves it to agent.py',function()
  local d=world({uci={pair_auto_mode='off'}})
  t.eq(code(M.request(d,args('reserve',{client_request_id=CID}))),'PAIR-MODE-NOT-CONFIGURED')
  local entries=canon.decode(d.files['/run/pair-manual-requests.json']).entries
  t.eq(#entries,1);t.eq(entries[1].client,CID)
  local locked=world({uci={pair_auto_mode='off'},locked=true})
  t.eq(M.request(locked,args('reserve',{client_request_id=CID})),M.FALLBACK)
end)

t.test('BH-07: a transient refusal is not kept; an older kept one is ignored; the retry decides afresh',function()
  local d=world({files={['/run/pair-manual-control.json']=canon.encode(canon.object({state='QUEUED',id=string.rep('9',32)}))}})
  t.eq(code(M.request(d,args('reserve',{client_request_id=CID}))),'PAIR-MANUAL-BUSY')
  t.eq(d.files['/run/pair-manual-requests.json'],nil,'PAIR-MANUAL-BUSY is not kept for the id')
  d.files['/run/pair-manual-control.json']='{"state":"COMPLETED"}'  -- the other operation ended
  local retry=M.request(d,args('reserve',{client_request_id=CID}))
  t.eq(retry.accepted,true);t.eq(retry.replayed,nil)
  local again=M.request(d,args('reserve',{client_request_id=CID}))
  t.eq(again.replayed,true);t.eq(again.request_id,retry.request_id,'no second row: no double switch')
  local stale=canon.object({accepted=false,queued=false,completed=false,blockers=canon.array({'SPEED-BUSY'})})
  local old=world({files={['/run/pair-manual-requests.json']=canon.encode(canon.object({entries=canon.array({canon.object({client=CID,reply=stale})})}))}})
  local fresh=M.request(old,args('reserve',{client_request_id=CID}))
  t.eq(fresh.accepted,true);t.eq(fresh.replayed,nil)
  local entries=canon.decode(old.files['/run/pair-manual-requests.json']).entries
  t.eq(#entries,1);t.eq(entries[1].reply.accepted,true)
  t.eq(M.transient_refusal(canon.object({accepted=false,blockers=canon.array({'PAIR-MANUAL-REQUEST-UNCONFIRMED'})})),true)
  t.eq(M.transient_refusal(canon.object({accepted=false,blockers=canon.array({'PAIR-MODE-NOT-CONFIGURED'})})),false)
  t.eq(M.transient_refusal(canon.object({accepted=true,blockers=canon.array({'SPEED-BUSY'})})),false)
end)

t.test('request id: a resume id seen before is replayed even though resume itself goes to agent.py',function()
  local reply=canon.object({accepted=true,queued=true,completed=false,request_id=string.rep('e',32),control_revision=REV})
  local ledger=canon.encode(canon.object({entries=canon.array({canon.object({client='resume-click-0001',reply=reply})})}))
  local d=world({files={['/run/pair-manual-requests.json']=ledger}})
  local again=M.request(d,args('resume',{client_request_id='resume-click-0001'}))
  t.eq(again.replayed,true);t.eq(again.request_id,string.rep('e',32))
  t.eq(M.request(d,args('resume',{client_request_id='resume-click-0009'})),M.FALLBACK)
end)

t.test('request id: invalid ids, a damaged ledger, the bound, and no id at all',function()
  for _,bad in ipairs({'short',string.rep('x',65),'with space id',7}) do
    t.eq(code(M.request(world(),args('reserve',{client_request_id=bad}))),'PAIR-MANUAL-FIELDS')
  end
  local broken=world({files={['/run/pair-manual-requests.json']='{"entries":"nope"}'}})
  t.eq(code(M.request(broken,args('reserve',{client_request_id=CID}))),'PAIR-MANUAL-STATE-UNVERIFIED')
  t.eq(broken.files['/run/pair-manual-control.json'],nil)
  local d=world({uci={pair_auto_mode='off'}})
  for i=1,M.LEDGER_LIMIT+5 do M.request(d,args('reserve',{client_request_id=string.format('bounded-%04d',i)})) end
  local entries=canon.decode(d.files['/run/pair-manual-requests.json']).entries
  t.eq(#entries,M.LEDGER_LIMIT);t.eq(entries[#entries].client,string.format('bounded-%04d',M.LEDGER_LIMIT+5))
  local plain=world()
  local reply=M.request(plain,args('reserve'))
  t.eq(reply.accepted,true);t.eq(reply.replayed,nil);t.eq(plain.files['/run/pair-manual-requests.json'],nil)
end)

t.run()
