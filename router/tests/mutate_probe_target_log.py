"""Mutation check of the per-target probe log (docs/architecture/PER-TARGET-PROBE-LOG-2026-11-04.ru.md): every mutant of
the log code must make tests/test_probe_target_log.py (Python twin, agent wiring) or tests/lua/test_probe_target_log.lua
(Lua twin, fast_detect counters, monitor wiring, RPC) fail. Each mutant is applied in place, the matching suite runs,
the file is restored (also on error). Run on a copy (docker), never on the router:
  python router/tests/mutate_probe_target_log.py   -> one line per mutant, exit 1 when a mutant survives
"""
import os
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
PY=[sys.executable,'-m','unittest','test_probe_target_log','-q']
LUA=['lua5.1','lua/test_probe_target_log.lua']

# Not listed (equivalent): the S_ISREG test after os.open in Writer.record (O_NOFOLLOW already refuses a link; the test
# is a second belt), the early `return` of Writer.record without lines (an empty append writes nothing either way).
MUTANTS=[
    # Python twin
    ('probe_target_log.py','int(math.floor(elapsed + 0.5))','int(math.floor(elapsed))'),
    ('probe_target_log.py',"'timeout': 1,","'timeout': 2,"),
    ('probe_target_log.py',"if detail.get('trust') in TRUST_REASONS:","if detail.get('trust'):"),
    ('probe_target_log.py',"dns = 0 if dns is True else 1 if dns is False else NOT_MEASURED","dns = 0 if dns is True else 1"),
    ('probe_target_log.py',"'DNS-001': 1,","'DNS-001': 2,"),
    ('probe_target_log.py',"all(\n            type(v) is int and 0 <= v <= MAX_COUNT for v in hb) and any(hb[0::2])","all(\n            type(v) is int and 0 <= v <= MAX_COUNT for v in hb) and any(hb)"),
    ('probe_target_log.py',"type(v) is int and 0 <= v <= MAX_COUNT for v in hb","type(v) is int and 0 <= v < MAX_COUNT for v in hb"),
    ('probe_target_log.py',"if self.size + len(data) > self.segment and self.size > 0:","if self.size + len(data) >= self.segment and self.size > 0:"),
    ('probe_target_log.py',"            os.replace(self.path, self.previous)\n","            os.remove(self.path)\n"),
    ('probe_target_log.py',"self.seq = last_seq(current) or last_seq(_read(self.previous))","self.seq = last_seq(current)"),
    ('probe_target_log.py',"    lines = text.split('\\n')\n    lines.pop()\n","    lines = text.split('\\n')\n"),
    ('probe_target_log.py',"            if row[0] > after:","            if row[0] >= after:"),
    ('probe_target_log.py',"                if len(rows) < limit:","                if len(rows) <= limit:"),
    ('probe_target_log.py',"                    more = True","                    more = False"),
    ('probe_target_log.py',"or type(limit) is not int or not 1 <= limit <= MAX_ROWS","or type(limit) is not int or not 0 <= limit <= MAX_ROWS"),
    ('probe_target_log.py',"type(after) is not int or after < 0 or after > 10 ** 15","type(after) is not int or after < -1 or after > 10 ** 15"),
    ('probe_target_log.py',"    if not stat.S_ISREG(info.st_mode) or info.st_size > SEGMENT * 2:\n        raise OSError('probe target log: not a regular file or too large')","    if info.st_size > SEGMENT * 2:\n        raise OSError('probe target log: not a regular file or too large')"),
    ('probe_target_log.py',"seq, int(math.floor(stamp)), result['id']","seq, int(round(stamp)), result['id']"),
    ('probe_target_log.py',"verdict_code(result.get('code')), 1 if dense else 0,","verdict_code(result.get('code')), 0,"),
    ('probe_target_log.py',"if stamp is None or not 0 <= stamp <= MAX_STAMP:","if stamp is None or not 0 <= stamp:"),
    ('probe_target_log.py',r"\[(\d{1,2},-?\d{1,6},\d{1,2},-?\d{1,6},\d{1,2},-?\d{1,6})\]",r"\[(\d{1,2},\d{1,6},\d{1,2},\d{1,6},\d{1,2},\d{1,6})\]"),
    ('probe_target_log.py',"    return HEARTBEAT_SLOTS.index(target) if target in HEARTBEAT_SLOTS else len(HEARTBEAT_SLOTS)","    return HEARTBEAT_SLOTS.index(target) if target in HEARTBEAT_SLOTS else 0"),
    ('probe_target_log.py',"and settings.get(OPTION) is True","and settings.get(OPTION) is not False"),
    # the Python monitor wiring
    ('agent.py',"            if probe_target_log.enabled(settings):","            if True:"),
    ('agent.py',"target_writer.record([row for row in measured if row.get('id') in (failure_pair.get('source'),failure_pair.get('target'))],","target_writer.record([row for row in measured],"),
    ('agent.py',"None,pass_dense,time.time())","None,False,time.time())"),
    ('agent.py',"print(json.dumps(probe_target_log.read(RUNTIME,arguments)));return","print(json.dumps(probe_target_log.read(RUNTIME,{})));return"),
    ('inventory.lua',"main.probe_target_log=s.probe_target_log~='0'","main.probe_target_log=s.probe_target_log=='1'"),
    # Lua twin
    ('lua/probe_target_log.lua','math.floor(elapsed+0.5)','math.floor(elapsed)'),
    ('lua/probe_target_log.lua',"if TRUST_REASONS[present(detail.trust)] then code=code+UNTRUSTED end","if TRUST_REASONS[present(detail.trust)] then code=code+1 end"),
    ('lua/probe_target_log.lua',"if dns==true then dns=0 elseif dns==false then dns=1 else dns=NOT_MEASURED end","if dns==true then dns=0 else dns=1 end"),
    ('lua/probe_target_log.lua',"if i%2==1 and v>0 then sent=true end","if v>0 then sent=true end"),
    ('lua/probe_target_log.lua',"v<0 or v>MAX_COUNT then return {} end","v<0 or v>=MAX_COUNT then return {} end"),
    ('lua/probe_target_log.lua',"if self.size+#data>self.segment and self.size>0 then","if self.size+#data>=self.segment and self.size>0 then"),
    ('lua/probe_target_log.lua',"  if seq==0 then seq=M.last_seq(runner.read_file(self.path..'.1') or '') end\n",""),
    ('lua/probe_target_log.lua',"if number and number>after then","if number and number>=after then"),
    ('lua/probe_target_log.lua',"if #rows<limit then rows[#rows+1]=row else more=true;break end","if #rows<=limit then rows[#rows+1]=row else more=true;break end"),
    ('lua/probe_target_log.lua',"for i=#lines,1,-1 do local row=M.parse_line(lines[i]);if row then last=row[1];break end end","for i=#lines,1,-1 do local row=M.parse_line(lines[i]);if row then last=row[1]+1;break end end"),
    ('lua/probe_target_log.lua',"stamp<0 or stamp>MAX_STAMP then return nil end","stamp<0 then return nil end"),
    ('lua/probe_target_log.lua',"    if #digits>6 then return nil end","    if #digits>7 then return nil end"),
    ('lua/probe_target_log.lua',"limit%1~=0 or limit<1 or limit>M.MAX_ROWS then bad('RPC-INPUT-INVALID') end","limit%1~=0 or limit<0 or limit>M.MAX_ROWS then bad('RPC-INPUT-INVALID') end"),
    ('lua/probe_target_log.lua',"  return #M.HEARTBEAT_SLOTS+1\n","  return 1\n"),
    ('lua/probe_target_log.lua',"M.verdict_code(result.code),\n    dense and 1 or 0,","M.verdict_code(result.code),\n    0,"),
    ('lua/probe_target_log.lua',"return type(settings)=='table' and settings[M.OPTION]==true end","return type(settings)=='table' and settings[M.OPTION]~=false end"),
    ('lua/fast_detect.lua',"if not answered[p.target] then ch.hb[slot+1]","if answered[p.target] then ch.hb[slot+1]"),
    ('lua/fast_detect.lua',"  local out=ch.hb\n  ch.hb={0,0,0,0,0,0,0,0}\n","  local out=ch.hb\n"),
    ('lua/fast_detect.lua',"ch.hb[slot]=math.min(ch.hb[slot]+1,target_log.MAX_COUNT)","ch.hb[slot]=ch.hb[slot]"),
    ('lua/monitor.lua',"if pair.source~=nil and (row.id==pair.source or row.id==pair.target) then","if true then"),
    ('lua/monitor.lua',"self:target_log(measured,pair,settings,ctx.dense==true)","self:target_log(measured,pair,settings,false)"),
    ('lua/monitor.lua',"        hb[row.id]=self.fast:take_heartbeat(row.id)\n",""),
    ('lua/monitor.lua',"  if not target_log.enabled(settings) then return end","  if false then return end"),
    ('lua/rpc.lua',"        if not state.probe_targets then return M.FALLBACK end\n",""),
    ('lua/rpc.lua',"    for _,name in ipairs(M.PROBE_LOG) do bind(name) end\n",""),
]


