"""Mutation check of the CUSUM trigger (CUSUM-TRIGGER-2026-11-04.ru.md): every mutant of the decision code must make
tests/test_cusum.py (Python twins) or tests/lua/test_cusum.lua (Lua twins) fail. Each mutant is applied in place, the
matching suite runs, the file is restored (also on error). Run on a copy (docker), never on the router:
  python router/tests/mutate_cusum.py   -> one line per mutant, exit 1 when a mutant survives
"""
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
PY=[sys.executable,'-m','unittest','test_cusum','-q']
LUA=['sh','-c','cd lua && lua5.1 test_cusum.lua']

# Not listed (equivalent): the name of the sentinel key of a sample without a target in lua/cusum.lua.
MUTANTS=[
    # the loss detector, Python twin
    ('cusum.py','H=8.0','H=12.0'),
    ('cusum.py','CAP=2 ','CAP=3 '),
    ('cusum.py','GATE=8 ','GATE=4 '),
    ('cusum.py','P1=0.5 ','P1=0.4 '),
    ('cusum.py','step=LOST_STEP if self.run<=CAP else 0.0','step=LOST_STEP'),
    ('cusum.py','self.run=0;step=KEPT_STEP','step=KEPT_STEP'),
    ('cusum.py','self.s=max(0.0,self.s+step)','self.s=self.s+step'),
    ('cusum.py','if self.s<H:return False\n        self.s=0.0\n','if self.s<H:return False\n'),
    ('cusum.py','if target is not None and sum(1','if False and sum(1'),
    ('cusum.py','self.beat-at<GATE','self.beat-at<=GATE'),
    ('cusum.py','if target is not None:self.seen[target]=self.beat','pass'),
    # the RTT watch, Python twin
    ('cusum.py','Z_ON=4.0;','Z_ON=5.0;'),
    ('cusum.py','Z_OFF=2.0','Z_OFF=3.0'),
    ('cusum.py','CLEAR=30 ','CLEAR=5 '),
    ('cusum.py','MAX_HOLD=1800 ','MAX_HOLD=18000 '),
    ('cusum.py','WARM=120 ','WARM=60 '),
    ('cusum.py','TARGET_MIN=5 ','TARGET_MIN=1 '),
    ('cusum.py','self._update(math.log(rtt_ms)-self.base[target])','self._update(math.log(rtt_ms)-min(self.base.values()))'),
    ('cusum.py','self.drift+=(self.x0-self.drift)/TRACK','pass'),
    ('cusum.py','elif abs(self.z)<Z_OFF:','elif True:'),
    ('cusum.py','sigma=max(residuals[len(residuals)//2]*1.4826,SIG_MIN)','sigma=SIG_MIN'),
    ('cusum.py','self.P11-=K1*self.P01','pass'),
    ('cusum.py','if error>limit:error=limit','if False:pass'),
    # the Booster, Python
    ('probe_policy.py',"if now<held.get('until',0) and not bypass:continue","if now<held.get('until',0):continue"),
    ('probe_policy.py',"if isinstance(view,dict) and view.get('failed') is True:continue","pass"),
    ('probe_policy.py',"bypass=now>=last['at']+cusum_gap(last['clean']) or now<last['at']","bypass=True"),
    ('probe_policy.py'," or now<last['at']",""),
    ('probe_policy.py','return 0 if clean<=CUSUM_FREE else','return 0 if clean<CUSUM_FREE else'),
    ('probe_policy.py','CUSUM_GAP_MAX=600','CUSUM_GAP_MAX=6000'),
    ('probe_policy.py','CUSUM_FREE=2;CUSUM_GAP=60','CUSUM_FREE=2;CUSUM_GAP=30'),
    ('probe_policy.py',"(0 if episode.get('bad') else 1)","1"),
    ('probe_policy.py',"if self._forced(suspect)['clean']:self._note_forced(suspect,clean=0)","pass"),
    ('probe_policy.py',"if item['reason'] in REST_BYPASS:self._note_forced(profile,at=now,ids=roles)","pass"),
    ('probe_policy.py',"if episode.get('reason') in REST_BYPASS:\n","if True:\n"),
    ('probe_policy.py',"'streaks','cusum_at')","'streaks')"),
    ('probe_policy.py',"'wan-ok-tunnel-down','cusum-loss')","'wan-ok-tunnel-down')"),
    ('probe_policy.py',"if type(at) not in (int,float) or type(clean) is not int or clean<0:","if not isinstance(at,(int,float)):"),
    ('probe_policy.py',"kept={key:value for key,value in forced.items() if ids is None or key in ids}","kept=dict(forced)"),
    # the loss detector and the RTT watch, Lua twin
    ('lua/cusum.lua','M.H=8;','M.H=12;'),
    ('lua/cusum.lua','M.CAP=2;','M.CAP=3;'),
    ('lua/cusum.lua','M.GATE=8\n','M.GATE=4\n'),
    ('lua/cusum.lua','step=self.run<=M.CAP and M.LOST_STEP or 0','step=M.LOST_STEP'),
    ('lua/cusum.lua','self.run=0;step=M.KEPT_STEP','step=M.KEPT_STEP'),
    ('lua/cusum.lua','self.s=math.max(0,self.s+step)','self.s=self.s+step'),
    ('lua/cusum.lua','if self.s<M.H then return false end\n  self.s=0\n','if self.s<M.H then return false end\n'),
    ('lua/cusum.lua','if self.beat-at<M.GATE then','if self.beat-at<=M.GATE then'),
    ('lua/cusum.lua','if recent<2 then','if false then'),
    ('lua/cusum.lua','M.Z_ON=4;','M.Z_ON=5;'),
    ('lua/cusum.lua','M.Z_OFF=2;','M.Z_OFF=3;'),
    ('lua/cusum.lua','M.CLEAR=30;','M.CLEAR=5;'),
    ('lua/cusum.lua','M.MAX_HOLD=1800','M.MAX_HOLD=18000'),
    ('lua/cusum.lua','M.WARM=120;','M.WARM=60;'),
    ('lua/cusum.lua','local middle=values[math.floor(#values/2)+1]','local middle=values[math.floor((#values+1)/2)]'),
    ('lua/cusum.lua','self:update(math.log(rtt_ms)-self.base[target])','self:update(math.log(rtt_ms))'),
    ('lua/cusum.lua','self.drift=self.drift+(self.x0-self.drift)/M.TRACK',''),
    ('lua/cusum.lua','elseif math.abs(self.z)<M.Z_OFF then','elseif true then'),
    # the Booster, Lua
    ('lua/probe_policy.lua',"(bypass or now>=(num(get(held,'until')) or 0))","(now>=(num(get(held,'until')) or 0))"),
    ('lua/probe_policy.lua',"if not decided and (bypass","if (bypass"),
    ('lua/probe_policy.lua',"bypass=now>=at+M.cusum_gap(clean) or now<at","bypass=true"),
    ('lua/probe_policy.lua',"bypass=now>=at+M.cusum_gap(clean) or now<at","bypass=now>=at+M.cusum_gap(clean)"),
    ('lua/probe_policy.lua','if clean<=M.CUSUM_FREE then return 0 end','if clean<M.CUSUM_FREE then return 0 end'),
    ('lua/probe_policy.lua','M.CUSUM_GAP_MAX=600','M.CUSUM_GAP_MAX=6000'),
    ('lua/probe_policy.lua',"clean+(get(episode,'bad') and 0 or 1)","clean+1"),
    ('lua/probe_policy.lua',"if clean>0 then self:note_forced(suspect,nil,0) end",""),
    ('lua/probe_policy.lua',"if M.REST_BYPASS[item.reason] then self:note_forced(profile,now,nil,roles) end",""),
    ('lua/probe_policy.lua',"if M.REST_BYPASS[get(episode,'reason')] then","if true then"),
    ('lua/probe_policy.lua',"'streaks','cusum_at'}","'streaks'}"),
    ('lua/probe_policy.lua',"['cusum-loss']=true}\n-- REST_BYPASS","}\n-- REST_BYPASS"),
    ('lua/probe_policy.lua',"if not finite(at) or type(clean)~='number' or clean%1~=0 or clean<0 then","if not finite(at) then"),
    ('lua/probe_policy.lua',"if ids==nil or ids[key] then kept[key]=value end","kept[key]=value"),
    # the pulse
    ('lua/fast_detect.lua',"ch.stalled=nil;ch.cusum:reset() end\n    return nil","ch.stalled=nil end\n    return nil"),
    ('lua/fast_detect.lua',"local timeout=ch.reason=='timeout' or ch.reason=='rx-flowing'","local timeout=true"),
    ('lua/fast_detect.lua',"local timeout=ch.reason=='timeout' or ch.reason=='rx-flowing'","local timeout=ch.reason=='timeout'"),
    ('lua/fast_detect.lua',"fired=ch.cusum:feed(outcome~='ok',","fired=ch.cusum:feed(outcome=='lost',"),
    ('lua/fast_detect.lua',"if outcome~='ok' and outcome~='lost' and outcome~='vetoed' then return false end","outcome=outcome or 'lost'"),
    ('lua/fast_detect.lua',";ch.judged=pending[1].target end",";ch.judged=target end"),
    ('lua/fast_detect.lua',"if self:detect(ch,outcome) then","if self:detect(ch,outcome) and ch.armed and now>=ch.hold_until then"),
    ('lua/fast_detect.lua',"if self.opts.cusum then\n    local timeout","if true then\n    local timeout"),
    ('lua/fast_detect.lua',"if self.opts.rtt then\n    local was","if true then\n    local was"),
    ('lua/fast_detect.lua',"if opts.cusum and not self.opts.cusum then ch.cusum:reset() end",""),
    ('lua/fast_detect.lua',"if opts.rtt and not self.opts.rtt then ch.rtt_watch:learn();ch.congested=false end",""),
    ('lua/fast_detect.lua',"if ms<0 or ms>M.RTT_MAX_MS then return end",""),
    ('lua/fast_detect.lua',"if #list<M.RTT_KEEP then list[#list+1]=ch.rtt_last end","list[#list+1]=ch.rtt_last"),
    ('lua/fast_detect.lua',"ch.judged=nil;ch.rtt_ms=nil;ch.rtt_target=nil\n","ch.judged=nil;ch.rtt_target=nil\n"),
    ('lua/fast_detect.lua',"if type(arrived)~='number' or type(echo.sent_at)~='number' then return end","if type(arrived)~='number' then arrived=now end"),
    ('lua/fast_detect.lua',"local out=ch.rtts\n  ch.rtts={}\n","local out=ch.rtts\n"),
    ('lua/fast_detect.lua',"if ch.suspect_reason==M.CUSUM_REASON then evidence.cause='cusum' end",""),
    ('lua/fast_detect.lua',"congested=ch.congested==true,code=ch.congested and cusum.CODE or canon.null","congested=ch.congested==true,code=canon.null"),
    # the monitor
    ('lua/monitor.lua',"if reason~=fast.CUSUM_REASON then self.fast:hold(ch.id,now+fast.RETRY) end","self.fast:hold(ch.id,now+fast.RETRY)"),
    ('lua/monitor.lua',"self.fast:pair(),state,runner.wall(),self.failure_models) end)","self.fast:pair(),state,runner.wall()) end)"),
    ('lua/monitor.lua',"if not rtt_log.enabled(self.settings) then return end",""),
    ('lua/monitor.lua',"  self:rtt_flush(now)\n",""),
    ('lua/monitor.lua',"cusum=cusum.enabled(settings),rtt=cusum.rtt_enabled(settings)}","cusum=true,rtt=cusum.rtt_enabled(settings)}"),
    ('lua/monitor.lua',"self.rtt_flush_at=now+rtt_log.PERIOD\n  local runner","local runner"),
    ('lua/monitor.lua',"  if ok then self.rtt_log_error=nil\n  elseif self.rtt_log_error~=tostring(err) then\n    self.rtt_log_error=tostring(err)\n    if runner.log then runner.log('heartbeat rtt log: '","  if not ok then\n    if runner.log then runner.log('heartbeat rtt log: '"),
    # the socket
    ('lua/monitor_io.lua','if wakes>M.BEAT_WAKES then unwatch();return end',''),
    ('lua/monitor_io.lua','function handle:close() unwatch();pcall','function handle:close() pcall'),
    ('lua/monitor_io.lua','wakes=0;watch()','watch()'),
    ('lua/monitor_io.lua','arrived[#arrived+1]={data,M.hires()}','arrived[#arrived+1]={data}'),
    ('lua/monitor_io.lua','if #arrived<M.BEAT_QUEUE then arrived','arrived'),
    ('lua/monitor_io.lua','local first=table.remove(arrived,1)\n    if first then return first[1],first[2] end\n',''),
    # the log
    ('lua/heartbeat_rtt_log.lua','sorted[math.floor(#sorted/2)+1]','sorted[math.floor(#sorted/2)]'),
    ('lua/heartbeat_rtt_log.lua','if self.size+#data>self.segment and self.size>0 then','if false then'),
    ('lua/heartbeat_rtt_log.lua',"if self.size==nil then self.size=#(self.runner.read_file(self.path) or '') end","if self.size==nil then self.size=0 end"),
    ('lua/heartbeat_rtt_log.lua','if not any then return nil end',''),
]


