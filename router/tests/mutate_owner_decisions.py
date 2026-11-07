"""HomenS.AI VPN - (C) 2026 Serhii Khomenko. Mutation check of the owner's decisions of 05.11.2026: every rule broken on purpose must
be caught. It rewrites source files, so run it ONLY on a copy of the tree, e.g.
  git archive HEAD | docker run -i --rm --tmpfs /tmp homensai-vpn-python311:local sh -c \\
    "mkdir -p /tmp/w && tar -x -C /tmp/w && cd /tmp/w && python3 router/tests/mutate_owner_decisions.py /tmp/w"
Model mutants run the Model tests of tests/test_key_gate.py, the others the suites named beside them."""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(sys.argv[1])
LIB = ROOT/'router/files/usr/lib/homensai-vpn'
NAT, PAIR, AUTO, CTL = LIB/'native_switch.py', LIB/'pair_auto.py', LIB/'auto_control.py', LIB/'advisor_control.py'
TX, LPAIR, INV = LIB/'lua/transaction.lua', LIB/'lua/pair.lua', LIB/'inventory.lua'
MODEL = ROOT/'tools/formal/model.py'

KEY_PY = (['python3', '-m', 'unittest', 'test_key_gate.Carrying', 'test_key_gate.Session', 'test_key_gate.Start', 'test_key_gate.LegacyStart', 'test_boot_held.VariantC', 'test_boot_held.VariantD'], 'router/tests')
MODEL_PY = (['python3', '-m', 'unittest', 'test_key_gate.Model'], 'router/tests')
LEVER_PY = (['python3', '-m', 'unittest', 'test_fast_switch', 'test_setup_detector', 'test_late_switch'], 'router/tests')
KEY_LUA = [(['lua5.1', 'router/tests/lua/test_key_gate.lua'], '.'), (['lua5.1', 'router/tests/lua/test_boot_held.lua'], '.')]
LEVER_LUA = [(['lua5.1', 'router/tests/lua/test_fast_switch.lua'], '.'), (['lua5.1', 'router/tests/lua/test_late_switch.lua'], '.')]

BEGIN_PY = "pinned=n.carrying_unaccepted(backend,selection)\n    if pinned:raise n.Refused(pinned)"
PROOF_PY = "pinned=n.carrying_unaccepted(backend,selection)\n        if pinned:\n            n.publish({'state':'BLOCKED'"
BEGIN_LUA = "local pinned=T.carrying_unaccepted(env,selection)\n  if pinned then refuse(pinned) end"
PROOF_LUA = "local pinned=T.carrying_unaccepted(env,selection)\n    if pinned then\n      T.publish(env,{state='BLOCKED'"
BOTH_PY = "n.key_unaccepted(selection['source']['id'],selection['target']['id'])"
BOTH_LUA = "T.key_unaccepted(env,selection.source.id,selection.target.id)"

