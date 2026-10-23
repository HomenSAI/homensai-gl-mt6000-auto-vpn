<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Offline continuation, 20 October 2026

The owner asked to finish work that does not require the physical test router. The mobile
GL-MT3000 is not connected. The primary GL-MT6000 and Windows networking remain outside
this continuation. All live package tests use a marked, independently copied x86 OpenWrt VM
inside an unprivileged Docker container with network `none` and no host mounts.

The current candidate is alpha12 (`586a2a5305dbb638dfeac05755c8f9e1de736408`): exact-source
dual-runtime CI passes 449 application tests, 85 QA tests and 30 Node UI suites. The canonical
IPK is 654970 bytes, SHA256 `d7a2b47e1c3afc4b6c042e7f1ea1b23941d438630915fd9b83597ae381203b29`.
Older alpha10/11 results below retain their actual source identities.

The corrected visible-frame alpha11 matrix completed all 50 personas with no retries:
5,495 steps, 14,560 attempted clicks, 3,381 field edits, 1,487 RPC calls, maximum lag 557 ms.
All 50 passed. Parser/payload comparison carries these normal-flow results to alpha12:
all compiled JavaScript outside `renderTermsGate`, its one conditional call receiving the
already loaded status, and the version literal is byte-identical. All other 69 payload
paths/modes and lifecycle hooks match, apart from the program version and controller
version comment. This does not claim that the old 50 personas tested the new first-run gate.

The first-run page now shows the required owner/model/version/style identity, header badge
and footer. Its 36 Node combinations pass; legal declarations, all nine legal gate strings,
checkbox setup/sync/listener and the acceptance handler match the previous source exactly.
Accepting terms v1 in the disposable VM still requires the owner's explicit authorization;
the requested normal post-consent LuCI matrix is not replaced by read-only terms views.

Actual alpha12 read-only terms matrix: **12/12 PASS** (ABC × EN/RU × 1440/390),
with live program/package identity on each view, two unchecked boxes and disabled Accept.
The diagnostic 60-second mode recorded 39 RPCs, zero timeouts, 10 calls over the ordinary
20-second deadline, maximum 38.528 seconds. The full run took 580.303 seconds. The first
full attempt stopped after three passes when same-URL navigation retained its previous
Document; a unique benign navigation query fixed the harness, and the failed result remains
retained. No consent was accepted. See [the machine-readable evidence](../qa/OFFLINE-CONTINUATION-2026-10-20.json).

The earlier alpha11 long observation was deliberately stopped before a potential consent
change: 1582.656 seconds, 14 samples, zero failures/gaps, both cleanup witnesses confirmed.
Acceptance was then rejected before execution, so no consent/configuration change occurred.
This is STOPPED, not 12-hour PASS. A fresh alpha12 observation uses its own final-source
manifest and output directory. An optional guarded profiler was refused and obtained no
measurements; its session cleanup is unconfirmed, and no timing cause is asserted.

## Backend changes and public Start contract

Existing JSON state now refuses duplicate keys, nonfinite numbers, excessive nesting and
invalid numeric values. A present falsey lease is corruption, not a missing lease to rearm.
A rejected future Return timestamp cannot poison a later valid request. Terminal Stop uses
the same serialization as UI control, becomes global when policy cannot be read, and keeps
the high-water timestamp across wall-clock rollback.

`status.auto_control.control_revision` is a public, nonsecret 32-character lowercase hex
marker. A client must read live status and send exactly
`native_start {"control_revision":"<current marker>"}`. Missing, old or malformed markers
refuse. Every Stop rotates the RAM marker, including repeated Stops whose durable write is
deduplicated. A delayed Start arriving after Stop therefore cannot restart the previous
intent. A runtime/supervisor restart also invalidates outstanding Start requests.

`native_stop {}` remains independent of Start/Return pending state and has no confirmation
or cooldown. Slow read-only Start diagnostics run outside the short Stop serialization
lock; final acceptance rechecks the revision, configuration and recovery state under that lock.
This is ordering protection, not authorization to run Auto on an unsupported platform.

