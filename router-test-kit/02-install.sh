#!/bin/sh
# HomenSAI Auto VPN test kit, step 2: install/upgrade the audited package. Monitor only; Auto stays OFF.
# Usage on the router:  sh 02-install.sh /tmp/homensai-auto-vpn_0.9.1-alpha66-1_all.ipk
# Requires step 1 and verified Auto OFF/recovery. No firmware replacement.
# Package lifecycle may stop own services; never force past its guards.
EXPECTED_SHA=9581a4105469d23a414704857264b959b133d22c0d0321eb853479e9cd7c0282
EXPECTED_SIZE=986153
EXPECTED_VERSION=0.9.1-alpha66-1
KIT=/tmp/homensai-kit
IPK="$1"
die() { echo "STOP: $*" >&2; exit 1; }

[ -n "$IPK" ] && [ -f "$IPK" ] || die "usage: sh 02-install.sh /tmp/homensai-auto-vpn_${EXPECTED_VERSION}_all.ipk"
[ -f "$KIT/fingerprint.before" ] || die "run 01-preflight.sh first (no baseline fingerprint)"
SIZE=$(wc -c < "$IPK" | tr -d ' ')
SHA=$(sha256sum "$IPK" | cut -d' ' -f1)
[ "$SIZE" = "$EXPECTED_SIZE" ] || die "size $SIZE != $EXPECTED_SIZE"
[ "$SHA" = "$EXPECTED_SHA" ] || die "sha256 $SHA != $EXPECTED_SHA"
echo "package hash and size verified"

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
# opkg can return 0 even when a prerm guard refused; always run 03-verify.sh next.
echo "NEXT: sh 03-verify.sh"
exit $RC