MUTANTS = [
    # decision 3: the channel that carries the traffic after the Start
    ('begin: either channel (the old rule)', PAIR, BEGIN_PY, BEGIN_PY.replace('n.carrying_unaccepted(backend,selection)', BOTH_PY), [KEY_PY]),
    ('begin: no check', PAIR, BEGIN_PY, "pinned=None\n    if pinned:raise n.Refused(pinned)", [KEY_PY]),
    ('begin: always the source', PAIR, BEGIN_PY, BEGIN_PY.replace('n.carrying_unaccepted(backend,selection)', "n.key_unaccepted(selection['source']['id'])"), [KEY_PY]),
    ('first proof: either channel (leaves BLOCKED)', PAIR, PROOF_PY, PROOF_PY.replace('n.carrying_unaccepted(backend,selection)', BOTH_PY), [KEY_PY]),
    ('first proof: no check', PAIR, PROOF_PY, PROOF_PY.replace('n.carrying_unaccepted(backend,selection)', 'None'), [KEY_PY]),
    ('rule: the other channel', NAT, "carrying=selection[role(proof(selection),backend.order()[0])]['id']", "carrying=selection[{'source':'target','target':'source'}[role(proof(selection),backend.order()[0])]]['id']", [KEY_PY]),
    ('rule: no role lets the Start go', NAT, "return key_unaccepted(*[(selection.get(name) or {}).get('id') for name in ('source','target')])", "return None", [KEY_PY]),
    ('rule: the static order of the selection', NAT, "role(proof(selection),backend.order()[0])", "role(proof(selection),selection['order'])", [KEY_PY]),
    ('legacy button: either channel', AUTO, "key_blockers(blockers, selection, backend if trial_nonce is None else None)", "key_blockers(blockers, selection)", [KEY_PY]),
    ('legacy trial: the Start rule', AUTO, "key_blockers(blockers, selection, backend if trial_nonce is None else None)", "key_blockers(blockers, selection, backend)", [KEY_PY]),
    ('lua begin: either channel (the old rule)', LPAIR, BEGIN_LUA, BEGIN_LUA.replace('T.carrying_unaccepted(env,selection)', BOTH_LUA), KEY_LUA),
    ('lua begin: no check', LPAIR, BEGIN_LUA, "local pinned=nil\n  if pinned then refuse(pinned) end", KEY_LUA),
    ('lua begin: always the source', LPAIR, BEGIN_LUA, BEGIN_LUA.replace('T.carrying_unaccepted(env,selection)', 'T.key_unaccepted(env,selection.source.id)'), KEY_LUA),
    ('lua first proof: either channel (leaves BLOCKED)', LPAIR, PROOF_LUA, PROOF_LUA.replace('T.carrying_unaccepted(env,selection)', BOTH_LUA), KEY_LUA),
    ('lua first proof: no check', LPAIR, PROOF_LUA, PROOF_LUA.replace('T.carrying_unaccepted(env,selection)', 'nil'), KEY_LUA),
    ('lua rule: no role lets the Start go', TX, "return M.key_unaccepted(env,selection.source and selection.source.id,selection.target and selection.target.id)\nend", "return nil\nend", KEY_LUA),
    ('lua rule: the static order of the selection', TX, "local order=env.backend.order()\n", "local order=selection.order\n", KEY_LUA),
    ('model: begin refuses either channel', MODEL, "elif key_pin(cfg) == 'directional' and key_on_carrying(s):", "elif key_pin(cfg) == 'directional' and (s.kp or s.kr):", [MODEL_PY]),
    ('model: begin refuses nothing', MODEL, "elif key_pin(cfg) == 'directional' and key_on_carrying(s):", "elif False:", [MODEL_PY]),
    ('model: always the primary', MODEL, "return s.kr if s.uci == 'R' else s.kp", "return s.kp", [MODEL_PY]),
    # decision 2: the parallel recheck is off until measured
    ('parallel on by default', PAIR, "if settings.get('parallel_recheck') not in (True,'1') or check is None or", "if settings.get('parallel_recheck') in (False,'0') or check is None or", [LEVER_PY]),
    ('parallel never on', PAIR, "if settings.get('parallel_recheck') not in (True,'1') or check is None or", "if True or check is None or", [LEVER_PY]),
    ('inventory on by default', INV, "main.parallel_recheck=s.parallel_recheck=='1'", "main.parallel_recheck=s.parallel_recheck~='0'", [LEVER_PY]),
    ('lua parallel on by default', LPAIR, "if (on~=true and on~='1') or not env.backend.recheck_begin then return nil end", "if on==false or on=='0' or not env.backend.recheck_begin then return nil end", LEVER_LUA),
    ('lua parallel never on', LPAIR, "if (on~=true and on~='1') or not env.backend.recheck_begin then return nil end", "do return nil end", LEVER_LUA),
    # decision 1: the words of the turbo opt-in
    ('router wants the old words', CTL, "TURBO_ACK='minimum-downtime-up-to-8-extra-switches-a-day'", "TURBO_ACK='minimum-downtime-up-to-5-extra-switches-a-day'", [LEVER_PY]),
]


def run(steps):
    for command, directory in steps:
        try:
            done = subprocess.run(command, cwd=str(ROOT/directory), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        except subprocess.TimeoutExpired:
            return 'timeout'
        if done.returncode:
            return done.returncode
    return 0


def main():
    names = sys.argv[2:]
    total = killed = 0;survivors = []
    for steps in ([KEY_PY], KEY_LUA, [LEVER_PY], LEVER_LUA, [MODEL_PY]):
        if run(steps) != 0:raise SystemExit('baseline fails: %s' % (steps,))
    print('baseline passes', flush=True)
    for name, path, old, new, steps in MUTANTS:
        if names and not any(x in name for x in names):continue
        raw = path.read_bytes();text = raw.decode('utf-8')
        fitted = (old.replace('\n', '\r\n'), new.replace('\n', '\r\n')) if '\r\n' in text else (old, new)
        if text.count(fitted[0]) < 1:
            print('  %-50s NOT APPLIED' % name, flush=True);survivors.append(name);continue
        path.write_bytes(text.replace(fitted[0], fitted[1], 1).encode('utf-8'))
        started = time.time();code = run(steps)
        path.write_bytes(raw)
        total += 1;dead = code != 0;killed += dead
        if not dead:survivors.append(name)
        print('  %-50s %s (%.0f s)' % (name, 'killed' if dead else 'SURVIVED', time.time()-started), flush=True)
    print('mutants %d, killed %d, survived/not applied: %s' % (total, killed, survivors or 'none'))


main()