def write(path,text):
    with open(str(path),'w',encoding='utf-8',newline=chr(10)) as handle:handle.write(text)


def run(mutant):
    name,old,new=mutant
    path=LIB/name
    text=path.read_text(encoding='utf-8').replace('\r\n','\n')
    if text.count(old)!=1:return 'BROKEN (pattern found %d times)'%text.count(old)
    try:
        write(path,text.replace(old,new,1))
        argv=LUA if name.startswith('lua/') else PY
        # the case-file currency check would kill every Python mutant without a semantic test: off for mutants
        env=dict(__import__('os').environ,CUSUM_MUTATION='1')
        result=subprocess.run(argv,cwd=str(HERE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600,env=env)
        return 'killed' if result.returncode!=0 else 'SURVIVED'
    finally:
        write(path,text)


def main():
    survived=0
    for index,mutant in enumerate(MUTANTS,1):
        verdict=run(mutant)
        if verdict!='killed':survived+=1
        print('%3d %-26s %-8s %s'%(index,mutant[0],verdict,mutant[1][:70].replace('\n',' ')),flush=True)
    print('mutants %d, killed %d, survived %d'%(len(MUTANTS),len(MUTANTS)-survived,survived))
    return 1 if survived else 0


if __name__=='__main__':
    sys.exit(main())
