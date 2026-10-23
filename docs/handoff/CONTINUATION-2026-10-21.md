<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../CURRENT-STATUS.md) · [documentation index](../DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Owner-resumed testing - 21 October 2026

The owner explicitly resumed after the PC reboot and authorized extensive testing of the dedicated portable GL-MT3000, including manual and automatic scenarios. This supersedes the earlier stop for the active session; original observers remain STOPPED and are not automatically resumed. Primary GL-MT6000 and PC Wi-Fi stay excluded from changes.

Owner confirmed Wi-Fi is on the primary MT6000/gateway192.168.8.1; management cable is the portable MT3000/gateway192.168.11.1. Fresh host readback agrees. Owner again selected router-only testing: no separate client witness is available. Router-originated data checks never become LAN/IPv6/Kill Switch acceptance or a forged client confirmation.

## Corrected software batch

- Manual return now passes its control revision through the slow source health check. A Stop arriving during that check prevents the requested return; trusted recovery remains available.
- Explicit runtime/persist scopes reach the dispatcher and supervisor. An absent/terminal manual queue no longer creates control directories, locks or revisions; the former progress/Stop/expiry regression is fixed.
- Manual commit-boundary regressions now isolate Stop's UUID rotation from a fixed transaction fixture. Five native-branch checks pass, including Stop after COMMITTED rollback and Stop ordered after completed HELD without an invented rollback-success claim.
- MT3000 read-only collector now rejects duplicate JSON fields, deadline overrun after a final read, shared physical route bindings, held firewall locks, hotplug activity, PID changes and malformed FW3 sections. Its report remains noncertifying/no-apply.
- Confirmed failed/inactive channels are red even when no route is confirmed; an unknown/stale path remains grey, transitions yellow and green still requires fresh confirmed path+health. A healthy unused channel is labelled available, not failed.
- The source version advances through alpha18 to alpha19 because alpha17 was already a saved/public unfinished source checkpoint. Alpha17 did not become a release or installation. Alpha18 exact-source CI then found39 missing human-readable diagnostic explanations; alpha19 fixes them with explicit EN/RU rows, not a weakened coverage test. Alpha18 was only staged in /tmp, never installed/released.

## Evidence and limits

The immutable pre-version corrected application snapshot passed630 tests on Python3.9 with0skips and Python3.11 with15Lua skips covered in3.9. Earlier621-test baseline with3collector failures is retained. Later hotplug strengthening passed28focused platform checks on both runtimes. The selected page is dashboard68/ui45; final versioned exact-commit CI and canonical IPK follow separately.

Synthetic Edge A/B/C desktop/mobile UI passed6/6 cases/102checks after a reviewed local-only process execution; the older100s/0-case attempt is retained. The failure cause was Windows sandbox IPC denial before any HTTP request. The later narrow red-state change has a focused Node regression; its generated page still needs the final browser check.

Fresh physical readback before this batch: alpha16 monitor-only, Bdefault, onlymonitor, accepted owner terms1, onboarding incomplete, both VPNs saved disabled1, original startup link, no native journal/guard. A new supported configuration export was encrypted immediately with a Windows-DPAPI-protected key; plaintext was not persisted.

Actual new read-only MT3000 preflight reports only the remaining candidate blockers MONITOR-ONLY-DEPLOYMENT and SOURCE-RESERVE-NOT-CONFIGURED, plus the permanent capability refusal MT3000-MANUAL-ADAPTER-NOT-CERTIFIED. No actual native/manual channel transition is claimed.

## Hardware work remains substantial

An actual MT3000 route-write adapter is not implemented/certified. Existing native Auto remains platform/monitor/LAN gated. Owner permission allows testing but does not replace missing technical implementation/proof. A bounded OpenVPN cold-start diagnostic is being prepared separately from the previously verified WG lifecycle; stock hooks/PID/daemon/crypto/TAP/LAN-disconnect differences must be reviewed before activation. No generic WG-to-OV text replacement or global OpenVPN service start is permitted.

The selected OV profile is TUN, crypto_safexcel is absent, disconnect_lan_flag absent and no OV daemon/TUN remains; a stale numeric PIDfile refers to a nonexistent process. That stale artifact must not be trusted by stock teardown or removed casually. Cleanup/guard ownership and any remediation need explicit identity checks before an active trial. Profiles/keys remain private.

## D backup

The existing intended D volume returned.23reviewed files/179747433bytes copied to a new archive directory; all file hashes/sizes,9ZIP CRC checks/1871entries and67internal manifest hashes passed. This preserves alpha16/alpha17WIP/prior supplements/urgent stop overlay; later resumed fixes are not yet covered by that archive. A final current batch archive is still needed.

## Next checks

1. Build the canonical versioned IPK from committed source and run exact-commit dual-runtime application/QA/UI CI; verify privacy, generated assets and package hashes.
2. Install only the reviewed supported monitor mode; verify own/protected config preservation, every program file, actual served page/CSS, new RPC refusal/Stop/replay behavior and own monitor recovery.
3. Continue separately reviewed bounded router-only lifecycle work where prerequisites are satisfied. Keep real manual/Auto transition, independent LAN witness, permanent FW3 repair, acceleration and unattended/reboot/power behavior open until actually implemented/tested.
4. Update RESUME-TODO with executed evidence rather than checking off the entire project. Publication of a future completed release is distinct from the previously approved WIP upload; record actual approval/remote receipts. Preserve all earlier failed/STOPPED results.
