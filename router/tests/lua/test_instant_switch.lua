-- instant_switch.lua end to end against a fake router: UCI (libuci-like cursor), iptables, files, fence.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local journal=require('journal')
local s=require('instant_switch')

local REVISION=string.rep('c',32)
local FULL=table.concat({'*mangle',':PREROUTING ACCEPT [0:0]',':ROUTE_POLICY - [0:0]',':TUNNEL4192_ROUTE_POLICY - [0:0]',
  ':TUNNEL5841_ROUTE_POLICY - [0:0]',':TUNNEL10100_LOCAL_POLICY - [0:0]',
  '-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000',
  '-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN',
  '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY',
  '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY',
  '-A TUNNEL10100_LOCAL_POLICY -m comment --comment "TUNNEL10100 rule for set mark" -m connmark --mark 0x0/0xf000 -m mark --mark 0x0/0xf000 -m owner --gid-owner 20000 -j MARK --set-xmark 0x1000/0xf000',
  '-A TUNNEL4192_ROUTE_POLICY -m comment --comment "TUNNEL4192 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0xb000/0xf000',
  '-A TUNNEL4192_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP',
  '-A TUNNEL5841_ROUTE_POLICY -m comment --comment "TUNNEL5841 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0x1000/0xf000',
  '-A TUNNEL5841_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP','COMMIT',''},'\n')

local function copy(rows) local out={};for i,r in ipairs(rows) do local c={};for k,v in pairs(r) do c[k]=v end;out[i]=c end;return out end

