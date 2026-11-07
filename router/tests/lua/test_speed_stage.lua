-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- speed.lua stage(): the Lua twin of speed_test.stage counts the payload a curl transfer moved before the window end
-- once (review F-49), and keeps real cancellation distinct from the window expiry. Python twin: tests/test_speed_test.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local speed=require('speed')

local BINDING={device='wg0',mark=1,table='100'}
-- requests: list of {done=seconds after start, exit=, out='http down up total'}; done=nil means "until the window ends"
local function fake(requests,cancel_at)
  local d={ms=1000000,started={},killed=0}
  function d.clock() return d.ms/1000 end
  function d.sleep(seconds) d.ms=d.ms+math.floor(seconds*1000+0.5) end
  function d.route_get() return canon.decode('[{"dev":"wg0","table":"100"}]') end
  function d.zero_file() return '/tmp/zero' end
  local next_request=1
  function d.curl_start(argv)
    local spec=requests[next_request];next_request=next_request+1
    local handle={spec=spec,argv=argv}
    -- curl -m: the transfer ends at the deadline at the latest
    local limit=tonumber(argv[12]);handle.ends=d.clock()+(spec.done or limit)
    d.started[#d.started+1]=handle
    return handle
  end
  function d.curl_poll(handle)
    if handle.killed then return {exit=143,out=''} end
    if d.clock()+1e-9<handle.ends then return nil end
    return {exit=handle.spec.exit,out=handle.spec.out}
  end
  function d.curl_kill(handle) handle.killed=true;d.killed=d.killed+1 end
  local function cancelled() return cancel_at~=nil and d.clock()>=1000+cancel_at end
  return d,cancelled
end

t.test('window expiry counts the partial payload once: 1 MiB + 0.5 MiB over 3 s = 4.194 Mbps',function()
  local d,cancelled=fake({{done=1.6,exit=0,out='200 1048576 0 1.6'},{exit=28,out='000 524288 0 1.35'}})
  local live={}
  local row=speed.stage(d,BINDING,'9.9.9.9','download',2*speed.MIB,3,1,cancelled,function(mbps,total) live[#live+1]=total end)
  t.eq(row.payload_bytes,1572864);t.eq(canon.number(row.seconds),3);t.eq(canon.number(row.mbps),4.194)
  t.eq(live[#live],1572864,'live and final totals are the same bytes')
end)

t.test('partial upload uses size_upload, bounded by the request',function()
  local d,cancelled=fake({{exit=28,out='000 0 262144 1.0'}})
  local row=speed.stage(d,BINDING,'9.9.9.9','upload',speed.MIB,1,1,cancelled)
  t.eq(row.payload_bytes,262144);t.eq(canon.number(row.seconds),1);t.eq(canon.number(row.mbps),2.097)
  d,cancelled=fake({{exit=28,out='000 0 99999999 1.0'}})
  t.eq(speed.stage(d,BINDING,'9.9.9.9','upload',speed.MIB,1,1,cancelled).payload_bytes,speed.MIB)
end)

t.test('real cancellation inside a partial request is not a window expiry',function()
  local d,cancelled=fake({{done=1.6,exit=0,out='200 1048576 0 1.6'},{exit=28,out='000 524288 0 1.35'}},2.0)
  local err=t.raises(speed.stage,d,BINDING,'9.9.9.9','download',2*speed.MIB,3,1,cancelled)
  t.eq(err.code,'SPEED-CANCELLED')
end)

-- R2-02: a 429/403 body that stalls until curl's exit 28 is an HTTP failure, not payload
t.test('an error reply cut by the window is SPEED-HTTP, its body bytes are never credited',function()
  for _,status in ipairs({'429','403','500'}) do
    local d,cancelled=fake({{exit=28,out=status..' 524288 0 3.0'}})
    t.eq(t.raises(speed.stage,d,BINDING,'9.9.9.9','download',speed.MIB,3,1,cancelled).code,'SPEED-HTTP',status)
  end
  local d,cancelled=fake({{exit=28,out='403 0 262144 1.0'}})
  t.eq(t.raises(speed.stage,d,BINDING,'9.9.9.9','upload',speed.MIB,1,1,cancelled).code,'SPEED-HTTP','upload refused too')
  -- a second stream's 200 payload does not rescue the stage: the failure stands
  d,cancelled=fake({{done=1.6,exit=0,out='200 1048576 0 1.6'},{exit=28,out='429 524288 0 1.35'}})
  t.eq(t.raises(speed.stage,d,BINDING,'9.9.9.9','download',2*speed.MIB,3,1,cancelled).code,'SPEED-HTTP')
end)

t.test('a window expiry with nothing moved is no sample',function()
  local d,cancelled=fake({{exit=28,out='000 0 0 3.0'}})
  t.eq(t.raises(speed.stage,d,BINDING,'9.9.9.9','download',speed.MIB,3,1,cancelled).code,'SPEED-NO-SAMPLE')
end)

t.run()
