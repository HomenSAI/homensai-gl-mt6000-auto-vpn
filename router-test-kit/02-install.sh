#!/bin/sh
# HomenSAI Auto VPN test kit, step 2: install/upgrade the audited package. Monitor only; Auto stays OFF.
# Usage on the router:  sh 02-install.sh /tmp/homensai-auto-vpn_2.1.0-alpha10-1_all.ipk [--allow-unsigned] [--allow-downgrade]
# Requires step 1 and verified Auto OFF/recovery. No firmware replacement.
# Package lifecycle may stop own services; never force past its guards.
# Release signature (docs/architecture/SIGNING-2026-11-03.ru.md): copy <ipk>.sig and CHAIN.jsonl next to the .ipk. The
# router's own usign checks both before anything is changed. A wrong signature, an untrusted or revoked key, a damaged,
# forked or rolled-back release chain, or a package that is not the newest chain entry stops with a SIGNATURE-*/CHAIN-*
# code. Missing files stop too (SIGNATURE-MISSING) unless --allow-unsigned is given (packages released before signing).
# All zeros: the package of EXPECTED_VERSION is not built yet and this kit refuses to install (KIT-UNAVAILABLE). The release
# record fills EXPECTED_SHA and EXPECTED_SIZE from the built package together; scripts/bump-version.py zeroes them again.
EXPECTED_SHA=dadb77e7880908d42feff3769313c473af200783cf6ea4951b09389149c826b6
EXPECTED_SIZE=1894508
EXPECTED_VERSION=2.1.0-alpha10-1
# Release keys trusted on a FIRST install ("<key id>:<usign public key>"). An upgrade trusts only the keys of the installed
# package plus the ones the administrator added with homensai-vpn-trust-key. Before a first install compare the full
# fingerprints (sha256 of the base64 key, `sha256sum` of line 2 of the .pub file) with the release page.
TRUSTED_KEYS='701cdf098a0f849f:RWRwHN8Jig+En4PPtK6DnWPE5dVwJZ8fsPcPErBJJkvJb08SqPKov3x3 a1c06016584475fa:RWShwGAWWER1+n6DHH2pzRX53mHsoWojoXFxbPU4+UJZL+lH/9QDEzVI'
REVOKED_KEYS=''
KIT=${HOMENSAI_KIT:-/tmp/homensai-kit}
KEYS=${HOMENSAI_KEYS:-/etc/homensai-vpn/keys}
LOCAL_KEYS=${HOMENSAI_LOCAL_KEYS:-/etc/homensai-vpn/keys.local}
INSTALLED_CHAIN=${HOMENSAI_CHAIN:-/etc/homensai-vpn/chain.jsonl}
IPK="$1"
die() { echo "STOP: $*" >&2; exit 1; }
# Exit codes: 20 missing, 21 invalid signature, 22 untrusted key, 23 revoked key, 24 no usign, 25 damaged chain,
# 26 package is not the chain head, 27 forked history, 28 downgrade without --allow-downgrade.
refuse() { echo "STOP: $1: $2" >&2; exit "$3"; }
case "$EXPECTED_SHA" in
  0000000000000000000000000000000000000000000000000000000000000000)
    die "KIT-UNAVAILABLE: package $EXPECTED_VERSION is not built and recorded yet; use the kit of a released package";;
esac
ALLOW_UNSIGNED=0; ALLOW_DOWNGRADE=0
[ $# -gt 0 ] && shift
for option in "$@"; do
  case "$option" in
    --allow-unsigned) ALLOW_UNSIGNED=1;;
    --allow-downgrade) ALLOW_DOWNGRADE=1;;
    *) die "unknown option $option";;
  esac
done

