-- probe.lua: DNS/HTTPS/ICMP packet rules, route binding and the probe verdicts, with a fake runner.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local probe=require('probe')

t.test('dns question/answer wire format and validation',function()
  local R=t.fake_runner()
  local token,packet,question=probe.dns_question(R)
  t.eq(#token,2);t.eq(#packet,12+#question);t.eq(string.sub(packet,3,4),t.u16(0x100))
  t.eq(question,'\7example\3com\0'..t.u16(1)..t.u16(1))
  local answer=t.dns_answer(packet)
  t.truthy(probe.valid_dns(answer,token))
  t.truthy(not probe.valid_dns(answer,'\0\0'),'wrong token')
  local truncated=string.sub(answer,1,2)..t.u16(0x8380)..string.sub(answer,5)
  t.truthy(not probe.valid_dns(truncated,token),'TC bit refused')
  local servfail=string.sub(answer,1,2)..t.u16(0x8182)..string.sub(answer,5)
  t.truthy(not probe.valid_dns(servfail,token),'rcode refused')
  local noanswer=string.sub(answer,1,6)..t.u16(0)..string.sub(answer,9)
  t.truthy(not probe.valid_dns(noanswer,token),'no answers refused')
  t.truthy(not probe.valid_dns(string.sub(answer,1,11),token),'short refused')
  t.truthy(t.dns_now(R,'wgclient'))
  t.eq(R.last_udp,{device='wgclient',host='9.9.9.9',port=53},'device-bound only: no mark on the socket')
  R.dns_fail='timeout'
  t.eq(t.dns_now(R,'wgclient'),false)
  t.raises(probe.dns_probe,R,'bad device!',function() end)
end)

t.test('urlsafe base64 matches Python base64.urlsafe_b64encode without padding',function()
  t.eq(probe.urlsafe_b64('\0\0\1\0\0\1\0\0\0\0\0\0'),'AAABAAABAAAAAAAA')
  t.eq(probe.urlsafe_b64('\251\255'),'-_8')
  t.eq(probe.urlsafe_b64('a'),'YQ')
end)

t.test('HTTP response parsing: content-length, chunked, status',function()
  local r=probe.parse_http('HTTP/1.1 200 OK\r\nContent-Length: 5\r\nX: y\r\n\r\nhelloEXTRA')
  t.eq(r.status,200);t.eq(r.body,'hello');t.eq(r.headers.x,'y')
  r=probe.parse_http('HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n2\r\nde\r\n0\r\n\r\n')
  t.eq(r.body,'abcde')
  r=probe.parse_http('HTTP/1.1 426 Upgrade Required\r\n\r\n')
  t.eq(r.status,426)
  t.eq(probe.parse_http('garbage'),nil)
  t.eq(probe.parse_http('HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nzz\r\n'),nil)
end)

t.test('https probe: three target kinds, exit address, status handling',function()
  local R=t.fake_runner()
  local sink,detail={},{}
  local rtt=t.https_now(R,'wgclient',probe.TARGETS[1],detail,sink)
  t.truthy(rtt~=nil);t.eq(detail.result,'ok');t.eq(detail.http_status,200);t.eq(detail.target,'one.one.one.one');t.eq(sink.wgclient,{ip='93.184.216.34',country='DE'})
  t.eq(R.last_https.path,'/cdn-cgi/trace');t.eq(R.last_https.hostname,'one.one.one.one');t.eq(R.last_https.address,'1.1.1.1');t.eq(R.last_https.seconds,6)
  R.exit_ip='10.1.2.3';sink={}
  t.https_now(R,'wgclient',probe.TARGETS[1],{},sink)
  t.eq(sink.wgclient,nil,'private exit address is never recorded')
  detail={}
  t.truthy(t.https_now(R,'wgclient',probe.TARGETS[2],detail)~=nil);t.eq(detail.result,'ok')
  detail={}
  t.truthy(t.https_now(R,'wgclient',probe.TARGETS[3],detail)~=nil);t.eq(detail.result,'ok')
  t.truthy(string.find(R.last_https.path,'^/dns%-query%?dns=[A-Za-z0-9_-]+$'))
  R.https_status=426;detail={}
  t.eq(t.https_now(R,'wgclient',probe.TARGETS[1],detail),nil);t.eq(detail.result,'http-unsupported');t.eq(detail.http_status,426)
  R.https_status=500;detail={}
  t.eq(t.https_now(R,'wgclient',probe.TARGETS[1],detail),nil);t.eq(detail.result,'http-error')
  R.https_status=200;R.https_fail['1.1.1.1']='tls-error';detail={}
  t.eq(t.https_now(R,'wgclient',probe.TARGETS[1],detail),nil);t.eq(detail.result,'tls-error');t.truthy(detail.elapsed_ms~=nil)
  R.https_fail={}
  R.https_reply=function() return {status=200,body='abc'} end
  detail={}
  t.eq(t.https_now(R,'wgclient',probe.TARGETS[1],detail),nil);t.eq(detail.result,'invalid-response')
end)

t.test('route binding: device, mark, table and ifindex; the Python refusal codes',function()
  local R=t.fake_runner()
  t.eq(probe.route_binding(R,'wgclient'),{device='wgclient',mark=4096,table='53',ifindex=20})
  R.interfaces.wgclient.up=false
  t.eq(probe.route_binding(R,'wgclient'),{code='VPN-001'})
  R.interfaces.wgclient.up=true;R.interfaces.wgclient.l3_device='bad/dev'
  t.eq(probe.route_binding(R,'wgclient'),{code='ROUTE-001'})
  R.interfaces.wgclient.l3_device='wgclient';R.marks.wgclient=nil
  t.eq(probe.route_binding(R,'wgclient').code,'CHECK-001')
  R.marks.wgclient={mark=0x1000,table='53'};R.marks.wgclient2={mark=0x2000,table='53'}
  R.interfaces.wgclient2.l3_device='wgclient'
  t.eq(probe.route_binding(R,'wgclient').code,'CHECK-001','two marks for one table')
  R=t.fake_runner()
  local original=R.command
  R.command=function(name,a,b) if name=='route_get' then return canon.encode(canon.array({canon.object({dst=a,dev='eth0'})})) end;return original(name,a,b) end
  t.eq(probe.route_binding(R,'wgclient'),{code='ROUTE-001',device='wgclient'})
  R=t.fake_runner();R.counters.wgclient=nil
  t.raises(probe.route_binding,R,'wgclient')
  t.eq(probe.route_binding(R,'../x'),{code='ROUTE-001'})
end)

t.test('probe verdicts: OK, VPN-003, DNS-001, identity change, inactive, system failure',function()
  local R=t.fake_runner()
  local profile=R.inventory_data.profiles[1]
  local result=t.probe_now(R,profile)
  t.eq(result.code,nil);t.eq(result.https_success,3);t.eq(result.dns_ok,true);t.eq(result.exit_ip,'93.184.216.34')
  t.eq(result.device,'wgclient');t.eq(result.mark,4096);t.eq(result.ifindex,20);t.eq(result.scope,'router-originated');t.eq(result.lan_path_verified,false)
  t.eq(#result.probe_checks,3);t.eq(result.probe_checks[2].target,'dns.google');t.eq(result.administrative_state,'enabled')
  t.truthy(type(result.rtt_ms)=='number')
  R.https_fail['1.1.1.1']='timeout';R.https_fail['8.8.8.8']='transport-error'
  result=t.probe_now(R,profile)
  t.eq(result.code,'VPN-003');t.eq(result.https_success,1);t.eq(result.exit_ip,nil);t.eq(result.probe_checks[1].result,'timeout')
  R.https_fail={};R.dns_fail='timeout'
  result=t.probe_now(R,profile)
  t.eq(result.code,'DNS-001');t.eq(result.dns_ok,false);t.eq(result.https_success,3)
  R.dns_fail=false
  local calls=0;local original=R.command
  R.command=function(name,a,b)
    if name=='iface_status' then calls=calls+1;if calls>1 then return canon.encode(canon.object({up=true,l3_device='wgclient2',proto='wgclient'})) end end
    return original(name,a,b)
  end
  result=t.probe_now(R,profile)
  t.eq(result.code,'VENDOR-IDENTITY-CHANGED');t.eq(result.https_success,nil);t.eq(result.probe_checks,nil)
  R.command=original
  t.eq(t.probe_now(R,R.inventory_data.profiles[3]).code,'PROFILE-INACTIVE')
  t.eq(t.probe_now(R,{id='x',interface='wgclient',administrative_state='disabled'}).code,'PROFILE-INACTIVE')
  R.command=function() return nil,'COMMAND-FAILED' end
  t.eq(t.probe_now(R,profile).code,'SYSTEM-001')
end)

t.test('probe_profiles: anchors first, enabled before unknown, disabled and detached excluded, limit',function()
  local settings={probe_limit=2,plan_source_tunnel='wireguard:wgclient2'}
  local profiles={{id='a',interface='x',administrative_state='unknown',vendor_tunnel_id='wireguard:x'},
    {id='b',interface='y',administrative_state='enabled',vendor_tunnel_id='wireguard:y'},
    {id='c',interface='wgclient2',administrative_state='unknown',vendor_tunnel_id='wireguard:wgclient2'},
    {id='d',interface=canon.null,administrative_state='enabled'},{id='e',interface='z',administrative_state='disabled'}}
  local chosen=probe.probe_profiles(profiles,settings)
  t.eq(#chosen,2);t.eq(chosen[1].id,'c');t.eq(chosen[2].id,'b')
  settings.probe_limit=16
  chosen=probe.probe_profiles(profiles,settings)
  t.eq(#chosen,3);t.eq(chosen[3].id,'a')
end)

t.test('icmp packet, checksum and reply validation',function()
  local R=t.fake_runner()
  local packet,identifier,sequence,payload=probe.icmp_packet(R)
  t.eq(#packet,8+#payload);t.eq(string.byte(packet,1),8);t.eq(probe.icmp_checksum(packet),0,'checksum of a checksummed packet is zero')
  t.eq(string.sub(payload,1,8),'HV-PING\0')
  local echo='\0\0'..t.u16(0)..t.u16(identifier)..t.u16(sequence)..payload
  echo='\0\0'..t.u16(probe.icmp_checksum(echo))..string.sub(echo,5)
  local total=20+#echo
  local ip='\69\0'..t.u16(total)..t.u16(1)..t.u16(0)..'\64\1'..t.u16(0)..'\1\1\1\1'..'\192\168\8\1'
  t.truthy(probe.valid_reply(ip..echo,identifier,sequence,payload,'1.1.1.1'))
  t.truthy(not probe.valid_reply(ip..echo,identifier,sequence,payload,'8.8.8.8'),'source must be the target')
  t.truthy(not probe.valid_reply(ip..echo,identifier+1,sequence,payload,'1.1.1.1'),'identifier')
  local bad=string.sub(ip..echo,1,-2)..string.char((string.byte(payload,-1)+1)%256)
  t.truthy(not probe.valid_reply(bad,identifier,sequence,payload,'1.1.1.1'),'payload/checksum')
  local fragment='\69\0'..t.u16(total)..t.u16(1)..t.u16(0x2000)..'\64\1'..t.u16(0)..'\1\1\1\1'..'\192\168\8\1'
  t.truthy(not probe.valid_reply(fragment..echo,identifier,sequence,payload,'1.1.1.1'),'fragment flags refused')
end)

t.test('ping sampler: selected pair only, cadence, identity checks, cached rows',function()
  local R=t.fake_runner()
  local sampler=probe.PingSampler(R,function(logical) return probe.route_binding(R,logical) end)
  local function row(id,iface,gen)
    return {id=id,protocol='wireguard',interface=iface,vendor_tunnel_id='wireguard:'..iface,vendor_generation=gen,
      administrative_state='enabled',vendor_state='SETTLED',device=iface,mark=R.marks[iface].mark,table=R.marks[iface].table,ifindex=R.counters[iface].ifindex,time=R.now}
  end
  local rows={row('wireguard:peer_7','wgclient',string.rep('a',32)),row('wireguard:peer_8','wgclient2',string.rep('b',32)),{id='openvpn:1_2'}}
  sampler:apply(rows,{source='wireguard:peer_7',target='wireguard:peer_8'},R.now)
  t.eq(rows[1].ping.state,'ok');t.eq(rows[1].ping.rtt_ms,12.3);t.eq(rows[1].ping.code,canon.null);t.eq(rows[1].ping.metric,'icmp-rtt-ms');t.eq(rows[1].ping.backend,'nixio-raw')
  t.eq(rows[2].ping.state,'ok');t.eq(rows[3].ping.code,'PING-NOT-SELECTED')
  t.eq(R.last_icmp.target,'1.1.1.1')
  R.icmp_rtt=nil;R.icmp_kind='timeout'
  R.advance(5)
  rows={row('wireguard:peer_7','wgclient',string.rep('a',32)),row('wireguard:peer_8','wgclient2',string.rep('b',32))}
  sampler:apply(rows,{source='wireguard:peer_7',target='wireguard:peer_8'},R.now)
  t.eq(rows[1].ping.state,'ok','cached within the interval, no new echo')
  R.advance(30)
  rows={row('wireguard:peer_7','wgclient',string.rep('a',32)),row('wireguard:peer_8','wgclient2',string.rep('b',32))}
  sampler:apply(rows,{source='wireguard:peer_7',target='wireguard:peer_8'},R.now)
  t.eq(rows[1].ping.state,'failed');t.eq(rows[1].ping.code,'PING-FAILED')
  rows={row('wireguard:peer_7','wgclient','short')}
  sampler:apply(rows,{source='wireguard:peer_7'},R.now)
  t.eq(rows[1].ping.code,'PING-UNAVAILABLE','invalid generation: no signature')
  rows={row('wireguard:peer_7','wgclient',nil)};rows[1].vendor_state='CHANGING'
  sampler:apply(rows,{source='wireguard:peer_7'},R.now)
  t.eq(rows[1].ping.code,'PING-UNAVAILABLE','a present vendor_state must be SETTLED')
  rows={row('wireguard:peer_7','wgclient',string.rep('a',32))};rows[1].time=R.now-500
  sampler:apply(rows,{source='wireguard:peer_7'},R.now)
  t.eq(rows[1].ping.code,'PING-DATA-STALE')
  R.icmp_rtt=5;R.icmp_kind=nil;R.advance(60)
  R.marks.wgclient.mark=0x3000  -- the kernel binding changed under the row snapshot
  rows={row('wireguard:peer_7','wgclient',string.rep('a',32))};rows[1].mark=0x1000
  sampler:apply(rows,{source='wireguard:peer_7'},R.now)
  t.eq(rows[1].ping.code,'PING-IDENTITY-CHANGED')
end)

t.run()
