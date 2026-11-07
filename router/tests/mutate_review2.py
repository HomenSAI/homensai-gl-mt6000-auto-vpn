"""Mutation check of the fixes of the second safety review (05.11.2026): the queued click key, the Start with an unaccepted server
key, the trust of keys.local after a firmware upgrade. Each mutant is applied in place, the suites run, the file is restored (also
on error). Run on a copy (docker), never on the router:
  python router/tests/mutate_review2.py [py|lua|kit] [substring]   -> one line per mutant, exit 1 when a mutant survives
"""
import sys

from mutate_safety_review import run

PY=[[sys.executable,'-W','ignore','-m','unittest','-f','test_key_gate.Start','test_boot_held.VariantC','test_boot_held.VariantD','-q']]
LUA=[['lua5.1','lua/test_wave3_product.lua'],['lua5.1','lua/test_key_gate.lua'],['lua5.1','lua/test_boot_held.lua']]
KIT=[[sys.executable,'-W','ignore','-m','unittest','-f','test_gl_sensors.SystemFiles','-q'],
     [sys.executable,'-W','ignore','-c',"import sys,unittest;sys.path.insert(0,'../../qa');import test_signing_install as m;"
      "sys.exit(not unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(m)).wasSuccessful())"]]

GATE="    pinned=n.key_unaccepted(selection['source']['id'],selection['target']['id'])\n    if pinned:raise n.Refused(pinned)\n"
LGATE="  local pinned=T.key_unaccepted(env,selection.source.id,selection.target.id)\n  if pinned then refuse(pinned) end\n"
KEY="(type(row.id)=='string' and row.id or '')..'|'..string.format('%.17g',canon.number(row.requested) or -1)"
INSTALL='../../../../../router-test-kit/02-install.sh'
LOCAL='''  for path in "$LOCAL_KEYS"/*; do\n    [ -f "$path" ] && is_key_id "${path##*/}" && cp "$path" "$TRUST/"\n'''

PY_MUTANTS=[
    ('pair_auto.py',GATE,""),
    ('pair_auto.py',GATE,GATE.replace("selection['source']['id'],selection['target']['id']","selection['source']['id']")),
    ('pair_auto.py',GATE,GATE.replace("selection['source']['id'],selection['target']['id']","selection['target']['id']")),
]

LUA_MUTANTS=[
    # the bug itself: a decoded float is a table, its text differs at each read
    ('lua/auto.lua',KEY,"tostring(row.id)..'|'..tostring(row.requested)"),
    ('lua/auto.lua',KEY,"tostring(row.requested)"),
    ('lua/auto.lua',KEY,"string.format('%.17g',canon.number(row.requested) or -1)"),
    ('lua/auto.lua',KEY,"(type(row.id)=='string' and row.id or '')"),
    ('lua/auto.lua',"string.format('%.17g',canon.number(row.requested) or -1)","string.format('%.0f',canon.number(row.requested) or -1)"),
    ('lua/pair.lua',LGATE,""),
    ('lua/pair.lua',LGATE,LGATE.replace('selection.source.id,selection.target.id','selection.source.id')),
    ('lua/pair.lua',LGATE,LGATE.replace('selection.source.id,selection.target.id','selection.target.id')),
]

KIT_MUTANTS=[
    (INSTALL,'''  for path in "$KEYS"/*; do\n''','''  for path in "$KEYS"/* "$LOCAL_KEYS"/*; do\n'''),
    (INSTALL,LOCAL+"  done\n",""),
    (INSTALL,LOCAL,LOCAL.replace('''"$TRUST/"\n''','''"$TRUST/" && TRUST_MODE=upgrade\n''')),
    ('../../../lib/upgrade/keep.d/homensai-vpn',"/etc/homensai-vpn/chain.jsonl\n",""),
]


def main():
    which=sys.argv[1] if len(sys.argv)>1 else 'all'
    only=sys.argv[2] if len(sys.argv)>2 else ''
    bad=[];total=0
    for name,mutants,commands in (('py',PY_MUTANTS,PY),('lua',LUA_MUTANTS,LUA),('kit',KIT_MUTANTS,KIT)):
        if which not in ('all',name):continue
        chosen=[m for m in mutants if only in m[1]]
        total+=len(chosen);bad+=run(name,chosen,commands)
    print('mutants: %d, survived: %d'%(total,len(bad)))
    return 1 if bad else 0


if __name__=='__main__':raise SystemExit(main())