[ -n "$IPK" ] && [ -f "$IPK" ] || die "usage: sh 02-install.sh /tmp/homensai-auto-vpn_${EXPECTED_VERSION}_all.ipk"
[ -f "$KIT/fingerprint.before" ] || die "run 01-preflight.sh first (no baseline fingerprint)"
SIZE=$(wc -c < "$IPK" | tr -d ' ')
SHA=$(sha256sum "$IPK" | cut -d' ' -f1)
[ "$SIZE" = "$EXPECTED_SIZE" ] || die "size $SIZE != $EXPECTED_SIZE"
[ "$SHA" = "$EXPECTED_SHA" ] || die "sha256 $SHA != $EXPECTED_SHA"
echo "package hash and size verified"

is_key_id() { case "$1" in ''|*[!0-9a-f]*) return 1;; esac; [ ${#1} -eq 16 ]; }
revoked_at() {  # key id, chain seq: true when a revocation "<key id>:<first seq>" covers it
  for item in $REVOKED; do [ "${item%%:*}" = "$1" ] && [ "$2" -ge "${item#*:}" ] && return 0; done
  return 1
}
add_revocations() {
  for item in $1; do
    case "${item#*:}" in ''|*[!0-9]*) refuse CHAIN-FORMAT "bad revocation '$item'" 25;; esac
    is_key_id "${item%%:*}" || refuse CHAIN-FORMAT "bad revocation '$item'" 25
    REVOKED="$REVOKED $item"
  done
}
# The keys this run trusts: the installed package's (upgrade) or else the kit's (first install), and the administrator's on top.
# Only the package's own keys mean an upgrade: keys.local outlives a firmware upgrade (keep.d), the package keys do not.
TRUST="$KIT/trusted-keys"
build_trust() {
  rm -rf "$TRUST" && mkdir -p "$TRUST" || die "cannot create $TRUST"
  TRUST_MODE=first-install
  for path in "$KEYS"/*; do
    [ -f "$path" ] && is_key_id "${path##*/}" && cp "$path" "$TRUST/" && TRUST_MODE=upgrade
  done
  if [ "$TRUST_MODE" = first-install ]; then
    for item in $TRUSTED_KEYS; do
      is_key_id "${item%%:*}" || die "kit key list damaged"
      printf 'untrusted comment: HomenS.AI Auto VPN release key %s\n%s\n' "${item%%:*}" "${item#*:}" > "$TRUST/${item%%:*}"
    done
  fi
  for path in "$LOCAL_KEYS"/*; do
    [ -f "$path" ] && is_key_id "${path##*/}" && cp "$path" "$TRUST/"
  done
  REVOKED=''
  add_revocations "$REVOKED_KEYS"
  for file in "$KEYS/revoked" "$LOCAL_KEYS/revoked"; do
    [ -f "$file" ] && add_revocations "$(sed 's/#.*//' "$file" | tr ',\n' '  ')"
  done
  echo "release keys ($TRUST_MODE): $(ls "$TRUST" | tr '\n' ' ')"
}
check_signature() {  # message, signature file, chain seq used for revocations
  SIGNER=$(usign -F -x "$2" 2>/dev/null)
  is_key_id "$SIGNER" || refuse SIGNATURE-INVALID "unreadable signature ${2##*/}" 21
  revoked_at "$SIGNER" "$3" && refuse SIGNATURE-KEY-REVOKED "key $SIGNER is revoked" 23
  [ -f "$TRUST/$SIGNER" ] || refuse SIGNATURE-KEY-UNTRUSTED "key $SIGNER is not trusted on this router" 22
  usign -V -q -m "$1" -x "$2" -p "$TRUST/$SIGNER" || refuse SIGNATURE-INVALID "${2##*/} does not sign ${1##*/}" 21
}
# One strict expression per chain line (the same shape scripts/signing/chain.py writes and checks):
# \1 entry  \2 key id  \3 package version  \4 prev  \5 revocations  \6 seq  \7 sha256  \8 size  \9 signature
LINE_RE='^{"entry":\({"artifact":"[A-Za-z0-9._+-]*","date_utc":"[0-9TZ:-]*","key_id":"\([0-9a-f]\{16\}\)","origin":"[a-z]*","package_version":"\([A-Za-z0-9._+-]*\)","prev":"\([0-9a-f]\{64\}\)","revoked":"\([0-9a-f: ]*\)","seq":\([0-9]\{1,9\}\),"sha256":"\([0-9a-f]\{64\}\)","size":\([0-9a-z]*\),"source_commit":"[0-9a-f]\{40\}","version":"[A-Za-z0-9._+-]*"}\),"sig":"\([A-Za-z0-9+/]\{99\}=\)"}$'
# An entry may carry the optional signed link to the release's test-evidence manifest, right after date_utc. Fields are read from
# the line without that link (still matched by the one strict expression above); the entry bytes that were signed are taken
# from the original line, so the signature check covers the link.
EVID_RE='\("date_utc":"[0-9TZ:-]*",\)"evidence_sha256":"[0-9a-f]\{64\}",'
ENTRY_RE='^{"entry":\({.*}\),"sig":"[A-Za-z0-9+/]\{99\}="}$'
check_chain() {
  add_revocations "$(sed "s|$EVID_RE|\1|" "$CHAIN" | sed -n "s|$LINE_RE|\5|p")"
  work="$KIT/chain-check"; rm -rf "$work" && mkdir -p "$work" || die "cannot create $work"
  expect=0; prev=0000000000000000000000000000000000000000000000000000000000000000
  while IFS= read -r line; do
    plain=$(printf '%s\n' "$line" | sed "s|$EVID_RE|\1|")
    fields=$(printf '%s\n' "$plain" | sed -n "s|$LINE_RE|\2 \3 \4 \6 \7 \8|p")
    [ -n "$fields" ] || refuse CHAIN-FORMAT "line $((expect+1)) of CHAIN.jsonl" 25
    set -- $fields
    [ "$4" = "$expect" ] || refuse CHAIN-SEQ-GAP "seq $4 where $expect was expected" 25
    [ "$3" = "$prev" ] || refuse CHAIN-PREV-MISMATCH "seq $4 does not link to the entry before it" 25
    printf '%s\n' "$line" | sed -n "s|$ENTRY_RE|\1|p" | tr -d '\n' > "$work/entry"
    printf 'untrusted comment: chain entry %s\n%s\n' "$4" "$(printf '%s\n' "$plain" | sed -n "s|$LINE_RE|\9|p")" > "$work/entry.sig"
    revoked_at "$1" "$4" && refuse CHAIN-KEY-REVOKED "seq $4 is signed by revoked key $1" 25
    [ -f "$TRUST/$1" ] || refuse CHAIN-KEY-UNTRUSTED "seq $4 is signed by key $1, not trusted on this router" 25
    usign -V -q -m "$work/entry" -x "$work/entry.sig" -p "$TRUST/$1" || refuse CHAIN-SIGNATURE-INVALID "seq $4" 25
    prev=$(sha256sum "$work/entry" | cut -d' ' -f1)
    HEAD_KEY=$1; HEAD_VERSION=$2; HEAD_SEQ=$4; HEAD_SHA=$5; HEAD_SIZE=$6
    expect=$((expect+1))
  done < "$CHAIN"
  [ "$expect" -gt 0 ] || refuse CHAIN-FORMAT "empty CHAIN.jsonl" 25
  [ "$HEAD_SHA" = "$SHA" ] && [ "$HEAD_SIZE" = "$SIZE" ] && [ "$HEAD_VERSION" = "$EXPECTED_VERSION" ] ||
    refuse CHAIN-HEAD-MISMATCH "the package is not the newest chain entry ($HEAD_VERSION)" 26
  if [ -f "$INSTALLED_CHAIN" ]; then
    # The installed history must be a prefix of the new one: no rewritten or forked past, no silent rollback.
    old=$(wc -l < "$INSTALLED_CHAIN"); new=$(wc -l < "$CHAIN")
    if [ "$new" -ge "$old" ] && [ "$(head -n "$old" "$CHAIN" | sha256sum)" = "$(sha256sum < "$INSTALLED_CHAIN")" ]; then
      echo "release chain extends the installed history ($old -> $new entries)"
    elif [ "$new" -lt "$old" ] && [ "$(head -n "$new" "$INSTALLED_CHAIN" | sha256sum)" = "$(sha256sum < "$CHAIN")" ]; then
      [ "$ALLOW_DOWNGRADE" = 1 ] || refuse CHAIN-DOWNGRADE "this is an older release than the installed history; add --allow-downgrade" 28
      echo "WARNING: downgrade to $HEAD_VERSION allowed by --allow-downgrade"
    else
      refuse CHAIN-FORK "the release history differs from the one installed on this router" 27
    fi
  fi
  echo "release chain verified: $expect entries, head seq $HEAD_SEQ signed by $HEAD_KEY"
}

