# Next-stage execution evidence

## First implementation checkpoint — offline executor and candidates

Scope: development branch only; no router installation, VM resume, native worker
arbitration claim or replacement of the immutable alpha6 release.

Implemented in `cascade_executor.py`:

- Per-edge ephemeral proof registry: source/target, transaction nonce, root,
  pre-hop/desired order, semantic policy hash, generation, metadata/profile and
  recovery revisions, boot identity, cooperative lease and expected client path.
  Probe evidence must be recent, profile-bound and explicitly successful for
  DNS/HTTPS. Proofs are single-use and invalid after restart.
- Cooperative MemoryBackend lease shared by simulated executor, worker and
  operator. Contention, expiry and changed policy refuse writes.
- Bounded checksummed journal with atomic replacement, file/directory fsync,
  independent original-root/pre-hop snapshots and previous-good copy. Unknown
  fields are refused. A corrupt current file never replaces the previous-good
  copy. Recovery observes state and stays HELD; it does not restore or enable
  automatically from an ambiguous journal.
- Offline executor consumes actual CascadeModel intents across server/channel/
  protocol transitions and stable root return. Failed second-hop rollback keeps
  the first reserve and preserves the original root.
- Client-witness verifier rejects self-declared alternate expected interfaces or
  exits, stale/early/future/wrong-transaction evidence and unsuccessful DNS/HTTPS.
  This is not yet an extension of the source-bound Windows collection helper.

Implemented in `candidate_runtime.py`:

- Inactive registered-profile start/connect/failure/timeout/cancel/owned-cleanup
  contracts on MemoryProfileBackend. Removed or externally revised profiles are
  held and never overwritten; the already-connected primary is unchanged.
- Isolated-binding probe reservation with concurrency, duration and total byte
  limits. Failed/cancelled reservations remain charged; changed bindings and
  replayed results are refused. It executes no real network probes or namespaces.

Evidence: 28 new Python test methods; full Linux Docker check at this checkpoint
passed 260 application tests, 5 QA tests and 8 UI suites. Process-death injection
interrupts before/after each journal phase write, with restart remaining HELD
and no additional backend writes. Eight simultaneous lease contenders yield one
owner. All artifacts/measurements here are offline fixtures.

Initial focused run: 5 errors in one repeated metadata test, caused by reusing
time 1 after time 2. Fixed the test to advance monotonic time for each case;
the production clock-regression refusal remains. The corrected focused run
passed. Review also strengthened recovery to check metadata/hash/revisions and
phase-specific order, rather than generation/order alone.

Task status: NEXT-02, NEXT-03, NEXT-04 and NEXT-07 completed within their explicit
offline/test-double scope. NEXT-01, NEXT-05, NEXT-06 and NEXT-08 are in progress:
the source-bound helper, complete recovery/control integration and actual virtual
network acceptance are not claimed complete. Other tasks remain open.

Native capability remains UNVERIFIED. Only exact MemoryBackend types are
accepted, deliberately preventing this new code from executing router writes.


## Additional interface checkpoint — alpha7 development

NEXT-16/18/19 implemented in analytics_panel.inc.js and dashboard28/ui15. Full hierarchy display, explicit uncertified suggestions, retained-event timeline, day/week/month recovery aggregates and four private column-whitelisted CSV exports. Calendar boundaries use Europe/Berlin and DST tests; event timestamps are UTC. Trial/automatic attempts are separate. Missing event sequences, unpaired outcomes and retained-window gaps remain unknown; durations cover recorded phases and are not full outage measurements. Browser matrix and screenshot: qa/alpha7-ui-matrix.json and qa/ui-alpha7-overview.png. Eight EN/RU/mobile/desktop cases passed without document overflow. The synthetic transition CSV actually downloaded and contains one commit and one rollback. NEXT-17 remains partial: no new probe/client evidence exists in the old history. The native executor is still disconnected from router services.


## Runtime / migration / witness checkpoint

Python 3.9.15, Lua 5.1.5/CJSON real interpreter tests passed; UCI cursor was mocked. Private full own-UCI snapshot conversion preserves original sections/anonymous flags and secrets, rejects redacted inventory, and clears Auto. Source-bound Windows DNS/HTTPS helper SelfTest passed without network calls. Safe attempt/retry IDs and sanitized probe/phase evidence are now integrated into native history and the timeline/CSV. Rich history is byte-bounded with aggregate counters retained. See NEXT-STAGE-REVIEW.md, alpha7-load-report.json and alpha7-git-reconciliation.json. Remaining SDK and automatic runner boundaries are explicit in SDK-ACCEPTANCE.md and CI-PRIMARY.md. New isolated virtual-copy acceptance is pending; no physical router deployment. Immutable-source CI is not claimed passed until its receipt exists.