def write(path,text):
    with open(str(path),'w',encoding='utf-8',newline=chr(10)) as handle:handle.write(text)


def run(mutant):
    name,old,new=mutant
    path=LIB/name
    text=path.read_text(encoding='utf-8')
    if text.count(old)!=1:return 'BROKEN (pattern found %d times)'%text.count(old)
    try:
        write(path,text.replace(old,new,1))
        argv=LUA if name.startswith('lua/') else PY
        # the case-file currency check would kill every Python mutant without a semantic test: off for mutants
        env=dict(os.environ,PROBE_TARGET_LOG_MUTATION='1')
        result=subprocess.run(argv,cwd=str(HERE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900,env=env)
        return 'killed' if result.returncode!=0 else 'SURVIVED'
    finally:
        write(path,text)


def main():
    survived=0
    only={int(a) for a in sys.argv[1:]}   # optional: run just these mutants (1-based numbers of the listing)
    for index,mutant in enumerate(MUTANTS,1):
        if only and index not in only:continue
        verdict=run(mutant)
        if verdict!='killed':survived+=1
        print('%2d %-28s %-8s %s'%(index,mutant[0],verdict,mutant[1][:70].replace('\n',' ')),flush=True)
    total=len(only) if only else len(MUTANTS)
    print('mutants %d, killed %d, survived %d'%(total,total-survived,survived))
    return 1 if survived else 0


if __name__=='__main__':
    sys.exit(main())
