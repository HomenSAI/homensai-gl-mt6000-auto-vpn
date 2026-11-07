#!/bin/sh
# Evidence driver (not a unit test): real OpenWrt usign (host build from the pinned OpenWrt 21.02.7 SDK archive,
# sha256 21c75e4c5a429da487f8a885555cb49eee80cfc355d5dbe35d2b3ae05324a09d, staging_dir/host/bin/.usign.bin) against
# scripts/signing. Run in a throwaway glibc container, network off:
#   docker run --rm --network none -v <repo>:/src:ro -v <extracted sdk usign dir>:/u:ro python:3.12-slim sh /src/qa/evidence/signing-2026-11-03/usign_crosscheck.sh
U=$(find /u -name .usign.bin | head -1)
W=$(mktemp -d); cd "$W" || exit 1
PY="python3 -I /src/scripts/signing/pyusign.py"
pass=0; fail=0
same() { [ "$(sha256sum < "$1")" = "$(sha256sum < "$2")" ]; }
check() { if "$@" >/dev/null 2>&1; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: $*"; fi; }
refuse() { if "$@" >/dev/null 2>&1; then fail=$((fail+1)); echo "FAIL (accepted): $*"; else pass=$((pass+1)); fi; }
echo "usign binary sha256: $(sha256sum "$U" | cut -d' ' -f1)"
i=0
while [ $i -lt 20 ]; do
  head -c $((i*997+1)) /dev/urandom > msg$i
  # ours -> real
  $PY -G -p ours$i.pub -s ours$i.sec -c "ours $i"; $PY -S -m msg$i -s ours$i.sec -x ours$i.sig
  check "$U" -V -q -m msg$i -x ours$i.sig -p ours$i.pub
  "$U" -S -m msg$i -s ours$i.sec -x real-with-ours$i.sig
  check same real-with-ours$i.sig ours$i.sig
  check [ "$("$U" -F -p ours$i.pub)" = "$($PY -F -p ours$i.pub)" ]
  # real -> ours
  "$U" -G -p real$i.pub -s real$i.sec -c "real $i"; "$U" -S -m msg$i -s real$i.sec -x real$i.sig
  check $PY -V -q -m msg$i -x real$i.sig -p real$i.pub
  $PY -S -m msg$i -s real$i.sec -x ours-with-real$i.sig
  check same ours-with-real$i.sig real$i.sig
  # both refuse tampering and the wrong key
  printf x >> msg$i
  refuse "$U" -V -q -m msg$i -x ours$i.sig -p ours$i.pub
  refuse $PY -V -q -m msg$i -x real$i.sig -p real$i.pub
  refuse "$U" -V -q -m msg$i -x real$i.sig -p ours$i.pub
  i=$((i+1))
done
# The repository's real release chain: every entry verified by the real usign with the committed public keys.
LINE_RE=$(sed -n "s/^LINE_RE='\(.*\)'$/\1/p" /src/router-test-kit/02-install.sh)
n=0
while IFS= read -r line; do
  id=$(printf '%s\n' "$line" | sed -n "s|$LINE_RE|\2|p")
  printf '%s' "$line" | sed -n "s|$LINE_RE|\1|p" | tr -d '\n' > entry
  printf 'untrusted comment: chain\n%s\n' "$(printf '%s\n' "$line" | sed -n "s|$LINE_RE|\9|p")" > entry.sig
  check "$U" -V -q -m entry -x entry.sig -p /src/router/files/etc/homensai-vpn/keys/$id
  n=$((n+1))
done < /src/releases/CHAIN.jsonl
echo "repository chain entries verified by real usign: $n"
echo "RESULT pass=$pass fail=$fail"
