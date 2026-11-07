"""HomenS.AI VPN - (C) 2026 Serhii Khomenko. Mutation check of the fast end of Auto (FAST-SWITCH-2026-11-04.ru.md): every rule
broken on purpose must be caught. It rewrites source files, so run it ONLY on a copy of the tree, e.g.
  git archive HEAD | docker run -i --rm --tmpfs /tmp homensai-vpn-python311:local sh -c \\
    "mkdir -p /tmp/w && tar -x -C /tmp/w && cd /tmp/w && python3 router/tests/mutate_fast_switch.py /tmp/w both"
Python mutants run the semantic tests of tests/test_fast_switch.py WITHOUT the check that the cases file is current; Lua mutants
run tests/lua/test_fast_switch.lua + test_late_switch.lua (the shared cases are the Lua twin's specification)."""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(sys.argv[1])
LIB = ROOT / 'router/files/usr/lib/homensai-vpn'
ADV, CMP, CTL, POL, PAIR, NAT = LIB/'advisor.py', LIB/'channel_model.py', LIB/'advisor_control.py', LIB/'probe_policy.py', LIB/'pair_auto.py', LIB/'native_switch.py'
REC, HIS = LIB/'recovery_settings.py', LIB/'native_history.py'
LADV, LCM, LPOL, LPAIR, LAUTO, LFAST = (LIB/('lua/%s.lua' % n) for n in ('advisor', 'channel_model', 'probe_policy', 'pair', 'auto', 'fast_detect'))

