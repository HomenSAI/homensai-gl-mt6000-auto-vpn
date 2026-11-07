"""HomenS.AI VPN - (C) 2026 Serhii Khomenko. Mutation check of the network journal and the advisor (2.1.0-alpha9):
every rule broken on purpose must be caught. It rewrites source files, so run it ONLY on a copy of the tree, e.g.
  tar -cf - --exclude=.git . | docker run -i --rm --tmpfs /tmp homensai-vpn-python39:local sh -c \\
    "mkdir -p /work && tar -x -C /work && cd /work && python3 router/tests/mutate_network_advisor.py /work both"
Python mutants run the semantic tests of tests/test_network_advisor.py WITHOUT the shared-cases file check (that
check would catch every behaviour change trivially); Lua mutants run tests/lua/test_network_advisor.lua (the
shared cases are the Lua twin's specification)."""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(sys.argv[1])
LIB = ROOT / 'router/files/usr/lib/homensai-vpn'
ADV, JOU, CMP, CTL = LIB / 'advisor.py', LIB / 'netjournal.py', LIB / 'channel_model.py', LIB / 'advisor_control.py'
LADV, LJOU, LCM = LIB / 'lua/advisor.lua', LIB / 'lua/netjournal.lua', LIB / 'lua/channel_model.lua'