SIG="$IPK.sig"
CHAIN="${IPK%/*}/CHAIN.jsonl"; [ "$CHAIN" = "$IPK/CHAIN.jsonl" ] && CHAIN=CHAIN.jsonl
CHAIN_OK=0
if [ ! -f "$SIG" ] || [ ! -f "$CHAIN" ]; then
  [ "$ALLOW_UNSIGNED" = 1 ] || refuse SIGNATURE-MISSING "${SIG##*/} and CHAIN.jsonl must be next to the .ipk (--allow-unsigned only for packages released before signing)" 20
  echo "WARNING: SIGNATURE-MISSING: installing without a complete signature check (--allow-unsigned); only the pinned hash protects this package"
fi
if [ -f "$SIG" ] || [ -f "$CHAIN" ]; then
  if ! command -v usign >/dev/null 2>&1; then
    [ "$ALLOW_UNSIGNED" = 1 ] || refuse SIGNATURE-TOOL-MISSING "usign is not available on this router" 24
    echo "WARNING: SIGNATURE-TOOL-MISSING: usign absent, signature not checked (--allow-unsigned)"
  else
    build_trust
    HEAD_SEQ=999999999
    if [ -f "$CHAIN" ]; then check_chain; CHAIN_OK=1; fi
    if [ -f "$SIG" ]; then check_signature "$IPK" "$SIG" "$HEAD_SEQ"; echo "package signature verified (key $SIGNER)"; fi
  fi
