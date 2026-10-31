-- rpc.lua: rpc_input.decode_request rules, read replies from memory, forwarding of writing methods.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local rpc=require('rpc')

local function code(fn,...) local err=t.raises(fn,...);return type(err)=='table' and err.code or tostring(err) end

t.test('decode_request: the codes of rpc_input.decode_request',function()
  t.eq(rpc.decode_request(''),{});t.eq(rpc.decode_request('  \n'),{});t.eq(rpc.decode_request(nil),{})
  t.eq(rpc.decode_request('{"direction":"reserve","ubus_rpc_session":"abc"}'),{direction='reserve'})
  t.eq(code(rpc.decode_request,string.rep(' ',65537)),'RPC-INPUT-SIZE')
  t.eq(code(rpc.decode_request,'{"a":1,"a":2}'),'RPC-DUPLICATE-FIELD')
  t.eq(code(rpc.decode_request,'{"a":NaN}'),'RPC-INPUT-INVALID')
  t.eq(code(rpc.decode_request,'{"a":1e999}'),'RPC-NONFINITE-NUMBER')
  t.eq(code(rpc.decode_request,'{"a":'..string.rep('[',70)..string.rep(']',70)..'}'),'RPC-INPUT-COMPLEXITY')
  t.eq(code(rpc.decode_request,'[1,2]'),'RPC-INPUT-OBJECT')
  t.eq(code(rpc.decode_request,'"x"'),'RPC-INPUT-OBJECT')
  t.eq(code(rpc.decode_request,'{bad json'),'RPC-INPUT-INVALID')
  local wide={};for i=1,10001 do wide['k'..i]=i end
  t.eq(code(rpc.decode_request,wide),'RPC-INPUT-COMPLEXITY')
  t.eq(code(rpc.decode_request,{a=0/0}),'RPC-NONFINITE-NUMBER')
  t.eq(code(rpc.decode_request,{1,2}),'RPC-INPUT-OBJECT')
  local parsed=rpc.decode_request({control_revision='r1',ubus_rpc_session='s'})
  t.eq(parsed,{control_revision='r1'});t.truthy(canon.is_object(parsed))
end)

local function make(status)
  local R=t.fake_runner()
  local native=canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-2,source='wireguard:peer_7',target='wireguard:peer_8',blockers=canon.array({'X-1','bad code'})})
  local state={version='2.0.0-lua-alpha3',now=function() return R.now end,status=function() return status end,
    native_status=function() return native end,inventory=function() return canon.object({profiles=canon.array(),settings=canon.object()}) end}
  return rpc.new(state,R),R,native
end

t.test('status reply: samples trimmed for the page, native_failover attached, history split',function()
  local status=canon.object({version='2.0.0-lua-alpha3',mode='monitor',time=1761825600,
    profiles=canon.array({canon.object({id='wireguard:peer_7',code=canon.null,time=1761825600,https_success=3,dns_ok=true})}),
    samples=canon.array({canon.object({id='wireguard:peer_7',time=1,code=canon.null,rtt_ms=1,https_success=3,dns_ok=true,interface='wgclient',vendor_tunnel_id='wireguard:wgclient',vendor_generation='g'})}),
    events=canon.array({canon.object({time=1,code='OK',profile='wireguard:peer_7'})}),
    accounting=canon.object({months=canon.object(),quality=canon.object({p=canon.object()})}),
    native_history=canon.object({events=canon.array({1,2}),detail_days=7})})
  local handler,R=make(status)
  local reply=handler.handle('status','{}')
  t.eq(reply.samples[1],{id='wireguard:peer_7',time=1,code=canon.null,rtt_ms=1,https_success=3,dns_ok=true})
  t.eq(reply.native_failover.state,'OBSERVING');t.eq(reply.server_time,R.now)
  t.eq(reply.history_split,{'accounting.quality','native_history.events'})
  t.eq(reply.accounting.quality,nil);t.eq(reply.native_history.events,nil)
  t.eq(status.accounting.quality~=nil,true,'the in-memory status is not mutated');t.eq(status.samples[1].interface,'wgclient')
  t.eq(handler.handle('events',nil),{events={{time=1,code='OK',profile='wireguard:peer_7'}}})
  local history=handler.handle('history','{}')
  t.eq(history['accounting.quality'],{p={}});t.eq(history.time,R.now)
  handler,R=make(nil)
  reply=handler.handle('status','{}')
  t.eq(reply.error,'SERVICE-STOPPED');t.eq(reply.version,'2.0.0-lua-alpha3');t.eq(reply.native_failover.state,'OBSERVING')
end)

