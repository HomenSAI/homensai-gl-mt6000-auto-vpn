-- CPU of the network advisor in Lua (not a test): the nightly recommendation over 7 and 30 days of the synthetic
-- journals, the journal's per-pass cost and the monitor part's status field. Multiply by 5-10 for the MT3000.
--   lua5.1 router/tests/lua/bench_advisor.lua
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..here..'/stubs/?.lua;'..here..'/?.lua;'..package.path
local canon=require('canon')
local A=require('advisor')
local J=require('netjournal')
local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.plain(canon.decode(read_file(here..'/../advisor_cases.json')))
local CURVE=A.load_curve(here..'/../../files/usr/lib/homensai-vpn/slider_curve.json')
local SIM=require('advisor_sim').new(CASES)

local function clock() return os.clock() end
local results={}
for _,case in ipairs({{'blips',7,7},{'long',7,7},{'long',30,30},{'flappy',30,30}}) do
  local name,days,window=case[1],case[2],case[3]
  local t0=clock()
  local journal=SIM.build(SIM.scenario_days(name,days),0)
  local built=clock()-t0
  local now=CASES.base+days*86400+3.5*3600
  -- a cold run: the replay caches are emptied by fresh module state
  package.loaded.advisor=nil;local AA=require('advisor')
  local t1=clock()
  local r=AA.recommend(CURVE,journal.days,{failure_model='hmm',advisor_window=window},now,0)
  local cold=clock()-t1
  local t2=clock()
  for _=1,5 do AA.recommend(CURVE,journal.days,{failure_model='hmm',advisor_window=window},now,0) end
  local warm=(clock()-t2)/5
  local passes=days*8640
  results[#results+1]=string.format('%-7s %2d days: journal %.1f us/pass (%d passes), recommendation cold %.0f ms, warm %.0f ms, %s t=%s, %d evaluations, days file %d bytes',
    name,days,built/passes*1e6,passes,cold*1000,warm*1000,r.state,tostring(r.t or r.best_t),r.evaluations,#J.days_text(journal))
end
-- the monitor part per pass (journal + status field), journal of 30 days in RAM
local files={}
local io_={read=function(p) return files[p] end,write_ram=function(p,s) files[p]=s end,write_flash=function(p,s) files[p]=s end,spawn=function() return true end}
local journal=SIM.build(SIM.scenario_days('long',30),0)
files['/run/'..J.DAYS_NAME]=J.days_text(journal)
local t4=clock()
for _=1,5 do J.load(files['/run/'..J.DAYS_NAME],nil,nil) end
results[#results+1]=string.format('reading the 30-day journal file (%d bytes): %.0f ms',#files['/run/'..J.DAYS_NAME],(clock()-t4)/5*1000)
local start=CASES.base+30*86400+100
local part=A.monitor_part(io_,'/run','/etc',start,CURVE)
local settings={failure_model='hmm',advisor_mode='advice',advisor_window=30}
local t3=clock()
local n=2000
for k=0,n-1 do
  local now=start+k*10
  part:pass({SIM.sample(SIM.primary,now-8,false,false,40),SIM.sample(SIM.reserve,now-7.5,false,false,50)},CASES.pair,'source','OBSERVING',settings,now,0,now)
end
results[#results+1]=string.format('monitor part: %.2f ms per pass (journal + status field, 30-day journal, summary every 60 s)',(clock()-t3)/n*1000)
for _,line in ipairs(results) do print(line) end