fi

if nft list table inet homensai_vpn_guard >/dev/null 2>&1; then die "owned nft guard present; see EMERGENCY.md"; fi
[ "$(uci -q get homensai_vpn.main.native_enabled)" = "1" ] && die "native_enabled=1; stop Auto first"
[ -n "$(uci -q changes homensai_vpn)" ] && die "pending uci changes for homensai_vpn"

# Complete a verified encrypted configuration export before this step.
# opkg preserves the own conffile; the kit never duplicates tokens in plaintext.
opkg status homensai-auto-vpn | sed -n 's/^Version: //p' > "$KIT/version.before"
echo "previous version: $(cat "$KIT/version.before" 2>/dev/null)"

echo "installing (opkg install, no force flags)..."
opkg install "$IPK"
RC=$?
echo "opkg exit code: $RC"
# Remember the verified history only once the new version is really installed (the next install must extend it).
if [ "$RC" = 0 ] && [ "$CHAIN_OK" = 1 ] && [ "$(opkg status homensai-auto-vpn | sed -n 's/^Version: //p')" = "$EXPECTED_VERSION" ]; then
  mkdir -p "${INSTALLED_CHAIN%/*}" && cp "$CHAIN" "$INSTALLED_CHAIN" && echo "release chain recorded in $INSTALLED_CHAIN"
fi
# opkg can return 0 even when a prerm guard refused; always run 03-verify.sh next.
echo "NEXT: sh 03-verify.sh"
exit $RC
