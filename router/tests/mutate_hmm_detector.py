"""HomenS.AI VPN - (C) 2026 Serhii Khomenko. Mutation check of the channel-failure detector (channel_model, the
Booster model episodes, the committed return gate). It rewrites source files, so run it ONLY on a copy of the tree,
e.g. in the CI container:
  tar -cf - --exclude=.git . | docker run -i --rm --init --tmpfs /tmp homensai-vpn-python39:local sh -c     "mkdir -p /work && tar -x -C /work && cd /work && python3 router/tests/mutate_hmm_detector.py /work both"
Each mutant must make tests/test_hmm_detector.py (Python mutants) or tests/lua/test_hmm_detector.lua (Lua) fail."""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(sys.argv[1])
PY = ROOT / 'router/files/usr/lib/homensai-vpn/channel_model.py'
LUA = ROOT / 'router/files/usr/lib/homensai-vpn/lua/channel_model.lua'
POL = ROOT / 'router/files/usr/lib/homensai-vpn/probe_policy.py'
POLL = ROOT / 'router/files/usr/lib/homensai-vpn/lua/probe_policy.lua'
TRA = ROOT / 'router/files/usr/lib/homensai-vpn/lua/transaction.lua'
NAT = ROOT / 'router/files/usr/lib/homensai-vpn/native_switch.py'

PYM = [
    ('theta 0.8 -> 0.7', PY, "PRESETS={'hmm':{'theta':0.8,", "PRESETS={'hmm':{'theta':0.7,"),
    ('dur_B 4 -> 5', PY, "'dur_b':4.0}", "'dur_b':5.0}"),
    ('cost 20 -> 10', PY, 'COST=20.0', 'COST=10.0'),
    ('suspect 0.2 -> 0.3', PY, 'SUSPECT=0.2 ', 'SUSPECT=0.3 '),
    ('healthy 0.9 -> 0.95', PY, 'HEALTHY=0.90', 'HEALTHY=0.95'),
    ('clean 300 -> 200', PY, 'CLEAN=300', 'CLEAN=200'),
    ('floor 1e-9 -> 0', PY, 'FLOOR=1e-9', 'FLOOR=0.0'),
    ('dense gap 7 -> 3', PY, 'DENSE_GAP=7.0', 'DENSE_GAP=3.0'),
    ('normal wait delay 6 -> 3', PY, 'HTTP_NORMAL=6.0', 'HTTP_NORMAL=3.0'),
    ('VPN-MTU no observation', PY, "HARD=frozenset({'VPN-003','VPN-001','VPN-MTU'})", "HARD=frozenset({'VPN-003','VPN-001'})"),
    ('healthy needs 3 HTTPS', PY, 'https>=2 else None', 'https>=3 else None'),
    ('predict: wrong leak', PY, 'out0+=pi[i]*(1-e)', 'out0+=pi[i]*e'),
    ('cadence swapped', PY, 'k=obs+(3 if dense else 0)', 'k=obs+(0 if dense else 3)'),
    ('persist without B', PY, 'return pi[2]*w[1]+pi[3]*w[2]+pi[4]*w[3]+pi[5]*w[4]', 'return pi[2]*w[1]+pi[4]*w[3]+pi[5]*w[4]'),
    ('no freshness', PY, 'fresh=last is not None and now-last<=max_age and', 'fresh=last is not None and'),
    ('newest non-observation decides', PY, 'and observation(points[-1]) is not None', ''),
    ('future samples kept', PY, 'if not finite(t) or not 0<=now-t<=WINDOW:continue', 'if not finite(t) or not now-t<=WINDOW:continue'),
    ('conflicts ignored', PY, '            if seen[t]!=health:return None\n', ''),
    ('consecutive ignored', PY, "    if model=='consecutive':\n        from failover_plan import streak", "    if False:\n        from failover_plan import streak"),
    ('no 300 s bound', PY, '    return stable_success([p for p in points if isinstance(p,dict)],identifier,count,CLEAN,now,max_age)', '    return False'),
    ('default consecutive', PY, "DEFAULT='hmm'", "DEFAULT='consecutive'"),
    ('first dt 10 -> 0', PY, 'FIRST_DT=10.0', 'FIRST_DT=0.0'),
    ('window 600 -> 60', PY, 'WINDOW=600.0', 'WINDOW=60.0'),
    ('model episode never ends on decision', POL, "elif decided and (reserve is None or episode['reserve_good']>=DENSE_GOOD):result='failure-confirmed'", "elif False:result='failure-confirmed'"),
    ('false alarm ignores suspicion', POL, "elif episode['good']>=DENSE_GOOD and view.get('suspect') is not True:result='false-alarm'", "elif episode['good']>=DENSE_GOOD:result='false-alarm'"),
    ('model trigger on any channel', POL, "role='source' if native_state=='OBSERVING' else 'target'", "role='source'"),
    # integration alpha8: the gate is the model_gate of recovery_settings.return_rule (rescue x HMM)
    ('no return gate (committed)', NAT, "and (not model_gate or return_ready(samples,journal['source'],recovery['primary_successes'],now,age,settings,pair['source']))", ''),
]
LUAM = [
    ('theta 0.8 -> 0.7', LUA, 'hmm={theta=0.8,', 'hmm={theta=0.7,'),
    ('dur_B 4 -> 5', LUA, 'dur_b=4.0}', 'dur_b=5.0}'),
    ('cost 20 -> 10', LUA, 'M.COST=20.0', 'M.COST=10.0'),
    ('healthy 0.9 -> 0.95', LUA, 'M.HEALTHY=0.9;', 'M.HEALTHY=0.95;'),
    ('clean 300 -> 200', LUA, 'M.CLEAN=300', 'M.CLEAN=200'),
    ('dense gap 7 -> 3', LUA, 'M.DENSE_GAP=7.0', 'M.DENSE_GAP=3.0'),
    ('normal wait delay 6 -> 3', LUA, 'M.HTTP_NORMAL=6.0', 'M.HTTP_NORMAL=3.0'),
    ('VPN-MTU no observation', LUA, "M.HARD={['VPN-003']=true,['VPN-001']=true,['VPN-MTU']=true}", "M.HARD={['VPN-003']=true,['VPN-001']=true}"),
    ('predict: wrong leak (3rd state)', LUA, 'e=exp(-dt/dur[3]);o0=o0+pi[4]*(1-e)', 'e=exp(-dt/dur[3]);o0=o0+pi[4]*e'),
    ('cadence swapped', LUA, 'local k=obs+(dense and 4 or 1)', 'local k=obs+(dense and 1 or 4)'),
    ('floor removed', LUA, 'M.FLOOR=1e-9', 'M.FLOOR=0'),
    ('persist without B', LUA, 'return pi[3]*w[2]+pi[4]*w[3]+pi[5]*w[4]+pi[6]*w[5]', 'return pi[3]*w[2]+pi[5]*w[4]+pi[6]*w[5]'),
    ('no freshness', LUA, 'local fresh=last~=nil and now-last<=max_age and', 'local fresh=last~=nil and'),
    ('newest non-observation decides', LUA, ' and M.observation(points[#points])~=nil', ''),
    ('conflicts ignored', LUA, '          if not same_health(first,point) then return nil end\n', ''),
    ('consecutive ignored', LUA, "  if model=='consecutive' then return require('pair').streak", "  if false then return require('pair').streak"),
    ('no 300 s bound', LUA, "  return pair.stable_success(list,identifier,count,M.CLEAN,num(now),num(max_age))==true", '  return false'),
    ('first dt 10 -> 0', LUA, 'M.FIRST_DT=10.0', 'M.FIRST_DT=0.0'),
    ('model trigger on any channel', POLL, "local role=native_state=='OBSERVING' and 'source' or 'target'", "local role='source'"),
    ('false alarm ignores suspicion', POLL, "elseif episode.good>=M.DENSE_GOOD and view.suspect~=true then result='false-alarm'", "elseif episode.good>=M.DENSE_GOOD then result='false-alarm'"),
    ('no return gate (committed)', TRA, '       and (not model_gate or CM.return_ready(samples,value.source,recovery.primary_successes,now,age,settings,source_row,env))\n', ''),
]