t.test('auto_live: bounded fields only',function()
  local status=canon.object({time=1761825600,observation_valid_for=30,profiles=canon.array({
    canon.object({id='wireguard:peer_7',code='VPN-003',time=1761825600,https_success=1,dns_ok=false}),
    canon.object({id=string.rep('x',97),code='X'}),canon.object({id='wireguard:peer_8',code='bad code',dns_ok='yes'})})})
  local handler,R,native=make(status)
  local live=handler.handle('auto_live','{}')
  t.eq(live.native_failover.state,'OBSERVING');t.eq(live.native_failover.blockers,{'X-1'});t.eq(live.native_failover.time,R.now-2)
  t.eq(live.time,1761825600);t.eq(live.observation_valid_for,30)
  t.eq(#live.profiles,2);t.eq(live.profiles[1].code,'VPN-003');t.eq(live.profiles[2].code,canon.null);t.eq(live.profiles[2].dns_ok,canon.null)
  native.time=R.now+100
  live=handler.handle('auto_live','{}')
  t.eq(live.native_failover.time,nil,'a future stamp is dropped')
end)

t.test('Python-answered methods give FALLBACK (agent.py answers); setup_* go to the native handler; unknown refused',function()
  local handler,R=make(nil)
  for _,name in ipairs({'native_start','native_stop','fault_start','fault_cancel','setup_monitor','terms_accept','stats_reset'}) do
    t.truthy(handler.handle(name,'{"a":1,"a":2}')==rpc.FALLBACK,name..': the request bytes go to agent.py unchanged')
  end
  -- plan item 4: pair_manual is answered in Lua when the monitor wires a handler, else agent.py answers
  t.truthy(handler.handle('pair_manual','{"direction":"reserve"}')==rpc.FALLBACK,'pair_manual without a handler')
  t.eq(#R.forwards,0,'Lua never starts agent.py itself')
  t.truthy(handler.handle('setup_stats',{mode='work'})==rpc.FALLBACK,'without a setup handler')
  t.eq(handler.handle('reboot','{}'),{error='RPC-UNKNOWN-METHOD'})
  t.eq(handler.handle('setup_probe','{"a":1,"a":2}'),{error='RPC-DUPLICATE-FIELD'},'decode_request first, like agent.rpc')
  t.eq(handler.handle('setup_probe','{bad'),{error='RPC-INPUT-INVALID'})
end)

t.test('bridge call: request file in, canonical reply file out, fallback, path checks',function()
  local handler,R=make(canon.object({version='v',mode='monitor',time=1,profiles=canon.array(),events=canon.array({canon.object({code='OK',time=1})})}))
  R.files['/run/hv/rpc-in.Ab12Cd']='{"ubus_rpc_session":"x"}'
  local answer=handler.bridge_call({method='events',request_file='/run/hv/rpc-in.Ab12Cd',reply_file='/run/hv/rpc-out.Zz99Yy'})
  t.eq(answer,{ok=true})
  t.eq(R.files['/run/hv/rpc-out.Zz99Yy'],'{"events":[{"code":"OK","time":1}]}')
  t.eq(handler.bridge_call({method='pair_manual',request_file='/run/hv/rpc-in.Ab12Cd',reply_file='/run/hv/rpc-out.Zz99Yy'}),{fallback=true})
  t.eq(handler.bridge_call({method='events',request_file='/etc/passwd',reply_file='/run/hv/rpc-out.Zz99Yy'}),{error='RPC-BRIDGE-PATH'})
  t.eq(handler.bridge_call({method='events',request_file='/run/hv/rpc-in.Ab12Cd',reply_file='/run/hv/../x'}),{error='RPC-BRIDGE-PATH'})
  t.eq(handler.bridge_call({method='events',request_file='/run/hv/rpc-in.missing',reply_file='/run/hv/rpc-out.Zz99Yy'}),{error='RPC-BRIDGE-PATH'})
  t.eq(handler.bridge_call({method='Bad;rm',request_file='/run/hv/rpc-in.Ab12Cd',reply_file='/run/hv/rpc-out.Zz99Yy'}),{error='RPC-UNKNOWN-METHOD'})
  R.files['/run/hv/rpc-in.Ab12Cd']='{"a":1,"a":2}'
  t.eq(handler.bridge_call({method='status',request_file='/run/hv/rpc-in.Ab12Cd',reply_file='/run/hv/rpc-out.Zz99Yy'}),{ok=true})
  t.eq(R.files['/run/hv/rpc-out.Zz99Yy'],'{"error":"RPC-DUPLICATE-FIELD"}','input errors keep the Python codes')
end)

t.test('ubus object: native methods registered, for_ubus unboxes floats and drops nulls',function()
  local handler=make(nil)
  local replies={}
  local conn={reply=function(self,req,value) replies[#replies+1]={req,value} end}
  local object=handler.ubus_object(conn,{})
  local methods=object['homensai-vpn-lua']
  t.eq(rpc.OBJECT,'homensai-vpn-lua','the page object homensai-vpn stays with rpcd')
  for _,name in ipairs(rpc.READ) do t.truthy(type(methods[name][1])=='function',name) end
  for _,name in ipairs(rpc.NATIVE) do t.truthy(type(methods[name][1])=='function',name) end
  for _,name in ipairs(rpc.FORWARD) do t.eq(methods[name],nil,name) end
  t.truthy(type(methods.rpc[1])=='function')
  methods.status[1]('req',{})
  t.eq(replies[1][1],'req');t.eq(replies[1][2].error,'SERVICE-STOPPED')
  t.eq(rpc.for_ubus(canon.object({a=canon.float(1.5),b=canon.null,c=canon.array({1,canon.null})})),{a=1.5,c={1}})
end)

t.run()
