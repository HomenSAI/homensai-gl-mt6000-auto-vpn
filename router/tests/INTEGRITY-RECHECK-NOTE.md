# Deferred integrity re-check after opkg (safety review F-02, product side) - working note

Branch fix/a9-integrity-recheck-20261107 (base integ/a9-night-20261107, 062a2f4d). Version stays 2.1.0-alpha9-1
(bump-version.py --fingerprint-only only). Owner rule: keep this note current until the branch is merged.

## Problem
postinst runs `/etc/init.d/homensai-vpn restart` while opkg still holds /var/lock/opkg.lock (opkg-lede unlinks it only
in opkg_conf_deinit, after postinst). start_service -> integrity_gate -> `homensai-vpn-integrity boot` answers
INTEGRITY-DEFERRED / mode normal and nothing ran the check later, so after every install/upgrade status.integrity stayed
INTEGRITY-DEFERRED until the next service start: the self-check never ran on the new files.

## Design
- `boot`, when it defers, launches `homensai-vpn-integrity recheck` detached (stdin/stdout/stderr on /dev/null, so the
  init's `$(sh tool boot | sed)` does not wait for it; the init and opkg finish as before).
- `recheck` (POSIX sh, same tool, same `check` function):
  - one instance: RAM lock directory RUNTIME/integrity-recheck.lock with the pid; a live holder means a recheck is
    already waiting (it checks whatever files are installed when opkg ends), a dead holder's lock is taken over;
  - waits while the opkg lock exists, every RECHECK_EVERY=10 s, at most RECHECK_LIMIT=600 s;
  - acts only while integrity.json still says INTEGRITY-DEFERRED (a later service start already wrote the real result:
    nothing to do); a package operation that began during the check sends it back to waiting;
  - read-only verification. Clean -> INTEGRITY-OK; permissions only -> INTEGRITY-MODE-DIFFERS; no manifest and no
    pristine copy -> INTEGRITY-UNVERIFIED (all mode normal, exactly what `boot` writes), log INTEGRITY-RECHECKED <code>.
    The monitor is NOT restarted for these.
  - content damage (FILE-DAMAGED / FILE-MISSING / MANIFEST-): log INTEGRITY-RECHECK-DAMAGED and, when the service runs
    (procd reports a running instance) and is enabled, `/etc/init.d/homensai-vpn restart`: the existing start path then
    restores from the pristine copy while the instances are stopped and decides normal / no-c / python / stopped /
    no-auto exactly as at boot (no second implementation of the consequences). The lock is released before the restart,
    so a start that defers again (another opkg run) can launch its own recheck. A service that is not running is not
    started: the record becomes INTEGRITY-RECHECK-DAMAGED with the mode the damage implies (mode_of), so Start is refused
    for mode stopped (BH-04 blockers read the mode) and the next service start restores/decides as usual.
  - opkg lock still there after 600 s -> INTEGRITY-RECHECK-TIMEOUT, mode normal (the service keeps running as before;
    a manual restart after the installation, or the next reboot, checks the files).
- Never: starting Auto (the restart is the same init restart postinst already does; Auto resumes only from an
  owner-started intent on disk), touching the owner's config / journal / history, restoring while the service runs.
- Python/Lua twins: unchanged. Both only publish integrity.json (status.integrity) and read its `mode` for the Start
  blockers; the recheck writes only mode normal itself, and no-auto/stopped still come from a service start or the
  not-running damage record. The page needs no logic change (banner only for no-auto/stopped); the catalogue gets rows.

## New codes (catalogue rows RU+EN, docs/ERROR_CODES.md generated)
INTEGRITY-RECHECKED, INTEGRITY-RECHECK-DAMAGED, INTEGRITY-RECHECK-TIMEOUT; INTEGRITY-DEFERRED text corrected (the
installation does not restart the service after it ends; the check now runs again by itself).

## Steps
1. Tool `recheck` + boot launch + tests (test_integrity_faults RecheckTest) + catalogue rows + this note.
2. Regenerated outputs (dashboards/help, legacy page, docs sync) + fingerprint.
3. Design document row (INTEGRITY-MATRIX).

## Status
- step 1 committed: tool `recheck` + boot launch, RecheckTest (9) + BootTest opkg case extended; test_integrity_faults 57 OK in Docker (python39, dash); busybox ash scenario (alpine 3.20: detached launch, single lock, restart path, not-running record, timeout) ALL-OK.
- step 2 committed: rebuilt dashboard210.js (609 740 B) + help210.js, qa legacy page, docs sync (ERROR_CODES.md: 3 new rows + DEFERRED text); 128 Node test files OK; sync-documentation --check OK.
- step 3 committed: INTEGRITY-MATRIX design document (tool row + recheck row + DEFERRED sentence; docs only). boot_resume FINAL comments (both twins) left as they are: no-auto/stopped still only come from a service start or from the not-running record, when no boot_resume runs.

## Final test status (docker homensai-vpn-python39:night, node 24 local)
- Full router/tests Python suite: 2645 tests, 4 failures, all the known container-only ones listed in
  MONITOR-BOOT-NOTE.md (test_failure_matrix.Settings x2, test_priority_recovery and test_setup_config pending_delta:
  RPC-RATE-LIMIT), none touch the integrity tool. All router/tests/lua/test_*.lua pass. 128 Node test files pass.
- qa/test_documentation_current OK; sync-documentation --check OK; bump-version --check VERSION-CURRENT 2.1.0-alpha9-1.
- Not done here (separate ticket, kit side of F-02): the install kit template / kit_checks still treat
  INTEGRITY-DEFERRED as not OK; with this fix they can wait (up to ~10 min) for the real result instead.
