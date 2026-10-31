-- CPU cost of one fast-detection beat (Lua plan item 5), measured with os.clock() over many beats.
--   PC (docker, no nixio):  lua5.1 router/tests/lua/bench_fast_detect.lua [beats] [device1] [device2]
--     real sysfs reads of two existing devices (default lo and eth0) through monitor_io.sysfs, a fake socket that
--     answers every echo (the reply is built, received and validated in Lua like on the router).
--   Router (nixio present):  lua bench_fast_detect.lua 2000 wgclient1 ovpnclient2
--     real monitor_io.beat_socket: real raw ICMP echoes through the two tunnels (two packets per beat; the
--     beats run back to back, so most answers are collected one beat later exactly as in the monitor). Read-only.
-- Per beat it runs what the monitor's 1 s timer runs while the switch is on and nothing is suspect:
-- config_mtime (switch cache key), the speed-pause check, Pulse:tick over both channels.
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..'/usr/lib/homensai-vpn/lua/?.lua;'..package.path
local canon=require('canon')
canon.configure({runtime=os.getenv('HOMENSAI_TEST_RUNTIME') or '/tmp'})
local io_=require('monitor_io')
local fast=require('fast_detect')
local probe=require('probe')

local beats=tonumber(arg[1]) or 20000
local d1,d2=arg[2] or 'lo',arg[3] or 'eth0'
local has_nixio=pcall(require,'nixio')

local runner={sysfs=io_.sysfs,random=io_.random,clock=io_.clock,exists=io_.exists,config_mtime=io_.config_mtime}
local sockets='real nixio raw ICMP'
if not has_nixio then
  sockets='fake (answers every echo)'
  local function u16(n) return string.char(math.floor(n/256)%256,n%256) end
  runner.beat_socket=function()
    local inbox={}
    return {send=function(_,target,packet)
      local echo='\0\0'..u16(0)..string.sub(packet,5)
      echo='\0\0'..u16(probe.icmp_checksum(echo))..string.sub(echo,5)
      local a,b,c,d=string.match(target,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
      inbox[#inbox+1]='\69\0'..u16(20+#echo)..u16(1)..u16(0)..'\64\1'..u16(0)..string.char(tonumber(a),tonumber(b),tonumber(c),tonumber(d))..'\10\0\0\2'..echo
      return true
    end,recv=function() return table.remove(inbox,1) end,close=function() end}
  end
else
  runner.beat_socket=io_.beat_socket
end

local function ifindex(dev) return tonumber(io_.sysfs(dev,'ifindex') or '') end
local rows={{id='wireguard:peer_1',device=d1,mark=0x1000,table='53',ifindex=ifindex(d1)},
            {id='wireguard:peer_2',device=d2,mark=0x2000,table='54',ifindex=ifindex(d2)}}
if not rows[1].ifindex or not rows[2].ifindex then io.stderr:write('device not found: ',d1,' ',d2,'\n');os.exit(2) end
local pulse=fast.Pulse(runner,function() return runner.exists('/var/run/homensai-vpn/speed-pause.json') end)
pulse:configure(true,rows,{source='wireguard:peer_1',target='wireguard:peer_2'},'OBSERVING')
local now=0
for _=1,50 do now=now+1;runner.config_mtime();pulse:tick(now) end  -- warm up (sockets opened)
collectgarbage('collect')
local kb0=collectgarbage('count')
local c0=os.clock()
for _=1,beats do now=now+1;runner.config_mtime();pulse:tick(now) end
local c1=os.clock()
local kb1=collectgarbage('count')
local per=(c1-c0)/beats
local p=pulse:public(now,true)
print(canon.encode(canon.object({beats=beats,channels=2,sockets=sockets,devices=canon.array({d1,d2}),
  cpu_us_per_beat=math.floor(per*1e7+0.5)/10,cpu_percent_at_1_beat_per_s=math.floor(per*1e6+0.5)/1e4,
  heap_kb_growth=math.floor(kb1-kb0),replies=canon.array({p.channels[1].replies,p.channels[2].replies}),
  states=canon.array({p.channels[1].state,p.channels[2].state})})))
pulse:close()
