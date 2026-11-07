"""Single source for custom-IPK and SDK lifecycle hook bodies."""
from pathlib import Path
import re

SOURCE=Path(__file__).resolve().parent


def guard_block(action):
    source=(SOURCE/'files/usr/lib/homensai-vpn/lifecycle_guard.py').read_text(encoding='utf8')
    if '\nHOMENSAI_LIFECYCLE_GUARD\n' in source:raise ValueError('hook delimiter collision')
    return "/usr/bin/python3 - "+action+" <<'HOMENSAI_LIFECYCLE_GUARD'\n"+source+"\nHOMENSAI_LIFECYCLE_GUARD\n"


# Owner decision 07.11.2026: a damaged or unverified package on upgrade rolls back to the previous working version
# instead of leaving the service stopped. The previous version is the pristine copy the last good installation saved
# (PERSIST/pristine/payload.tar.gz + .sha256; snapshot refuses to replace it with a damaged payload, so after exit 8 it
# still holds the previous version). This script is embedded in postinst (it never trusts the freshly unpacked, possibly
# damaged helper): it checks the copy against its sha256 and its own manifest, copies every listed program file back
# (never /etc/config or /etc/homensai-vpn: the owner's settings, terms, journal and history stay as they are), verifies
# the result against the restored manifest and records the outcome in PERSIST/upgrade-result.json for the page (a red
# reason line). Exit 0 rolled back and verified, 5 no usable previous copy (nothing copied), 6 copied but not verified.
# Files of the damaged new version that the previous one does not list are left in place (never referenced by it).
# BH-02 (bug hunt 07.11.2026): the pristine copy may be older than the running version (a snapshot refused with exit 7
# keeps the copy it had), so the rollback restores it only when its manifest version equals the version preinst
# recorded as running before this upgrade (PERSIST/upgrade-from); otherwise nothing is copied (exit 5, unavailable).
ROLLBACK_SCRIPT = r"""set -u
ROOT=${HOMENSAI_ROLLBACK_ROOT:-}
PERSIST=${HOMENSAI_ROLLBACK_PERSIST:-/etc/homensai-vpn}
reason=${1:-INTEGRITY-PAYLOAD-DAMAGED}
case "$reason" in INTEGRITY-PAYLOAD-DAMAGED|INTEGRITY-HELPER-FAILED) ;; *) reason=INTEGRITY-HELPER-FAILED ;; esac
MANIFEST_REL=usr/lib/homensai-vpn/integrity.sha256
PRISTINE=$PERSIST/pristine/payload.tar.gz
NOHASH=----------------------------------------------------------------
version_of() { v=$(sed -n 's/^# version //p' "$1" 2>/dev/null | head -n 1); case "$v" in *[!0-9A-Za-z.+~_-]*) v= ;; esac; printf '%s' "$v"; }
rows() { awk -v nohash="$NOHASH" '!/^#/ && NF==3 && $1!=nohash && length($1)==64 && $2 ~ /^0[0-7][0-7][0-7]$/ && $3 ~ /^\/[A-Za-z0-9_.+\/-]+$/ && $3 !~ /\.\./ {print}' "$1" 2>/dev/null; }
verified() { [ -n "$(rows "$2")" ] && rows "$2" | awk -v d="$1" '{print $1 "  " d $3}' | sha256sum -c >/dev/null 2>&1; }
record() {
    mkdir -p "$PERSIST" 2>/dev/null
    printf '{"code":"%s","reason":"%s","from":"%s","to":"%s","time":%s}\n' "$1" "$reason" "$new" "$2" "$(date +%s)" \
        > "$PERSIST/.upgrade-result.json.new" 2>/dev/null && mv -f "$PERSIST/.upgrade-result.json.new" "$PERSIST/upgrade-result.json" 2>/dev/null
    logger -t homensai-vpn "$1 $reason ${new:-?} -> ${2:-?}" 2>/dev/null || true
}
new=$(version_of "$ROOT/$MANIFEST_REL")
if ! { [ -f "$PRISTINE" ] && [ -f "$PRISTINE.sha256" ] &&
       [ "$(sha256sum "$PRISTINE" 2>/dev/null | cut -d' ' -f1)" = "$(head -n 1 "$PRISTINE.sha256" | cut -d' ' -f1)" ]; }; then
    record UPGRADE-ROLLBACK-UNAVAILABLE ''; exit 5
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/homensai-rollback.XXXXXX") || { record UPGRADE-ROLLBACK-UNAVAILABLE ''; exit 5; }
trap 'rm -rf "$work"' EXIT
if ! { tar -xzf "$PRISTINE" -C "$work" 2>/dev/null && verified "$work" "$work/$MANIFEST_REL"; }; then
    record UPGRADE-ROLLBACK-UNAVAILABLE ''; exit 5
fi
old=$(version_of "$work/$MANIFEST_REL")
running=$(head -n 1 "$PERSIST/upgrade-from" 2>/dev/null)
case "$running" in *[!0-9A-Za-z.+~_-]*) running= ;; esac
if [ -z "$running" ] || [ "$old" != "$running" ]; then
    logger -t homensai-vpn "UPGRADE-ROLLBACK-VERSION kept ${old:-?} != running before ${running:-?}" 2>/dev/null || true
    record UPGRADE-ROLLBACK-UNAVAILABLE ''; exit 5
fi
failed=0
for row in $(rows "$work/$MANIFEST_REL" | awk '{print $2 ":" $3}') "0644:/$MANIFEST_REL"; do
    mode=${row%%:*}; path=${row#*:}
    case "$path" in /etc/config/*|/etc/homensai-vpn/*) continue ;; esac
    dst=$ROOT$path
    if mkdir -p "${dst%/*}" && cp "$work$path" "$dst.rollback-new" && chmod "$mode" "$dst.rollback-new" && mv -f "$dst.rollback-new" "$dst"; then :
    else rm -f "$dst.rollback-new"; failed=1; fi
done
sync
if [ "$failed" = 0 ] && cmp -s "$work/$MANIFEST_REL" "$ROOT/$MANIFEST_REL" && verified "$ROOT" "$ROOT/$MANIFEST_REL"; then
    record UPGRADE-ROLLED-BACK "$old"; exit 0
fi
record UPGRADE-ROLLBACK-FAILED "$old"; exit 6
"""


