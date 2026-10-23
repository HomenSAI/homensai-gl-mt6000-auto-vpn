<!-- current-release-context:0.9.0 -->
> Technical reference. Current release: **0.9.0**; [scope and status](CURRENT-STATUS.md). Dated examples and observations below retain their original scope.

# Persistent router preparation

The System readiness page includes a read-only MT3000 preparation report. The same report is available locally with:

    python3 /usr/lib/homensai-vpn/preparation_status.py

It checks saved HNAT state, the selected WG1/OV1 autostart flags, competing stock VPN/SFE boot entries, the exact preserved SFE autoload file and loaded software-acceleration modules. All checks must be fresh. A pass does not prove runtime HNAT state, correct DNS, firmware compatibility, a connected VPN or client connectivity; authoritative native checks still apply.

For the qualified MT3000 4.11.0 setup, follow [the actual operations and undo record](MT3000-OPERATIONS-2026-10-22.md). Preserve an encrypted supported configuration export before changes. Keep the exact stock autoload bytes outside /etc/modules.d, retain original startup settings, and disable only the reviewed competing boot paths. Do not force-unload modules or remove packages/drivers. A missing or modified preserved autoload file is UNKNOWN, not a successful preparation.

DNS preparation is conditional: inspect listener/upstream ownership and the stock API result. The earlier inactive enabled AdGuardHome owner blocked the stock DNS API with DNS_BUSY. A working DNS owner must not be disabled merely because the earlier test router needed that correction.

Undo is deliberate: restore only verified original values and exact preserved files when leaving the qualified native setup. Refuse restoration over unrelated newer edits. Restoring acceleration or stock automatic arbitration invalidates native readiness. Neither installation nor this read-only report starts profiles, enables Auto, changes the Windows network or claims external-LAN certification.