local function router(options)
  options=options or {}
  local st={revision=REVISION,files={},calls={},clock=100,wall=1761830400.5,mangle=FULL,
    config={{['.name']='gl_process_vpn',['.type']='rule_process',['.anonymous']=false,enabled='1',from_type='process_gid',
             tunnel_id='10100',via='wgclient1',mark='0x1000'},
            {['.name']='cfg01',['.type']='rule',['.anonymous']=true,enabled='1',via='wgclient1',mark='0x1000',tunnel_id='5841'},
            {['.name']='cfg02',['.type']='rule',['.anonymous']=true,enabled='1',via='ovpnclient2',mark='0xb000',tunnel_id='4192'}}}
  local run={fs={}}
  local function call(name) st.calls[#st.calls+1]=name end
  function run.uci_cursor()
    local work=copy(st.config)
    local c={}
    function c:foreach(config,kind,fn) for _,r in ipairs(work) do if not kind or r['.type']==kind then fn(r) end end end
    function c:get_all(config,name) for _,r in ipairs(work) do if r['.name']==name then return r end end end
    function c:reorder(config,name,index)
      call('reorder '..name..'='..index)
      for i,r in ipairs(work) do if r['.name']==name then table.remove(work,i);table.insert(work,index+1,r);return true end end
    end
    function c:set(config,name,key,value) call('set '..name..'.'..key..'='..value);self:get_all(config,name)[key]=value;return true end
    function c:commit(config) call('commit');if options.commit_fails then return nil end;st.config=copy(work);return true end
    return c
  end
  function run.capture(name)
    if name=='iptables_save' then call('iptables-save');return st.mangle end
    error('unexpected capture '..name)
  end
  function run.restore(payload)
    call('iptables-restore')
    if options.restore_ignored then return true end
    -- replace the chains named in the payload, in place
    local chains,lines={},{}
    for line in payload:gmatch('[^\n]+') do
      local chain=line:match('^:(%S+)');if chain then chains[chain]={} end
      local owner=line:match('^%-A (%S+) ');if owner then table.insert(chains[owner],line) end
    end
    local done={}
    for line in st.mangle:gmatch('[^\n]+') do
      local owner=line:match('^%-A (%S+) ')
      if owner and chains[owner] then
        if not done[owner] then done[owner]=true;for _,l in ipairs(chains[owner]) do lines[#lines+1]=l end end
      else lines[#lines+1]=line end
    end
    st.mangle=table.concat(lines,'\n')..'\n'
    return true
  end
  function run.conntrack_delete(mark) call('conntrack '..mark);return false end
  function run.uci_batch() error('libuci is present in this fake') end
  function run.fenced(rev,fn)
    call('fence')
    if rev~=st.revision then error({code='CLIENT-STOP'}) end
    return fn()
  end
  function run.clock() st.clock=st.clock+0.01;return st.clock end
  function run.wall() st.wall=st.wall+0.1;return st.wall end
  function run.sha256(text) return canon.sha256(text) end
  function run.memory() return {VmRSS=1} end
  function run.fs.read(path) return st.files[path] end
  function run.fs.write_atomic(path,text) call('journal');st.files[path]=text end
  return run,st
end

local function request(direction)
  local value=canon.object({tx='0123456789abcdef0123456789abcdef',phase='APPLYING',
    before=canon.array({'gl_process_vpn','a_5841','a_4192'}),after=canon.array({'gl_process_vpn','a_4192','a_5841'}),
    hash=string.rep('0',64),source='wireguard:peer_1',target='openvpn:1_2',started=canon.float(1761830400.25),
    deadline=canon.float(1761830520.25),trial=false,trial_nonce='pair-1',pid=canon.null,proof_scope='router-probed-ipv4',
    control_revision=REVISION,manual_request_id=string.rep('e',32),manual_instant=true,forward_policy_touched=true,
    rtp_dispatched=true,process_bindings=canon.object({wgclient1=4096,ovpnclient2=45056}),
    pair_transition=canon.object({destination_role='target',direction='first'})})
  return canon.object({direction=direction or 'reserve',control_revision=REVISION,journal=value,
    names=canon.object({gl_process_vpn='gl_process_vpn',a_5841='cfg01',a_4192='cfg02'}),
    tunnel_order=canon.array({'4192','5841'})})
end
local function saved(st) return journal.parse(st.files[journal.PATH]) end

t.test('a switch: journal, one uci session, sync, atomic restore, verify, held',function()
  local run,st=router()
  local result,code=s.switch(run,request(),'reserve')
  t.eq(code,0,'exit code '..tostring(result.code))
  t.eq(result.phase,'HELD-ON-RESERVE');t.eq(result.kernel.changed,true)
  t.eq(st.calls,{'fence','journal','fence','reorder cfg02=1','commit','set gl_process_vpn.via=ovpnclient2',
    'set gl_process_vpn.mark=0xb000','commit','iptables-save','fence','iptables-restore','iptables-save',
    'conntrack 0x1000','fence','journal'})
  local j=saved(st)
  t.eq(j.phase,'HELD-ON-RESERVE');t.eq(j.reason,'OPERATOR-MANUAL');t.eq(j.reserve_healthy,true)
  t.eq(#j.phase_evidence,2);t.truthy(canon.is_float(j.instant_seconds))
  t.truthy(st.mangle:find('TUNNEL4192_ROUTE_POLICY\n%-A ROUTE_POLICY %-m addrtype ! %-%-dst%-type LOCAL %-j TUNNEL5841'),'kernel order')
  t.truthy(st.mangle:find('gid%-owner 20000 %-j MARK %-%-set%-xmark 0xb000/0xf000'),'local mark')
end)

t.test('Stop before the first write: refused, nothing written',function()
  local run,st=router();st.revision=string.rep('d',32)
  local result,code=s.switch(run,request(),'reserve')
  t.eq(code,2);t.eq(result.code,'CLIENT-STOP');t.eq(st.files[journal.PATH],nil)
end)

t.test('wrong direction or a changed policy: refused before apply',function()
  local run,st=router()
  local result,code=s.switch(run,request(),'primary')
  t.eq({code,result.code},{2,'MANUAL-REQUEST-INVALID'});t.eq(st.files[journal.PATH],nil)
  run,st=router();st.config[2]['.name']='cfg09'
  result,code=s.switch(run,request(),'reserve')
  t.eq({code,result.code,result.rollback_required},{2,'POLICY-IDENTITY-CHANGED',false})
  local j=saved(st)
  t.eq({j.phase,j.reason,j.failure_code},{'ROLLED-BACK','FAILED-BEFORE-APPLY','POLICY-IDENTITY-CHANGED'})
end)

t.test('kernel not changed by the restore: APPLYING kept, Python rolls back',function()
  local run,st=router({restore_ignored=true})
  local result,code=s.switch(run,request(),'reserve')
  t.eq({code,result.code,result.rollback_required},{2,'FAST-PATH-UNVERIFIED',true})
  local j=saved(st);t.eq({j.phase,j.failure_code},{'APPLYING','FAST-PATH-UNVERIFIED'})
end)

t.test('a transaction in progress blocks a new switch',function()
  local run,st=router()
  local busy=request().journal;busy.phase='WAIT-CLIENT'
  st.files[journal.PATH]=journal.envelope(busy)
  local result,code=s.switch(run,request(),'reserve')
  t.eq({code,result.code},{2,'TRANSACTION-IN-PROGRESS'})
end)

t.test('unsupported kernel layout: vendor rebuild fallback reported',function()
  local run,st=router();st.mangle=st.mangle:gsub('%-j TUNNEL4192_ROUTE_POLICY\n','-j TUNNEL9999_ROUTE_POLICY\n',1)
  local result,code=s.switch(run,request(),'reserve')
  t.eq({code,result.code,result.fallback,result.rollback_required},{2,'FAST-ROUTE-CHAIN','vendor-rebuild',true})
end)

t.test('reorder moves are those of Linux.reorder',function()
  t.eq((s.reorder_moves({'a','b','c','d'},{'c','a','b','d'})),{{id='c',index=0}})
  t.eq((s.reorder_moves({'a','b','c'},{'c','b','a'})),{{id='c',index=0},{id='b',index=1}})
  t.code('POLICY-IDENTITY-CHANGED',s.reorder_moves,{'a','b'},{'a','c'})
  t.code('UNSAFE-SECTION',s.uci_apply,{},nil,{{id='x',index=0}},{x='bad;name'})
end)

t.test('dry run writes nothing',function()
  local run,st=router()
  local result,code=s.dry_run(run)
  t.eq(code,0);t.eq(result.changed,false);t.eq(result.attest,'verified');t.eq(result.journal,'none')
  for _,c in ipairs(st.calls) do t.truthy(c=='iptables-save','only reads: '..c) end
end)

t.run()