def rollback_block():
    if '\nHOMENSAI_ROLLBACK\n' in ROLLBACK_SCRIPT:
        raise ValueError('hook delimiter collision')
    return '''# Owner decision 07.11.2026: roll back to the previous working version and start it (Auto comes back only from an
# owner-started intent on disk, never from this start); without a usable previous copy nothing starts. Either way the
# package operation itself is reported as failed (exit 1): the new version is not installed. The page shows the reason.
rollback_and_start() {
    rollback=0
    sh -s "$1" <<'HOMENSAI_ROLLBACK' || rollback=$?
''' + ROLLBACK_SCRIPT + '''HOMENSAI_ROLLBACK
    case "$rollback" in
    0)
        echo "UPGRADE-ROLLED-BACK: $1; the previous working version was restored and started; Auto resumes only if you had started it" >&2
        rm -f /etc/homensai-vpn/maintenance.json
        /etc/init.d/homensai-vpn enable || true
        /etc/init.d/homensai-vpn restart || echo LIFECYCLE-RESTART-FAILED >&2
        /etc/init.d/rpcd reload || true
        /usr/bin/python3 /usr/lib/homensai-vpn/luci_cache.py || true ;;
    6) echo "UPGRADE-ROLLBACK-FAILED: $1; the previous version did not verify after the copy, the service is not started" >&2 ;;
    *) echo "UPGRADE-ROLLBACK-UNAVAILABLE: $1; no verified previous version is kept, the service is not started" >&2 ;;
    esac
    exit 1
}
'''


VERSION_RX=re.compile(r'[0-9A-Za-z.+~_-]{1,64}')
SDK_VERSION='@HOMENSAI-PACKAGE-VERSION@'   # sdk_fragment: make expands $(PKG_VERSION)-$(PKG_RELEASE) in its place


def package_version():
    """The package version (build_ipk.VERSION, the version both builds write into the payload manifest)."""
    found=re.search(r"^VERSION = '([^']*)'$",(SOURCE/'build_ipk.py').read_text(encoding='utf8'),re.M)
    if not found or not VERSION_RX.fullmatch(found.group(1)):raise ValueError('PACKAGE-VERSION-UNKNOWN')
    return found.group(1)


