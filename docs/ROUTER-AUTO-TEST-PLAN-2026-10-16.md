<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Prepared physical failover test — 2026-10-16T18:53:54.0327526+02:00

PREPARED / NOT RUN. Authorisation currently permits read-only inspection and backup only.

## Gates before any change or outage

1. Confirm independent Internet/recovery outside GL-MT6000. Current Wi-Fi and Ethernet share its gateway.
2. Diagnose Windows 10051 on interface-bound HTTPS. Ethernet SSH/DNS passed, HTTPS did not. Do not attribute local route failure to router or stop NordVPN/change Windows routing without approval. Require source/interface-bound DNS, TLS/HTTPS and VPN exit evidence before trials.
3. Resolve inactive configured source after approval. The active generic OpenVPN and WireGuard rules are plausible first candidates. The other active OpenVPN serves a special policy and must not be silently repurposed. Review order semantics, source/reserve and expected exits.
4. Hardware still runs 0.6.0-alpha5-1; UCI correction is local alpha7-2 only. Obtain deployment authorisation and complete outstanding native/network acceptance before candidate installation. Offline full-cascade contracts are not a live GL.iNet adapter.
5. Review prior ROLLED-BACK journal with original_restored=false against actual policies. Establish a fresh client-certified baseline; do not label historical rollback successful without proof.
6. Recheck fresh probes/handshakes, configuration fingerprints, HNAT runtime disabled, offload, explicit IPv6 policy, Kill Switch and vendor worker state. Do not disable anything merely because a module is loaded.
7. Keep the verified private backup and old package/recovery instructions off-router. Archive parsing is not a restore test. Plan selective recovery, not blind live extraction of /etc over root.

## Sequence after separate approval

- Refresh baseline and expected exits; start one bounded, explicit session-loss-approved transition between already-active eligible generic profiles with independent client/management.
- Require fresh source-bound DNS, two HTTPS checks and matching VPN exit from the LAN client. Connected alone is insufficient. Preserve special destination rules and Kill Switch.
- Verify reserve traffic; request Stop; require restored policy fingerprint plus fresh original-source DNS/HTTPS and client exit before rollback PASS. If source is unhealthy, report guarded reserve/hold and original_restored=false.
- After normal switch/rollback passes, inject a scoped timed path fault with ownership guards and independent kernel expiry. Never stop all VPNs, restart networking or remove Kill Switch as a shortcut.
- Verify absent/expired client confirmation causes independent rollback/hold without false success. Then observe bounded automatic operation with timestamped changes, recovery duration and errors.
- A two-profile success does not certify full server/channel/protocol cascade.

Abort on management loss, unexpected direct WAN, leak, uncertain IPv6, conflicting worker/config changes, stale proofs or uncertain rollback. Use independent recovery path and previously authorised recovery procedure. Keep raw configuration, credentials, recipient/session identifiers and exits private; publish anonymised timestamped results only.

## Preparation update — 2026-10-16T19:14:13.5975777+02:00
Cable 10051 and inactive-source gates resolved under owner authorisation. Source/interface-bound DNS and two TLS/HTTPS checks passed; exit matches active generic OpenVPN main, generic WireGuard reserve retained. Only own plan_source changed; Auto off, package unchanged. Wi-Fi remains preferred but shares router gateway; independent recovery/test-window and deployment/native-acceptance gates remain. See ROUTER-TEST-PREPARATION-2026-10-16.md.
