#!/bin/sh
# Runs inside the container: each mutation must make at least one new test fail.
set -u
run() {
  name=$1; old=$2; new=$3
  rm -rf /tmp/m; cp -r /src/router /tmp/m
  python3 - "$old" "$new" <<'PY'
import sys
p='/tmp/m/files/usr/lib/homensai-vpn/rollback_recovery.py'
s=open(p).read();old,new=sys.argv[1],sys.argv[2]
assert s.count(old)==1,old
open(p,'w').write(s.replace(old,new))
PY
  cd /tmp/m/tests
  if python3 -m unittest test_vendor_rebuild_recovery >/tmp/m.log 2>&1; then echo "MUTANT SURVIVED: $name"; else echo "killed: $name ($(grep -c '^FAIL:\|^ERROR:' /tmp/m.log) failing)"; fi
}
run unrouted "            if not unrouted_kernel():refuse()" "            pass"