PYM = [
    ('N may be 1', CMP, 'OR_FAILURES=(2,10)', 'OR_FAILURES=(1,10)'),
    ('N active in consecutive', CMP, "or not OR_FAILURES[0]<=v<=OR_FAILURES[1] or name(settings)=='consecutive':return None", "or not OR_FAILURES[0]<=v<=OR_FAILURES[1]:return None"),
    ('streak one sample short', CMP, 'if streak(samples,identifier,extra,now,max_age,False,profile):return', "if streak(samples,identifier,extra-1,now,max_age,False,profile):return"),
    ('rule off', CMP, "    if extra is not None:\n        from failover_plan import streak", "    if False:\n        from failover_plan import streak"),
    ('streak without the generation scope', CMP, 'if streak(samples,identifier,extra,now,max_age,False,profile):return', 'if streak(samples,identifier,extra,now,max_age,False,None):return'),
    ('turbo without the opt-in', CMP, "    if not turbo_on(settings):return None\n", ""),
    ('turbo in consecutive', CMP, "settings.get('slider_turbo') in (True,'1') and name(settings)!='consecutive'", "settings.get('slider_turbo') in (True,'1')"),
    ('beats below 3', CMP, 'TURBO_BEATS=(3,8)', 'TURBO_BEATS=(1,8)'),
    ('beats above 8', CMP, 'TURBO_BEATS=(3,8)', 'TURBO_BEATS=(3,99)'),
    ('reserve silent still leaves', CMP, " and beat.get('target_ok') is True", ""),
    ('old heartbeat row', CMP, 'BEAT_FRESH=2.5', 'BEAT_FRESH=60.0'),
    ('heartbeat row from the future', CMP, 'not 0<=now-t<=BEAT_FRESH', 'not now-t<=BEAT_FRESH'),
    ('foreign channel row', CMP, "return beat.get('id')==source and ", 'return '),
    ('foreign reserve row', CMP, " and beat.get('target')==target", ""),
    ('a wake row is a verdict', CMP, " or beat.get('reason')!='heartbeat'", ""),
    ('k off by one', CMP, 'type(lost) is int and lost>=k', 'type(lost) is int and lost>=k-1'),
    ('heartbeat without a fresh sample', CMP, "if view and view['time'] is not None and now-view['time']<=max_age:return 'heartbeat'", "return 'heartbeat'"),
    ('failures floor 3', REC, "RANGES={'failures':(2,10),", "RANGES={'failures':(3,10),"),
    ('history drops 2', HIS, "(('required_failures',2),", "(('required_failures',3),"),
    ('dense 3 s for everyone', POL, 'return TURBO_DENSE if heartbeat_k(settings) is not None else DENSE_INTERVAL', 'return TURBO_DENSE'),
    ('turbo keeps dense 4 s', POL, 'return TURBO_DENSE if heartbeat_k(settings) is not None else DENSE_INTERVAL', 'return DENSE_INTERVAL'),
    ('wake option ignored', POL, "    if isinstance(settings,dict) and settings.get('auto_event_wake') in (False,'0'):return None\n", ""),
    ('wake on a healthy sample', POL, "if isinstance(row,dict) and row.get('id') in ids and failing(row):return", "if isinstance(row,dict) and row.get('id') in ids:return"),
    ('wake on a foreign channel', POL, "if isinstance(row,dict) and row.get('id') in ids and failing(row):return", "if isinstance(row,dict) and failing(row):return"),
    ('one row wakes every nap', NAT, "if type(stamp) not in (int,float) or stamp==WAKE_SEEN[0]:return False", "if type(stamp) not in (int,float):return False"),
    ('heartbeat wakes every beat', NAT, "row.get('since',row.get('time'))", "row.get('time')"),
    ('nap ignores the row', NAT, "        if wake_due():return\n", ""),
    ('parallel option ignored', PAIR, "if settings.get('parallel_recheck') not in (True,'1') or check is None or", "if check is None or"),
    ('parallel on by default', PAIR, "if settings.get('parallel_recheck') not in (True,'1') or check is None or", "if settings.get('parallel_recheck') in (False,'0') or check is None or"),
    ('blind code probed', PAIR, "or check is None or evidence_code in PROBE_BLIND_CODES:return None", "or check is None:return None"),
    ('parallel answer ignored', PAIR, "return (LATE_RECHECK_CODE,'probe') if parallel[1].get('healthy') is True else None", "return None"),
    ('parallel: any answer stops', PAIR, "return (LATE_RECHECK_CODE,'probe') if parallel[1].get('healthy') is True else None", "return (LATE_RECHECK_CODE,'probe')"),
    ('parallel probe never waited for', PAIR, "        parallel[0].join(RECHECK_WAIT)\n", ""),
    ('parallel probe waited for without a bound', PAIR, "parallel[0].join(RECHECK_WAIT)", "parallel[0].join()"),
    ('parallel probe waited for zero seconds', PAIR, "parallel[0].join(RECHECK_WAIT)", "parallel[0].join(0)"),
    ('monitor no longer read before the answer', PAIR, "    if isinstance(status,dict) and monitor_recovered(status.get('samples',[]),identifier,evidence,time.time(),selection['source']):\n        return LATE_RECHECK_CODE,'monitor'\n    if parallel is not None:", "    if parallel is not None:"),
    ('tick ignores the rule', PAIR, "        failed = rule is not None\n", "        failed = rule in ('unstable','model')\n"),
    ('tick passes no row', PAIR, "selection['source'], selection['target']['id'], beat)", "selection['source'], selection['target']['id'], None)"),
    ('rule not in the evidence', PAIR, " 'failure_rule': rule,", ""),
    ('steps interpolated to the nearest', ADV, "if t<=a['t']+1e-9:best=a", "if t<=a['t']+0.05:best=a"),
    ('curve order unchecked', ADV, "        if not b['t']<a['t']:raise ValueError('ADVISOR-CURVE-INVALID')\n    return curve", "        pass\n    return curve"),
    ('fast candidates without the admin', ADV, "    if fast:\n        for a in curve['fast_anchors']:", "    if True:\n        for a in curve['fast_anchors']:"),
    ('turbo recommended', ADV, "            if a['t']>=FAST_MIN_T:\n", "            if True:\n"),
    ('auto below the limit', ADV, "    if t<0 and not (cur['fast'] and t>=FAST_MIN_T):return no('ADVISOR-FAST-OFF')\n", ""),
    ('auto moves turbo', ADV, "    if cur['beats'] is not None:return no('ADVISOR-TURBO')\n", ""),
    ('advisor speaks over turbo', ADV, "if cur['failure_model']=='consecutive' or cur['beats'] is not None:result['state']='inactive'", "if cur['failure_model']=='consecutive':result['state']='inactive'"),
    ('floor always turbo', ADV, "    if C.turbo_on(settings):return MIN_T\n", "    return MIN_T\n"),
    ('floor without the fast segment', ADV, "return FAST_MIN_T if fast_enabled(settings) else 0", "return FAST_MIN_T"),
    ('replay ignores N', ADV, "or (cons is not None and failed>=cons)", ""),
    ('attached ignores the detectors', ADV, " and extra==point.get('cons_f') and beats==point.get('beat_k')", ""),
    ('settings key blind to the fast end', ADV, "    if extra is not None or beats is not None or fast_enabled(settings):cur.append(", "    if False:cur.append("),
    ('position past the limit accepted', CTL, "        if t<A.t_floor(settings):return refuse('ADVISOR-FAST-OFF')\n", ""),
    ('position not on its step', CTL, "        t=point['t']\n        if t<A.t_floor", "        if t<A.t_floor"),
    ('turbo without the words', CTL, "if turbo and arguments.get('turbo_ack')!=TURBO_ACK:return None,'ADVISOR-TURBO-ACK'", "pass"),
    ('turbo without the fast segment', CTL, "        fast=True\n    main={'slider_fast'", "    main={'slider_fast'"),
    ('off leaves the position', CTL, "    moved=t is not None and t<floor\n", "    moved=False\n"),
    ('off during an outage', CTL, "        busy=A.calm_codes(calm)\n        if busy:return None,busy[0]\n    if moved:", "    if moved:"),
    ('off leaves the detector', CTL, "        if not fast and settings.get('hmm_or_failures') is not None:main['hmm_or_failures']='0'\n", ""),
    ('own values keep the detector', CTL, "        main.update(detector_options(None,None,settings))  # own values: no hidden detector of the slider stays on\n", ""),
    ('calm position keeps the detector', CTL, "if cons is not None or settings.get('hmm_or_failures') is not None:main['hmm_or_failures']=str(cons or 0)", "if cons is not None:main['hmm_or_failures']=str(cons)"),
]
LUAM = [
    ('N may be 1', LCM, 'M.OR_FAILURES={2,10}', 'M.OR_FAILURES={1,10}'),
    ('N active in consecutive', LCM, "if not v or v<M.OR_FAILURES[1] or v>M.OR_FAILURES[2] or M.name(settings)=='consecutive' then return nil end", "if not v or v<M.OR_FAILURES[1] or v>M.OR_FAILURES[2] then return nil end"),
    ('streak one sample short', LCM, "require('pair').streak(samples,identifier,extra,now,max_age,false,profile,env)", "require('pair').streak(samples,identifier,extra-1,now,max_age,false,profile,env)"),
    ('rule off', LCM, "if extra~=nil and require('pair').streak", "if false and require('pair').streak"),
    ('streak without the generation scope', LCM, "require('pair').streak(samples,identifier,extra,now,max_age,false,profile,env)", "require('pair').streak(samples,identifier,extra,now,max_age,false,nil,env)"),
    ('turbo without the opt-in', LCM, "  if not M.turbo_on(settings) then return nil end\n", ""),
    ('turbo in consecutive', LCM, "(settings.slider_turbo==true or settings.slider_turbo=='1') and M.name(settings)~='consecutive'", "(settings.slider_turbo==true or settings.slider_turbo=='1')"),
    ('beats below 3', LCM, 'M.TURBO_BEATS={3,8}', 'M.TURBO_BEATS={1,8}'),
    ('reserve silent still leaves', LCM, " and beat.target_ok==true", ""),
    ('old heartbeat row', LCM, 'M.BEAT_FRESH=2.5', 'M.BEAT_FRESH=60.0'),
    ('heartbeat row from the future', LCM, 'if not finite(t) or now-t<0 or now-t>M.BEAT_FRESH then', 'if not finite(t) or now-t>M.BEAT_FRESH then'),
    ('foreign channel row', LCM, "return beat.id==source and ", 'return '),
    ('foreign reserve row', LCM, " and beat.target==target", ""),
    ('a wake row is a verdict', LCM, " or beat.reason~='heartbeat'", ""),
    ('k off by one', LCM, "lost%1==0 and lost>=k", "lost%1==0 and lost>=k-1"),
    ('heartbeat without a fresh sample', LCM, "if view~=nil and view.time~=nil and now-view.time<=max_age then return 'heartbeat' end", "return 'heartbeat'"),
    ('dense 3 s for everyone', LPOL, "return require('channel_model').heartbeat_k(settings)~=nil and M.TURBO_DENSE or M.DENSE_INTERVAL", "return M.TURBO_DENSE"),
    ('wake option ignored', LPOL, "if off==false or off=='0' or not is_dict(pair)", "if not is_dict(pair)"),
    ('wake on a healthy sample', LPOL, "(id==source or id==target) and M.failing(row) then", "(id==source or id==target) then"),
    ('wake on a foreign channel', LPOL, "(id==source or id==target) and M.failing(row) then", "M.failing(row) then"),
    ('one row wakes every nap', LAUTO, "if stamp==nil or stamp==env.wake_seen then return false end", "if stamp==nil then return false end"),
    ('heartbeat wakes every beat', LAUTO, "(num(row.since) or num(row.time))", "num(row.time)"),
    ('nap ignores the row', LAUTO, "    if M.wake_due(env) then return end\n", ""),
    ('reserve state ignores its age', LFAST, " and now-target.ok_at<=M.TARGET_OK", ""),
    ('reserve state ignores its last beat', LFAST, "target_ok=target.last=='ok' and target.ok_at~=nil", "target_ok=target.ok_at~=nil"),
    ('parallel option ignored', LPAIR, "if (on~=true and on~='1') or not env.backend.recheck_begin then return nil end", "if not env.backend.recheck_begin then return nil end"),
    ('parallel on by default', LPAIR, "if (on~=true and on~='1') or not env.backend.recheck_begin then return nil end", "if on==false or on=='0' or not env.backend.recheck_begin then return nil end"),
    ('blind code probed', LPAIR, "  if type(evidence_code)=='string' and M.PROBE_BLIND_CODES[evidence_code] then return nil end\n  local ok,pending", "  local ok,pending"),
    ('parallel answer ignored', LPAIR, "if M.recheck_finish(env,pending)==true then return M.LATE_RECHECK_CODE,'probe' end\n    return nil", "M.recheck_finish(env,pending)\n    return nil"),
    ('parallel: any answer stops', LPAIR, "if M.recheck_finish(env,pending)==true then return M.LATE_RECHECK_CODE,'probe' end\n    return nil", "M.recheck_finish(env,pending);return M.LATE_RECHECK_CODE,'probe'"),
    ('failed start not caught', LPAIR, "local ok,pending=pcall(env.backend.recheck_begin,selection.source.id,M.RECHECK_SECONDS)\n  if ok then return pending end\n  return nil", "return env.backend.recheck_begin(selection.source.id,M.RECHECK_SECONDS)"),
    ('pending not collected on a monitor abort', LPAIR, "    if pending then M.recheck_finish(env,pending) end\n    return M.LATE_RECHECK_CODE,'monitor'", "    return M.LATE_RECHECK_CODE,'monitor'"),
    ('pending not passed in the tick', LPAIR, "M.late_recheck(env,selection,evidence,evidence_code,pending)\n        M.decision_timing", "M.late_recheck(env,selection,evidence,evidence_code)\n        M.decision_timing"),
    ('tick ignores the rule', LPAIR, "    local failed=rule~=nil\n", "    local failed=rule=='unstable' or rule=='model'\n"),
    ('tick passes no row', LPAIR, "selection.source,env,selection.target.id,beat)", "selection.source,env,selection.target.id,nil)"),
    ('rule not in the evidence', LPAIR, "failure_model=CM.name(settings),failure_rule=rule,", "failure_model=CM.name(settings),"),
    ('steps interpolated to the nearest', LADV, "if t<=a.t+1e-9 then best=a end", "if t<=a.t+0.05 then best=a end"),
    ('fast candidates without the admin', LADV, "  if fast then\n    for _,a in ipairs(curve.fast_anchors) do", "  if true then\n    for _,a in ipairs(curve.fast_anchors) do"),
    ('turbo recommended', LADV, "      if a.t>=M.FAST_MIN_T then\n", "      if true then\n"),
    ('auto below the limit', LADV, "  if t<0 and not (cur.fast and t>=M.FAST_MIN_T) then return no('ADVISOR-FAST-OFF') end\n", ""),
    ('auto moves turbo', LADV, "  if cur.beats~=nil then return no('ADVISOR-TURBO') end\n", ""),
    ('advisor speaks over turbo', LADV, "if cur.failure_model=='consecutive' or cur.beats~=nil then result.state='inactive'", "if cur.failure_model=='consecutive' then result.state='inactive'"),
    ('floor always turbo', LADV, "  if CM.turbo_on(settings) then return M.MIN_T end\n", "  do return M.MIN_T end\n"),
    ('floor without the fast segment', LADV, "return M.fast_enabled(settings) and M.FAST_MIN_T or 0", "return M.FAST_MIN_T"),
    ('replay ignores N', LADV, " or (cons~=nil and failed>=cons)", ""),
    ('attached ignores the detectors', LADV, "attached=extra==point.cons_f and beats==point.beat_k", "attached=true"),
    ('settings key blind to the fast end', LADV, "if extra~=nil or beats~=nil or fast then\n", "if false then\n"),
]
PY_TESTS = ['python3', '-m', 'unittest', 'discover', '-s', 'router/tests', '-p', 'test_fast_switch_mut.py']