def scripts(version=None):
    version=package_version() if version is None else version
    if version!=SDK_VERSION and not VERSION_RX.fullmatch(version):raise ValueError('PACKAGE-VERSION-UNKNOWN')
    header='#!/bin/sh\nset -eu\n[ -n "${IPKG_INSTROOT:-}" ] && exit 0\n'
    # BH-02: the version running before this install (its payload manifest, still in place: opkg unpacks after preinst);
    # the rollback restores the pristine copy only when it is exactly this version. No manifest: no rollback.
    record_running='''running=$(sed -n 's/^# version //p' /usr/lib/homensai-vpn/integrity.sha256 2>/dev/null | head -n 1)
case "$running" in *[!0-9A-Za-z.+~_-]*) running= ;; esac
if [ -n "$running" ]; then
    mkdir -p /etc/homensai-vpn && chmod 0700 /etc/homensai-vpn && printf '%s\\n' "$running" > /etc/homensai-vpn/upgrade-from
else
    rm -f /etc/homensai-vpn/upgrade-from
fi
'''
    # BH-03: after a rollback opkg keeps this package unpacked but not configured; a later opkg run (configure, another
    # install) runs this postinst again over the rolled-back files, where the snapshot would pass, erase the reason and
    # let opkg mark the package installed. When upgrade-result.json says exactly this package was rolled back and the
    # installed files are still the version it was rolled back to, postinst refuses before touching anything (the
    # rolled-back version keeps running; the page keeps the reason). opkg install --force-reinstall unpacks the files
    # again (the installed version then differs) and installs normally.
    rolled_back_refusal='''package_version='''+"'"+version+"'"+'''
result=/etc/homensai-vpn/upgrade-result.json
if [ -f "$result" ] && [ "$(sed -n 's/.*"code":"\\([A-Z-]*\\)".*/\\1/p' "$result")" = UPGRADE-ROLLED-BACK ] &&
   [ "$(sed -n 's/.*"from":"\\([^"]*\\)".*/\\1/p' "$result")" = "$package_version" ] &&
   [ "$(sed -n 's/.*"to":"\\([^"]*\\)".*/\\1/p' "$result")" = "$(sed -n 's/^# version //p' /usr/lib/homensai-vpn/integrity.sha256 2>/dev/null | head -n 1)" ]; then
    echo "UPGRADE-NOT-INSTALLED: $package_version was rolled back; its files are not installed. Use opkg install --force-reinstall with a verified package" >&2
    exit 1
fi
'''
    # IR-08 (integration review 07.11.2026): on an upgrade the old prerm has already stopped the service when this preinst
    # runs. A refusal of the guard here (it removes the maintenance marker itself) aborts opkg, and nothing else would start
    # the still-installed old version again: monitoring must always run (owner decision 07.11.2026), so the refusal starts
    # the service again, as prerm does after its own refusal (R4-07a). Only when the init script is there (a first install
    # over leftover settings has none). The supervisor starts Auto only from an owner-started intent on disk.
    preinst=header+'''if [ -f /etc/config/homensai_vpn ] || [ -d /etc/homensai-vpn ]; then
[ -x /usr/bin/python3 ] || { echo LIFECYCLE-PYTHON-REQUIRED >&2; exit 1; }
refused=0
'''+guard_block('prepare').replace("<<'HOMENSAI_LIFECYCLE_GUARD'\n","<<'HOMENSAI_LIFECYCLE_GUARD' || refused=$?\n",1)+'''if [ "$refused" != 0 ]; then
    if [ -x /etc/init.d/homensai-vpn ]; then
        /etc/init.d/homensai-vpn start || echo LIFECYCLE-RESTART-FAILED: the service could not be started again after the refusal >&2
    fi
    echo LIFECYCLE-REFUSED-PREINST: the installed version keeps running, the package operation is aborted >&2
    exit "$refused"
fi
fi
'''+record_running+'exit 0\n'
    # Plan item 54 (F-16/F-17): the guard below (and prerm/preinst before it) wrote the maintenance marker; postinst is the
    # end of the package operation, so every exit removes it (trap), and a good install removes it before the service starts
    # (Auto may resume only after it). A refusal inside the guard removes it itself.
    postinst=header+"trap 'rm -f /etc/homensai-vpn/maintenance.json' EXIT\n"+'mkdir -p /etc/homensai-vpn\nchmod 0700 /etc/homensai-vpn\n[ ! -f /etc/config/homensai_vpn ] || chmod 0600 /etc/config/homensai_vpn\n'+rolled_back_refusal+guard_block('prepare')+'''
# Never launch an uncertified board's native instance if opkg replaced a
# pre-staged conffile. Lifecycle/recovery refusal above remains the first gate.
board=$(ubus call system board 2>/dev/null | jsonfilter -e '@.board_name' 2>/dev/null || true)
if [ "$board" != "glinet,gl-mt6000" ] && [ "$board" != "glinet,mt3000-snand" ]; then
    monitor_only=$(uci -q get homensai_vpn.main.monitor_only 2>/dev/null || true)
    [ "$monitor_only" = "1" ] || { echo MONITOR-ONLY-DEPLOYMENT >&2; exit 1; }
fi
/usr/bin/python3 -c "from pathlib import Path; p=Path('/usr/lib/homensai-vpn/__pycache__'); [x.unlink() for x in p.glob('*.pyc') if x.is_file() and not x.is_symlink()]"
# Self-restore source (TODO item 15): opkg 21.02 does not tell maintainer scripts where the .ipk is, so the pristine
# copy is made from the files opkg has just unpacked, each verified against the shipped manifest first.
# A refused copy (no space, permissions only: the documented exit 7) is a warning; a damaged freshly unpacked payload
# never starts (exit 8); any other exit (2 usage, 126/127 helper missing or not executable, a crash) means the helper
# itself is not trustworthy, so the installation is not verified and nothing starts either (R4-07b).
# Since 07.11.2026 (owner decision) exits 8 and "other" roll back to the previous working version when one is kept
# (rollback_and_start always ends with exit 1, before enable/restart below).
'''+rollback_block()+'''snapshot=0
/usr/sbin/homensai-vpn-integrity snapshot >/dev/null || snapshot=$?
case "$snapshot" in
    0) rm -f /etc/homensai-vpn/upgrade-result.json ;;
    7) echo INTEGRITY-SNAPSHOT-REFUSED >&2; rm -f /etc/homensai-vpn/upgrade-result.json ;;
    8) echo INTEGRITY-PAYLOAD-DAMAGED: the installed files do not match the package manifest >&2; rollback_and_start INTEGRITY-PAYLOAD-DAMAGED ;;
    *) echo "INTEGRITY-HELPER-FAILED: the integrity helper exited with $snapshot, the installation is not verified" >&2; rollback_and_start INTEGRITY-HELPER-FAILED ;;
esac
rm -f /etc/homensai-vpn/maintenance.json
/etc/init.d/homensai-vpn enable
/etc/init.d/homensai-vpn restart
/etc/init.d/rpcd reload
/usr/bin/python3 /usr/lib/homensai-vpn/luci_cache.py
exit 0
'''
    # opkg 21.02 runs the installed package's prerm with 'upgrade <new>' before the
    # new preinst; a removal passes 'remove'. Only an upgrade may proceed over a
    # journal whose apply worker is provably gone (the new supervisor recovers it).
    # The guard runs again after the stop, before anything is disabled or removed: a Start accepted between the first
    # assessment and the stop, or a shutdown whose recovery did not finish (pair session not STOPPED/FAILED, journal
    # not closed, records the controller could not read), refuses the removal/upgrade while the recovery code is still
    # installed. R4-07a: the refusal then starts the (still enabled, still installed) service again, so the supervisor
    # that owns the recovery is running when the package operation aborts - a stopped service has no recovery path.
    # The supervisor starts Auto only from an owner-started intent it finds on disk, never from this start.
    # Plan item 54 (F-16/F-17): the first guard writes the maintenance marker under the control lock before it assesses, so
    # a Start between the assessment and the stop is refused (MAINTENANCE-IN-PROGRESS). The second guard ('-stopped') first
    # waits (bounded, STOP_WAIT) until every service process has exited - init.d stop only asks procd - and refuses when
    # the supervisor's shutdown record says its recovery did not finish. Any refusal removes the marker; on success it
    # stays for the new package's preinst/postinst (an upgrade) or for good with the removed package (a removal).
    prerm=header+'if [ "${1:-}" = upgrade ]; then action=upgrade; else action=check; fi\n'+guard_block('"$action"')+'''/etc/init.d/homensai-vpn stop
if ! '''+guard_block('"$action-stopped"')+'''then
    /etc/init.d/homensai-vpn start || echo LIFECYCLE-RESTART-FAILED: the service could not be started again after the refusal >&2
    echo LIFECYCLE-REFUSED-AFTER-STOP: the recovery is not finished, the service runs again, the package operation is aborted >&2
    exit 1
fi
/etc/init.d/homensai-vpn disable
if [ "$action" = check ]; then
    # Removal: no DNS-through-both-tunnels snippet (dns_dual) stays behind; each GL per-tunnel dnsmasq runs GL's own
    # configuration again. Auto's Stop already removed them; this covers a stopped service with leftovers.
    for snippet in /tmp/dnsmasq.d.*/homensai-dns-dual.conf; do
        [ -f "$snippet" ] || continue
        instance=${snippet#/tmp/dnsmasq.d.}; instance=${instance%/homensai-dns-dual.conf}
        rm -f "$snippet" && /etc/init.d/dnsmasq restart "$instance" >/dev/null 2>&1 || true
    done
fi
exit 0
'''
    return {'preinst':preinst,'postinst':postinst,'prerm':prerm}


def sdk_fragment():
    rows=['# Generated by package_hooks.py; do not edit independently.']
    for name,body in scripts(SDK_VERSION).items():
        body=body.replace('$','$$').replace(SDK_VERSION,'$(PKG_VERSION)-$(PKG_RELEASE)')
        rows.extend(['define Package/homensai-auto-vpn/'+name,body.rstrip(),'endef',''])
    return '\n'.join(rows).rstrip()+'\n'


if __name__=='__main__':
    (SOURCE/'package-hooks.mk').write_bytes(sdk_fragment().encode('utf8'))