PYM = [
    ('shift without 5 % saving', ADV, 'MIN_SAVING=0.05', 'MIN_SAVING=0.0'),
    ('shift with 1 event', ADV, 'MIN_EVENTS=5', 'MIN_EVENTS=1'),
    ('rule P(G) >= theta dropped', ADV, "if params['pg']<params['theta']:codes", "if False:codes"),
    ('rule rescue <= stable dropped', ADV, "if params['rescue_stable']>params['primary_stable']:codes", "if False:codes"),
    ('rule ride-out < leave dropped', ADV, "if leave is None or not ride<leave:codes", "if False:codes"),
    ('bounds dropped', ADV, "if v is None or not low<=v<=high:codes.append('ADVISOR-OUT-OF-BOUNDS');break", "pass"),
    ('auto step unlimited', ADV, 'AUTO_STEP=0.1 ', 'AUTO_STEP=1.0 '),
    ('auto more than once a day', ADV, 'AUTO_SPACING=20*3600', 'AUTO_SPACING=0'),
    ('auto during an outage', ADV, "if calm.get('open'):codes.append('ADVISOR-BUSY-OUTAGE')", "pass"),
    ('auto during a switch', ADV, "if (calm.get('route') in ('switching','down') or", "if ("),
    ('no calm record = calm', ADV, "if not isinstance(calm,dict):return ['ADVISOR-CALM-UNKNOWN']", "calm=calm if isinstance(calm,dict) else {}"),
    ('auto with consecutive', ADV, "if cur['failure_model']=='consecutive':return no('ADVISOR-MODEL-CONSECUTIVE')", "pass"),
    ('auto outside auto mode', ADV, "if mode(settings)!='auto':return no('ADVISOR-NOT-AUTO')", "pass"),
    ('default mode auto', ADV, "DEFAULT_MODE='advice'", "DEFAULT_MODE='auto'"),
    ('golden on any curve', ADV, "    if unimodal(costs):", "    if True:"),
    ('golden only (no anchor check)', ADV, "    candidates=list(zip(anchors,costs))", "    candidates=[]"),
    ('golden wrong side', ADV, "        if fc<=fd:\n            b=d", "        if fc>=fd:\n            b=d"),
    ('replay: no switch delay', ADV, 'EXEC=2.0 ', 'EXEC=0.0 '),
    ('replay: unnecessary rule', ADV, 'if d<=leave:unnecessary+=1', 'if d<leave-5:unnecessary+=1'),
    ('loss slots without short outages', ADV, 'LOSSY_MIN_SHORTS=2', 'LOSSY_MIN_SHORTS=0'),
    ('flap of two', ADV, 'FLAP_GAP=180;FLAP_MIN=3', 'FLAP_GAP=180;FLAP_MIN=2'),
    ('recent days not heavier', ADV, '    return 0.5**(age/half)', '    return 1.0'),
    ('nightly run any hour', ADV, 'return now+offset-today*J.DAY>=RUN_AT and', 'return'),
    ('rerun without spacing', ADV, 'if last_spawn is not None and now-last_spawn<RUN_SPACING:return False', 'pass'),
    ('flash every pass', JOU, "    return bool(journal['days']) and journal.get('flash_day')!=day_index(now,offset)", "    return bool(journal['days'])"),
    ('retention 31 days', JOU, 'RETENTION=30 ', 'RETENTION=31 '),
    ('flap failover not unnecessary', JOU, "if st['ret'] is not None and now-st['ret']<FLAP_RETURN:us=1", "if False:us=1"),
    ('false failover not unnecessary', JOU, "elif source not in st['open'] and (failed is None or now-failed>FALSE_LOOKBACK):us=1", "elif False:us=1"),
    ('switch that did not pay not unnecessary', JOU, "start+d-fo['t']<COST", "start+d-fo['t']<0"),
    ('outage = lower bound only', JOU, "d=max(1,floor((lower+upper)/2+0.5))", "d=max(1,floor(lower+0.5))"),
    ('short outages uncapped', JOU, "MAX_SHORT if d<=SHORT else MAX_OUTAGES", "MAX_OUTAGES"),
    ('RAM file every pass', JOU, "clock-self.today_at>=RAM_SPACING", "True"),
    ('numeric theta ignored', CMP, "preset['theta'] if theta is None else theta", "preset['theta']"),
    ('return_pg ignored', CMP, "'healthy':fresh and pi[0]>=p['healthy']}", "'healthy':fresh and pi[0]>=HEALTHY}"),
    ('memo ignores numeric options', CMP, "    key=(p['key'],identifier,len(points),", "    key=(p['model'],identifier,len(points),"),
    ('apply without calm check', CTL, "        unsafe=A.safety(point)\n        if unsafe:return refuse(unsafe[0])\n        busy=A.calm_codes(deps.get('calm',calm_now)(runtime,now))\n        if busy:return refuse(busy[0])", "        unsafe=A.safety(point)\n        if unsafe:return refuse(unsafe[0])"),
    ('apply without safety', CTL, "        unsafe=A.safety(point)\n        if unsafe:return refuse(unsafe[0])\n        busy", "        busy"),
    ('auto apply without auto_step', CTL, "            if not step['apply'] or step['t']!=t:return refuse(step['code'] or 'ADVISOR-AUTO-STALE')", "            pass"),
    ('manual without safety', CTL, "        unsafe=A.safety(params)\n        if unsafe:return refuse(unsafe[0])", "        pass"),
]
LUAM = [
    ('shift without 5 % saving', LADV, 'M.MIN_EVENTS=5;M.MIN_SAVING=0.05', 'M.MIN_EVENTS=5;M.MIN_SAVING=0.0'),
    ('shift with 1 event', LADV, 'M.MIN_EVENTS=5;', 'M.MIN_EVENTS=1;'),
    ('rule P(G) >= theta dropped', LADV, "if params.pg<params.theta then", "if false then"),
    ('rule rescue <= stable dropped', LADV, "if params.rescue_stable>params.primary_stable then", "if false then"),
    ('rule ride-out < leave dropped', LADV, "if leave==nil or not (ride<leave) then", "if false then"),
    ('auto step unlimited', LADV, 'M.AUTO_STEP=0.1;', 'M.AUTO_STEP=1.0;'),
    ('auto more than once a day', LADV, 'M.AUTO_SPACING=20*3600', 'M.AUTO_SPACING=0'),
    ('auto during an outage', LADV, "#calm.open>0 then", "false then"),
    ('auto during a switch', LADV, "if calm.route=='switching' or calm.route=='down' or", "if"),
    ('auto with consecutive', LADV, "if cur.failure_model=='consecutive' then return no('ADVISOR-MODEL-CONSECUTIVE') end", ""),
    ('golden wrong side', LADV, "if fc<=fd then b=d", "if fc>=fd then b=d"),
    ('replay: no switch delay', LADV, 'M.EXEC=2.0;', 'M.EXEC=0.0;'),
    ('replay: dense cadence 4 s only', LADV, 'M.DENSE={4.0,5.0,6.0}', 'M.DENSE={4.0,4.0,4.0}'),
    ('loss slots without short outages', LADV, 'M.LOSSY_MIN_SHORTS=2', 'M.LOSSY_MIN_SHORTS=0'),
    ('recent days not heavier', LADV, 'return 0.5^(age/half)', 'return 1.0'),
    ('Russian plural', LADV, "if n%10==1 and n%100~=11 then return one end", "if n%10==1 then return one end"),
    ('flash every pass', LJOU, "return #journal.days>0 and journal.flash_day~=M.day_index(now,offset)", "return #journal.days>0"),
    ('flap failover not unnecessary', LJOU, "if st.ret~=NULL and now-st.ret<M.FLAP_RETURN then us=1", "if false then us=1"),
    ('switch that did not pay not unnecessary', LJOU, "start+d-fo.t<M.COST", "start+d-fo.t<0"),
    ('outage = lower bound only', LJOU, "local d=mmax(1,floor((lower+upper)/2+0.5))", "local d=mmax(1,floor(lower+0.5))"),
    ('short outages uncapped', LJOU, "local cap=3*(d<=M.SHORT and M.MAX_SHORT or M.MAX_OUTAGES)", "local cap=3*M.MAX_OUTAGES"),
    ('loss slot packing', LJOU, "rec.lp[slot]=shorts*M.SHORTS+fails*M.PACK+total", "rec.lp[slot]=fails*M.PACK+total"),
    ('numeric theta ignored', LCM, "if theta==nil then theta=preset.theta end", "theta=preset.theta"),
    ('return_pg ignored', LCM, "healthy=fresh and pi[1]>=p.healthy}", "healthy=fresh and pi[1]>=M.HEALTHY}"),
]
PY_TESTS = ['python3', '-m', 'unittest', '-f'] + ['router.tests.test_network_advisor.' + c for c in
                                               ('Journal', 'Advisor', 'Safety', 'Modes', 'Alpha8Defaults', 'Control')]