def run(cmd, timeout=900):
    try:
        return subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        return 'timeout'


def lua_run():
    for name in ('test_fast_switch', 'test_late_switch'):
        code = run(['lua5.1', 'router/tests/lua/%s.lua' % name])
        if code != 0:return code
    return 0


def main():
    which = sys.argv[2] if len(sys.argv) > 2 else 'both'
    # the semantic suite without the "cases file is current" check (it would catch every change trivially)
    source = (ROOT/'router/tests/test_fast_switch.py').read_text(encoding='utf-8')
    (ROOT/'router/tests/test_fast_switch_mut.py').write_text(source.replace("    def test_cases_file_is_current(self):\n        self.assertEqual(json.loads(G.text()),CASES,'run: python3 router/tests/gen_fast_switch_cases.py --write')\n", "", 1), encoding='utf-8')
    groups = []
    if which in ('py', 'both'): groups.append(('python', PYM, lambda:run(PY_TESTS)))
    if which in ('lua', 'both'): groups.append(('lua', LUAM, lua_run))
    total = killed = 0;survivors = []
    for runtime, mutants, runner in groups:
        base = runner()
        print('%s baseline exit %s' % (runtime, base), flush=True)
        if base != 0:raise SystemExit('baseline fails')
        for name, path, old, new in mutants:
            text = path.read_text(encoding='utf-8')
            if text.count(old) != 1:
                print('  %-45s NOT APPLIED (pattern found %d times, exactly one is required)' % (name, text.count(old)), flush=True);survivors.append(name);continue
            path.write_text(text.replace(old, new, 1), encoding='utf-8')
            t0 = time.time();code = runner()
            path.write_text(text, encoding='utf-8')
            total += 1;dead = code != 0;killed += dead
            if not dead:survivors.append(runtime + ': ' + name)
            print('  %-7s %-45s %s (%.0f s)' % (runtime, name, 'killed' if dead else 'SURVIVED', time.time() - t0), flush=True)
    print('mutants %d, killed %d, survived/not applied: %s' % (total, killed, survivors or 'none'))


main()
