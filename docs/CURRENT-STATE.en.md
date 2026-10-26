<!-- doc-role: current-canonical -->
# Auto VPN — current source behavior

Source candidate: **0.9.1-alpha26**, package **0.9.1-alpha26-2**, Minimum UI. [Delivered and installed state](CURRENT-STATUS.md) and [verification](VERIFICATION-ALPHA26-2026-10-26.md) are separate from source metadata.

## Minimum and Advanced menu

Minimum shows Auto state, the confirmed channel, the actual Auto button and reserve health. Connection details are collapsed. Minimum stays accessible with Auto OFF, stale data or an error; a missing pair on fresh idle OFF offers setup. Display access never grants Start permission.

Advanced menu opens Channels first, then retains the last advanced section in this session. The header returns to Minimum. Five sections replace the old twelve: Channels, Diagnostics, Events, Settings and Help. On phones, Sections opens the navigation. Browser Back/Forward and old section links retain their destinations. Opening sections does not send command RPCs.

Both views reuse the same actual Auto control. Pending commands are not completion. Start checks current control revision, monitoring and backend prerequisites; the click handler rechecks evidence age. Stop remains governed by the existing recovery contract. Confirm the actual restored/retained route; stopping Auto does not by itself mean disconnecting VPN or Internet. Explicit Start is required after restart.

## Channels

The selected primary and reserve show name, independent selection and health. A healthy standby is neutral. Details contain endpoint, protocol, country, fresh HTTPS RTT and observation time. Missing data is not zero. Other profiles open in a searchable disclosure. Profiles and VPN keys remain owned by GL.iNet; this page never connects an inactive profile just to display it. Manual channel selection retains its own guards.

## Diagnostics

Checks requests a bounded connection measurement without selecting a channel. QUEUED/RUNNING is not a successful result; completion must match the request and measured snapshot. Conditions and technical data open on demand. Router-originated IPv4 observations are not proof of a LAN client's path.

Speed opens its actual measurement panel; it consumes traffic only after explicit review/start. CPU, route, cooldown and quota guards, sequential channels, cancellation and job isolation remain. Missing/error directions are gaps, not zero throughput. Old results, rankings and test preferences are collapsed. Controlled artificial faults are outside normal operator navigation and remain in test tooling.

Recovery provides instructions and existing guarded actions. Technical details retain the live log and all-profile observations. No universal automatic network repair is implied. [Control effects](CONTROL-AND-SETUP.md) · [Recovery](../router-test-kit/EMERGENCY.md).

## Events and retention

The journal initially shows up to 20 recent rows with period/type filtering; search/sorting and detailed analytics are disclosures. More history reads retained records. Historical main/reserve identity and reasons stay tied to event time, not the current pair. No missing events or routes are reconstructed.

History and Traffic retain their measurements, exports, monthly counters and explicit gaps. [Retention](HISTORY-RETENTION.md) remains bounded: 1–7 detail days, separate monthly/lifetime counters, configured browser observation limits. Increasing retention cannot restore expired detail. Latency/route timelines retain their existing bounded windows.

## Settings, terms and help

The pair editor keeps an unsaved draft through polling. Save opens review, verifies fresh configuration and uses the existing writer without starting Auto; negative/unconfirmed saving retains the draft. Leaving dirty settings offers Save/Discard/Stay. Browser language/theme are under Interface in this browser; saved defaults and optional preferences are under Additional settings. The accepted B design is fixed; old layout preferences no longer select alternate layouts.

First setup retains eight validated internal stages grouped into three phases. [Setup](FIRST-RUN-SETUP.md) covers required fields. Current terms are accepted by the person, never by an agent on their behalf; a package update preserves acceptance of the unchanged terms version. Telegram is optional and never sends a test on navigation/save without the explicit existing action. Secrets remain on the router and are not returned in status.

Help starts with four common tasks. Full instructions/codes, eight lessons/eleven questions and About remain available. Training does not invoke router control; answer grading, wrong-only retries and scroll/focus preservation remain. [Built-in Help](BUILTIN-HELP.en.md) · [Training](TRAINING.en.md) · [Codes](ERROR_CODES.md).

## Qualified scope and delivery

Prepared continuous Auto is qualified only for the documented MT3000/GL.iNet 4.11.0 arrangement and two existing independent clients using router IPv4 evidence. Architecture all, model selection or dependency checks do not qualify arbitrary firmware, MT6000 continuous mode or IPv6.

The optional [client-confirmed bounded trial](CLIENT-TRIAL.md) uses its own real LAN witness/certificate. It is distinct from normal router-probed Auto, which does not require a LAN certificate. [LAN helper modes](LAN-HELPER.en.md) and their side effects remain explicit.

[Install](INSTALL.en.md) one immutable package with matching SHA256/evidence/kit; preserve verified private recovery and do not downgrade an active newer installation. This is a design prerelease, with CI/VM/browser-fixture proof recorded separately from physical-device, external LAN/fault/power and 24-hour acceptance. [Release notes](RELEASE-0.9.1-alpha26.md) · [Verification meanings](VERIFICATION.md).