def run(cmd, timeout=900):
    try:
        return subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        return 'timeout'


def main():
    which = sys.argv[2] if len(sys.argv) > 2 else 'both'
    groups = []
    if which in ('py', 'both'): groups.append(('python', PYM, PY_TESTS))
    if which in ('lua', 'both'): groups.append(('lua', LUAM, ['lua5.1', 'router/tests/lua/test_network_advisor.lua']))
    total = killed = 0;survivors = []
    for runtime, mutants, cmd in groups:
        base = run(cmd)
        print('%s baseline exit %s' % (runtime, base), flush=True)
        if base != 0:raise SystemExit('baseline fails')
        for name, path, old, new in mutants:
            text = path.read_text(encoding='utf-8')
            if text.count(old) != 1:
                print('  %-45s NOT APPLIED (pattern %d)' % (name, text.count(old)), flush=True);survivors.append(name);continue
            path.write_text(text.replace(old, new), encoding='utf-8')
            t0 = time.time();code = run(cmd)
            path.write_text(text, encoding='utf-8')
            total += 1;dead = code != 0;killed += dead
            if not dead:survivors.append(runtime + ': ' + name)
            print('  %-7s %-45s %s (%.0f s)' % (runtime, name, 'killed' if dead else 'SURVIVED', time.time() - t0), flush=True)
    print('mutants %d, killed %d, survived/not applied: %s' % (total, killed, survivors or 'none'))


main()
