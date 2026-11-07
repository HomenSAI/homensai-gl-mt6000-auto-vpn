-- monitor.lua + server_pin.lua: every pass publishes status.server_keys; a healthy channel's first check pins its key
-- (history event), the same server with another key is a change (event, syslog line). Python twin:
-- tests/test_agent_server_pin.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local monitor=require('monitor')
local sp=require('server_pin')

local KEY_A='q3Yp1E6rM2u1Lr0m8X4h6c8w2T5fW1kJ9Zx0bVnAs0E='
local KEY_B='Bz7Q0mYk4sV8pT2xR6wN1cL5dH9fJ3gA0eU7iO4yK2w='

local function fresh(config)
  local R=t.fake_runner()
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  R.files[sp.CONFIG]=config
  R.key=KEY_A;R.execs={}
  function R.exec(argv)
    local line=table.concat(argv,' ');R.execs[#R.execs+1]=line
    if line=='uci -q get network.wgclient2.config' then return 0,'peer_8\n' end
    if line=='wg show wgclient2 endpoints' then return 0,R.key..'\t185.1.1.1:51820\n' end
    if line=='uci -q show wireguard.peer_8' then return 0,"wireguard.peer_8=peers\nwireguard.peer_8.name='de8.nordvpn.com'\n" end
    return 1,''
  end
  return R,monitor.new(R)
end

local function key_events(status)
  local out={}
  for _,e in ipairs(status.events) do if string.sub(e.code,1,10)=='SERVER-KEY' then out[#out+1]=e.code..' '..tostring(e.profile) end end
  return out
end

t.test('first use pins, the same server with another key is a change, enforce is published',function()
  local R,m=fresh("\toption server_key_pin 'enforce'\n")
  local status=m:pass()
  t.eq(key_events(status),{'SERVER-KEY-PINNED wireguard:peer_8'})
  t.eq(status.server_keys.mode,'enforce');t.eq(status.server_keys.pinned,1);t.eq(status.server_keys.code,canon.null)
  local written=canon.decode(R.files[m.runtime..'/'..sp.STATE])
  t.truthy(written.records['wireguard:peer_8|de8.nordvpn.com']~=nil,'RAM state written')
  t.truthy(R.files[m.persist..'/'..sp.STATE]~=nil,'first record reaches the flash file')
  R.key=KEY_B;R.advance(sp.RECHECK)
  status=m:pass()
  t.eq(key_events(status),{'SERVER-KEY-PINNED wireguard:peer_8','SERVER-KEY-CHANGED wireguard:peer_8'})
  t.eq(status.server_keys.code,'SERVER-KEY-CHANGED');t.eq(status.server_keys.changed[1].observed,'wg:'..KEY_B)
  local published=canon.decode(R.files['/run/hv/status.json'])
  t.eq(published.server_keys.changed[1].host,'de8.nordvpn.com')
end)

t.test('off: nothing is read, only the mode is published',function()
  local R,m=fresh("\toption server_key_pin 'off'\n")
  local status=m:pass()
  t.eq(canon.encode(status.server_keys),'{"mode":"off"}')
  for _,line in ipairs(R.execs) do t.truthy(not string.find(line,'wg show',1,true),'no wg call when off') end
  t.eq(key_events(status),{})
end)

t.run()
