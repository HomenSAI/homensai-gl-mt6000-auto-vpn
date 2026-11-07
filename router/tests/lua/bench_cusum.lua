-- CPU cost of the sequential detectors per channel and beat, without the socket and sysfs work of the pulse
-- (bench_fast_detect.lua measures the whole beat, with its options 'cusum' and 'rtt').
--   lua5.1 router/tests/lua/bench_cusum.lua [beats]
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..'/usr/lib/homensai-vpn/lua/?.lua;'..package.path
local cusum=require('cusum')
local beats=tonumber(arg[1]) or 2000000

local function measure(name,fn)
  collectgarbage('collect')
  local kb0=collectgarbage('count')
  local c0=os.clock()
  for i=1,beats do fn(i) end
  local c1=os.clock()
  print(string.format('%-34s %6.3f us per beat  %6.4f %% of one core at 2 channels, 1 beat/s  heap +%d KiB',name,(c1-c0)/beats*1e6,(c1-c0)/beats*2*100,collectgarbage('count')-kb0))
end

measure('empty loop',function() end)
local c=cusum.LossCusum()
measure('LossCusum, all answered',function() c:feed(false,'1.1.1.1') end)
local l=cusum.LossCusum()
measure('LossCusum, 30 % lost',function(i) l:feed(i%10<3,i%2==0 and '1.1.1.1' or '8.8.8.8') end)
local w=cusum.RttWatch()
measure('RttWatch, answered',function(i) w:feed(20+i%7,i%2==0 and '1.1.1.1' or '8.8.8.8') end)
