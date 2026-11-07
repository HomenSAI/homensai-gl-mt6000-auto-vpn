-- CPU cost of the pure GL-sensor functions (GL-SENSORS-2026-11-04.ru.md), os.clock() over many calls. Read-only.
--   lua5.1 router/tests/lua/bench_gl_sensors.lua        (PC/docker or the router: lua bench_gl_sensors.lua)
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..'/usr/lib/homensai-vpn/lua/?.lua;'..package.path
local wan=require('wan_diag')
local stall=require('stall')
local boot=require('boot_cause')
local bundle=require('diag_bundle')
local function bench(name,n,fn)
  collectgarbage('collect')
  local c0=os.clock()
  for i=1,n do fn(i) end
  local per=(os.clock()-c0)/n
  print(string.format('%-34s %10.2f us per call',name,per*1e6))
end
local ev={underlay='fail',link='up',kmwan='online',portal='no',primary='bad',reserve='bad',wg='timeout'}
bench('wan_diag.diagnose (7 factors)',20000,function() wan.diagnose(ev,true) end)
local s=stall.Stall()
bench('stall.feed',200000,function(i) s:feed(i,1000+i*100,2000+i*50) end)
local log=string.rep('<6>[ 1.2] crash record line with some text\n',6000)  -- about 256 KB
bench('boot_cause.fingerprint 256 KB (boot)',5,function() boot.fingerprint(log) end)
local text=string.rep("network.wgclient1.private_key='aGVsbG8gd29ybGQgdGhpcyBpcyBhIHRlc3Qga2V5MTI='\n  endpoint: 203.0.113.7:51820\n",5000)
bench('diag_bundle.mask 0.5 MB (on demand)',2,function() bundle.mask(text) end)
