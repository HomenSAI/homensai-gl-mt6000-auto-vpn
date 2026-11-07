-- CPU cost of the per-target probe log (docs/architecture/PER-TARGET-PROBE-LOG-2026-11-04.ru.md), measured with os.clock().
--   PC / container:  lua5.1 router/tests/lua/bench_probe_target_log.lua [passes] [directory]
--   Router (nixio present, read-only apart from the file in the given directory):
--     lua bench_probe_target_log.lua 20000 /tmp/ptl-bench
-- Per pass it runs what the monitor adds for the log: two Auto channels -> two encoded lines -> ONE append to the RAM
-- file through the real monitor_io.append (durable.append) with the real rotation. For scale it also times what a pass
-- already does in Lua anyway: canon.encode of a status of the same two channels (status.json is written every pass),
-- and the RPC replies (rare). The heartbeat counting is measured by bench_fast_detect.lua before/after.
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..'/usr/lib/homensai-vpn/lua/?.lua;'..package.path
local canon=require('canon')
canon.configure({runtime=os.getenv('HOMENSAI_TEST_RUNTIME') or '/tmp'})
local io_=require('monitor_io')
local log=require('probe_target_log')

local passes=tonumber(arg[1]) or 20000
local directory=arg[2] or '/tmp/ptl-bench'
os.execute('mkdir -p '..directory..' && rm -f '..directory..'/probe-targets.log '..directory..'/probe-targets.log.1')

local function row(id)
  return {id=id,time=1762243200.4,code=canon.null,dns_ok=true,https_success=3,rtt_ms=canon.float(97.5),
    probe_checks=canon.array({canon.object({target='one.one.one.one',result='ok',elapsed_ms=143.5,http_status=200}),
      canon.object({target='dns.google',result='ok',elapsed_ms=61.2,http_status=200}),
      canon.object({target='dns.quad9.net',result='ok',elapsed_ms=88.0,http_status=200})})}
end
local results={row('wireguard:peer_7'),row('wireguard:peer_8')}
local hb={['wireguard:peer_7']={5,0,5,1,0,0,0,0},['wireguard:peer_8']={5,0,5,0,0,0,0,0}}
local runner={read_file=io_.read_file,append=io_.append,rename=io_.rename}
local writer=log.Writer(runner,directory)

for _=1,200 do writer:record(results,hb,false,1762243200) end  -- warm up
collectgarbage('collect')
local kb0=collectgarbage('count')
local c0=os.clock()
for i=1,passes do writer:record(results,hb,false,1762243200+i) end
local c1=os.clock()
local kb1=collectgarbage('count')
local per_pass=(c1-c0)/passes

-- encode only (no file)
local e0=os.clock()
for i=1,passes do for _,r in ipairs(results) do log.encode(i,r,false,hb[r.id],1762243200) end end
local e1=os.clock()
local per_encode=(e1-e0)/passes/2

-- the status.json encode of the same two channels, once per pass in the monitor
local status=canon.object({version='x',mode='monitor',time=1762243200.5,profiles=canon.array({
  canon.object({id='wireguard:peer_7',code=canon.null,https_success=3,dns_ok=true,probe_checks=results[1].probe_checks,time=1762243200.4}),
  canon.object({id='wireguard:peer_8',code=canon.null,https_success=3,dns_ok=true,probe_checks=results[2].probe_checks,time=1762243200.4})})})
local s0=os.clock()
local n=math.max(200,math.floor(passes/10))
for _=1,n do canon.encode(status) end
local s1=os.clock()
local per_status=(s1-s0)/n

-- the RPC reply: a poll of the newest rows (what the soak kit does once per cycle: 60 rows of a full ring of about
-- 3000 lines), a default page and the largest page
local lines={}
for i=1,3000 do lines[#lines+1]=log.encode(i,results[i%2+1],false,hb[results[i%2+1].id],1762243200) end
local old,new=table.concat(lines,'',1,1500),table.concat(lines,'',1501,3000)
local function reply_cost(after,limit,rounds)
  local r0=os.clock()
  for _=1,rounds do canon.encode(log.select(old,new,after,limit)) end
  return (os.clock()-r0)/rounds
end
local per_poll,per_page,per_max=reply_cost(2940,200,100),reply_cost(0,200,50),reply_cost(0,1000,20)

local size=0
for _,name in ipairs({'probe-targets.log','probe-targets.log.1'}) do
  local f=io.open(directory..'/'..name,'rb');if f then size=size+f:seek('end');f:close() end
end
print(canon.encode(canon.object({passes=passes,channels_per_pass=2,
  cpu_us_per_pass=math.floor(per_pass*1e7+0.5)/10,cpu_us_per_line_encode=math.floor(per_encode*1e7+0.5)/10,
  cpu_us_status_json_encode_per_pass=math.floor(per_status*1e7+0.5)/10,
  cpu_ms_rpc_poll_60_rows_of_3000=math.floor(per_poll*1e4+0.5)/10,cpu_ms_rpc_page_200_rows=math.floor(per_page*1e4+0.5)/10,
  cpu_ms_rpc_page_1000_rows=math.floor(per_max*1e4+0.5)/10,
  cpu_percent_at_one_pass_per_10_s=math.floor(per_pass/10*1e8+0.5)/1e6,
  cpu_percent_at_one_pass_per_2_s=math.floor(per_pass/2*1e8+0.5)/1e6,
  heap_kb_growth=math.floor(kb1-kb0),ring_bytes=size,nixio=pcall(require,'nixio')})))
