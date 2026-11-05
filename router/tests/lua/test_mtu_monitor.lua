-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- The large-packet check through the real Lua monitor wiring: monitor.lua passes (start_pass -> probe.probe with
-- the monitor's mtu argument -> mtu_check.run -> vendor.lua -> status.json and the ubus status reply) with the REAL
-- monitor_io.datagram and monitor_io.sysfs underneath. Only the kernel is fake: nixio raw ICMP sockets bound to a
-- device (every echo is answered and delivered to each raw socket of that device, as Linux does), a uloop that
-- delivers readable sockets and timers, and a sysfs directory.
-- Router finding 03.11.2026 (MT3000, 2.1.0-alpha7, soak primary-mtu-long): `oifname wgclient1 meta length > 1300
-- drop` on the OUTPUT hook refused the monitor's large sends with EPERM, every check was 'unavailable' (no VPN-MTU,
-- no switch), and the field appeared in status.json only on the one pass in 300 s that measured.
-- Python twin: tests/test_mtu_check.py MonitorLoopIntegration.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local u16,be16=t.u16,t.be16

local function quad(text) local a,b,c,d=string.match(text,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$');return string.char(tonumber(a),tonumber(b),tonumber(c),tonumber(d)) end

-- fake kernel ---------------------------------------------------------------------------------------------------
local net={sockets={},next_fd=100,firewall={},sent={}}
local function checksum(data)
  if #data%2==1 then data=data..'\0' end
  local total=0
  for i=1,#data,2 do total=total+be16(data,i) end
  while total>=65536 do total=(total%65536)+math.floor(total/65536) end
  return 65535-total
end
local nixio={}
function nixio.socket(family,kind,proto)
  assert(family=='inet' and kind=='raw' and proto=='icmp','the fake kernel only has raw ICMP sockets')
  local s={inbox={},fd=net.next_fd}
  net.next_fd=net.next_fd+1
  function s:setopt(level,name,value) if level=='socket' and name=='bindtodevice' then self.device=value;return true end;return nil,22 end
  function s:setblocking() return true end
  function s:fileno() return self.fd end
  function s:sendto(packet,host,port)
    local size=#packet+20
    local limit=net.firewall[self.device]
    if limit and size>limit then return nil,1,'Operation not permitted' end  -- nft OUTPUT drop: EPERM to the sender
    net.sent[#net.sent+1]={device=self.device,host=host,size=size,mtu=string.sub(packet,9,14)=='HV-MTU'}
    local echo='\0\0'..u16(0)..string.sub(packet,5)
    echo='\0\0'..u16(checksum(echo))..string.sub(echo,5)
    local reply='\69\0'..u16(20+#echo)..u16(1)..u16(0)..'\64\1'..u16(0)..quad(host)..quad('10.2.0.2')..echo
    for _,other in pairs(net.sockets) do
      if other.device==self.device then other.inbox[#other.inbox+1]={reply,host} end
    end
    return #packet
  end
  function s:recvfrom(n)
    local item=table.remove(self.inbox,1)
    if not item then return false,11 end
    return string.sub(item[1],1,n),item[2],0
  end
  function s:close() net.sockets[self.fd]=nil end
  net.sockets[s.fd]=s
  return s
end

local loop={ULOOP_READ=1,fds={},timers={},now=0}
function loop.fd_add(fd,cb)
  local handle={}
  function handle:delete() loop.fds[fd]=nil end
  loop.fds[fd]=cb
  return handle
end
function loop.timer(cb)
  local timer={}
  function timer:set(ms) self.at=loop.now+ms;loop.timers[self]=cb end
  function timer:cancel() loop.timers[self]=nil end
  return timer
end
local function run_loop()
  for _=1,100000 do
    local ready
    for fd,cb in pairs(loop.fds) do local s=net.sockets[fd];if s and #s.inbox>0 then ready=cb;break end end
    if ready then ready()
    else
      local first
      for timer in pairs(loop.timers) do if not first or timer.at<first.at then first=timer end end
      if not first then return end
      local cb=loop.timers[first];loop.timers[first]=nil;loop.now=first.at;cb()
    end
  end
  error('the fake loop did not settle')
end

-- the real monitor_io over the fake kernel
package.loaded['nixio']=nixio
package.loaded['monitor_io']=nil
local mio=require('monitor_io')
mio.attach_loop(loop)
local base='/tmp/homensai-mtu-monitor-'..tostring(os.time())..'-'..tostring(math.random(100000))
mio.configure({SYS_NET=base})
local monitor=require('monitor')

local function write(path,text)
  os.execute('mkdir -p '..string.match(path,'^(.*)/[^/]*$'))
  local f=assert(io.open(path,'wb'));f:write(text);f:close()
end

local function fresh()
  net.sockets={};net.firewall={};net.sent={}
  local R=t.fake_runner()
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  -- sysfs: the harness counters, plus the tunnel MTUs (WireGuard primary 1350 as on the MT3000, reserve 1420)
  for device,row in pairs(R.counters) do
    write(base..'/'..device..'/ifindex',row.ifindex..'\n')
    write(base..'/'..device..'/statistics/rx_bytes',row.rx..'\n');write(base..'/'..device..'/statistics/tx_bytes',row.tx..'\n')
  end
  write(base..'/wgclient/mtu','1350\n');write(base..'/wgclient2/mtu','1420\n')
  R.sysfs=mio.sysfs
  local fake=R.datagram
  function R.datagram(kind,...)
    if kind=='icmp' then return mio.datagram(kind,...) end
    return fake(kind,...)  -- the DNS question stays the harness answer
  end
  function R.drain() run_loop() end
  return R,monitor.new(R)
end

local function row(status,id) for _,p in ipairs(status.profiles) do if p.id==id then return p end end end
-- echoes of the large-packet check (payload HV-MTU; the ping sampler's HV-PING echoes are not counted)
local function checks(device,small)
  local n=0
  for _,s in ipairs(net.sent) do if s.mtu and (device==nil or s.device==device) and (small or s.size>64) then n=n+1 end end
  return n
end
local function large(device) return checks(device,false) end

t.test('the status carries the check on every pass and a firewall black hole becomes VPN-MTU',function()
  local R,m=fresh()
  local wall=math.floor(R.now)
  local function pass()
    net.sent={}
    local status=m:pass()
    local written=canon.decode(R.files['/run/hv/status.json'])
    local p=row(written,'wireguard:peer_7')
    t.eq(row(status,'wireguard:peer_7').mtu_check,canon.plain(p.mtu_check),'memory and status.json agree')
    return p,written,status
  end
  -- pass 1: the first probe of each channel is checked (six echoes each)
  local p,written=pass()
  t.eq(canon.plain(p.mtu_check),{state='ok',size=1350,time=wall});t.eq(p.code,canon.null)
  t.eq(canon.plain(row(written,'wireguard:peer_8').mtu_check),{state='ok',size=1420,time=wall})
  t.eq(large('wgclient'),4);t.eq(large('wgclient2'),4)
  -- pass 2, 10 s later: no new measurement, the last reading is still published
  R.advance(10)
  p=pass()
  t.eq(canon.plain(p.mtu_check),{state='ok',size=1350,time=wall});t.eq(checks(nil,true),0,'nothing sent between checks')
  -- the fault starts: the router's own firewall drops every packet longer than 1300 bytes into the primary
  net.firewall.wgclient=1300
  R.advance(10)
  p=pass()
  t.eq(canon.plain(p.mtu_check),{state='ok',size=1350,time=wall},'the next check is not due yet');t.eq(p.code,canon.null)
  -- 300 s after the first check: due; the large sends are refused (EPERM), the small echoes come back
  R.advance(300)
  local status
  p,written,status=pass()
  t.eq(canon.plain(p.mtu_check),{state='black-hole',size=1350,time=wall+320});t.eq(p.code,'VPN-MTU')
  t.eq(p.https_success,3);t.eq(p.dns_ok,true)
  t.eq(large('wgclient'),0,'the refused large echoes never left');t.eq(checks('wgclient',true),2,'only the two small echoes');t.eq(checks('wgclient2',true),6,'the reserve is due too')
  t.eq(row(written,'wireguard:peer_8').code,canon.null)
  local seen=false
  for _,e in ipairs(written.events) do if e.profile=='wireguard:peer_7' and e.code=='VPN-MTU' then seen=true end end
  t.truthy(seen,'the changed verdict is an event')
  t.eq(m.rpc.handle('status','{}').profiles[1].mtu_check.state,'black-hole','the ubus status reply carries it')
  -- a suspected black hole is measured again on every probe
  R.advance(10)
  p=pass()
  t.eq(canon.plain(p.mtu_check),{state='black-hole',size=1350,time=wall+330});t.eq(p.code,'VPN-MTU')
  -- the fault is removed: the next probe measures and passes
  net.firewall.wgclient=nil
  R.advance(10)
  p=pass()
  t.eq(canon.plain(p.mtu_check),{state='ok',size=1350,time=wall+340});t.eq(p.code,canon.null);t.eq(large('wgclient'),4)
  t.eq(next(loop.timers),nil,'every socket deadline was cancelled or fired');t.eq(next(net.sockets),nil,'every socket closed')
end)

t.test('any other send failure stays unavailable and never fails the probe',function()
  local R,m=fresh()
  local send=nixio.socket
  nixio.socket=function(...) local s=send(...);function s:sendto() return nil,101,'Network is unreachable' end;return s end
  local ok,err=pcall(function()
    local p=row(m:pass(),'wireguard:peer_7')
    t.eq(p.mtu_check.state,'unavailable');t.eq(p.code,canon.null)
  end)
  nixio.socket=send
  if not ok then error(err,0) end
end)

t.test('cleanup',function() os.execute('rm -rf '..base) end)

t.run()