The backend agent added 24 regression tests; its 145 focused tests passed on both Python
3.9 and 3.11. Exact commit `984781141d5eddce4442941ee28ff851da7cbf28` passed the complete
449-application / 77-QA / 28-UI matrix. Lua checks run in the 3.9 image; Git/Node checks run
in the 3.11 image. The same commit's 50 backend personas sent 18,015 requests (2,349
accepted and 15,666 refused), with zero oracle violations. Later UI fixes require their
own current-commit matrix before publication.

## Browser failures retained for review

The frozen alpha10 synthetic matrix completed all 50 personas: 31 passed and 19 failed.
It performed 3,931 interaction steps, 12,904 attempted clicks, 1,696 field edits and 1,182 RPC
calls. Maximum observed event-loop lag was 848 ms; no horizontal overflow or invalid RPC
argument values were recorded. These totals do not make the failed cases pass.

Seventeen failures were load/reload readiness failures. Two actionable defects were found:
stale lesson-navigation nodes could move the lesson index below zero (`undefined.icon`),
and repeated setup launchers produced 114 expensive readiness checks in one persona.
The lesson failure was reproduced independently in Node before a fix. Their fixes,
regressions and a new frozen matrix must be assessed separately from the retained baseline.

Actual installed LuCI has a separate browser harness; synthetic fixture results do not
certify the real LuCI loader, CSS, RPC authorization or vendor firmware. The harness keeps
only sanitized phase/resource metrics and numeric RPC envelope codes. Cookies, sessions,
CSRF values and request/response bodies are never persisted as evidence.

The browser fixture was found to append its active iframe below an unused 900-pixel iframe.
That offscreen layout invalidates timing/visibility acceptance from the earlier attempts;
all their raw failures remain retained. The corrected fixture reuses one visible iframe and
requires its complete rectangle to fit the host viewport at both ends of every persona.
The independently reproduced lesson and setup-check defects do not depend on that layout.

Direct container-local HTTP probes, using a disposable session entirely in RAM, authenticated
successfully and returned the exact installed alpha11 identity. Status took 21.318/25.495
seconds; inventory took 18.943/21.151 seconds on the two local LuCI/ubus routes. These
at/above-20-second responses explain observed default LuCI RPC aborts independently of
per-request proxy startup. Default-deadline performance remains an open VM/environment
criterion. A separately declared, bounded 60-second RPC allowance in the browser harness
can verify DOM behavior and does not constitute default-performance acceptance. No product
timeout, device configuration or Windows networking was changed to obtain that result.

## Package and SDK provenance

Release bytes come from the immutable full-repository Git archive and the supported Linux
runtime matrix. Windows Python 3.14 can produce different compressed IPK bytes from an
identical payload, including compression-derived Installed-Size. Only the exact canonical
artifact hash may appear in the manifest, install kit, CI receipt and release.

SDK source export must preserve repository-root `.gitattributes`: use the full commit
context with `git archive <commit> -- router`, then strip the `router/` prefix without
converting file bytes. `git archive <commit>:router` loses root attributes and was observed
to convert pinned style files to CRLF. That failed tooling experiment remains private
evidence; it does not justify changing the upstream style assets or accepting a mismatched
package. See [SDK acceptance](SDK-ACCEPTANCE.md) for the bounded payload-build proof and
its explicitly separate vendor/runtime-dependency limits.

## Save and remaining acceptance

Local Git, primary Gitea, a reviewed GitHub snapshot/release, and a restore-verified recovery
archive are separate results. Compare the current branch SHA with the private CI/publication
receipts and the backup `CURRENT.local.json`; an older checkpoint is not a current save.
The owner is reconnecting D:. Until it is available, prepare and verify the current archive
locally and keep the D copy pending. Do not replace the backup pointer before its destination
bytes match the source hash.

Physical identity/firmware/bootloader and recovery backup, a verified GL-MT3000 vendor
adapter, cooperative writers, native multi-hop/inactive profiles, independent LAN/IPv6/
Kill Switch behavior and physical reboot/power-loss acceptance remain open. A completed
current-source long observation is also separate from a short VM smoke or a launched run.