def run(cmd, timeout=900):
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return r.returncode
    except subprocess.TimeoutExpired:
        return 'timeout'


def main():
    which = sys.argv[2] if len(sys.argv) > 2 else 'both'
    groups = []
    if which in ('py', 'both'): groups.append(('python', PYM, ['python3', '-m', 'unittest', '-f', 'router.tests.test_hmm_detector']))
    if which in ('lua', 'both'): groups.append(('lua', LUAM, ['lua5.1', 'router/tests/lua/test_hmm_detector.lua']))
    total = killed = 0
    for runtime, mutants, cmd in groups:
        base = run(cmd)
        print('%s baseline exit %s' % (runtime, base), flush=True)
        for name, path, old, new in mutants:
            text = path.read_text(encoding='utf-8')
            if text.count(old) != 1:
                print('  %-40s NOT APPLIED (pattern %d)' % (name, text.count(old)), flush=True); continue
            path.write_text(text.replace(old, new), encoding='utf-8')
            t0 = time.time(); code = run(cmd)
            path.write_text(text, encoding='utf-8')
            total += 1; dead = code != 0; killed += dead
            print('  %-7s %-40s %s (%.0f s)' % (runtime, name, 'killed' if dead else 'SURVIVED', time.time() - t0), flush=True)
    print('mutants %d, killed %d' % (total, killed))


main()
