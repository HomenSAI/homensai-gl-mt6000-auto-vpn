<!-- doc-role: current-canonical -->
# Auto VPN — current source behavior

Current source: **0.9.1-alpha33**, package **0.9.1-alpha33-1**. Installed on the dedicated MT3000; both real speed tests passed with Auto/monitor pause and automatic restoration. The responsive reference table and truthful diagnostics are delivered. [Current state](CURRENT-STATUS.md) · [Device proof and limits](VERIFICATION-ALPHA33-INSTALLED-2026-10-26.md).

Speed tests now request a bounded cooperative pause from the Auto controller and background monitor. Measurement starts only after both active processes acknowledge a safe loop boundary. VPN connections, routing, Auto intent and service settings are preserved. CPU admission uses fresh CPU accounting after the pause, not minute load average. Normal completion, failure, cancellation or worker loss withdraw the pause; monitoring obtains a fresh observation before Auto continues. A manual Stop is never undone. Manual switching is refused during the quiet window. Both selected speed tests completed on the installed alpha33 with a verified pause and automatic restoration; see the physical receipt.


Minimum remains accessible with Auto OFF, unknown data or errors. It shows the real Auto state, confirmed traffic channel and independent reserve health. Its button opens the former Overview. The expanded interface retains its twelve destinations, legacy page content, additional-navigation group, settings and A/B/C appearance selection. Return to Minimum reuses the same actual Auto button and action label without cloning handlers. Old beta nested links map to the corresponding legacy pages. Navigation does not run command RPCs.

Start requests are pending until the controller confirms them. A preflight refusal consumes only the matching accepted request and reports FAILED plus the specific BLOCKED reason, allowing retry without indefinite Starting. A late failure cannot overwrite a newer Start or Stop. Stop retains the existing recovery contract. Restart requires explicit Start.

The pair uses exact, distinct selected vendor tunnel identities, including a second OpenVPN client slot after channels have been removed. Readiness, startup preparation, firmware-zone checks and network compare-and-swap use those identities. Disabled historical profiles do not consume the active-probe limit. A healthy standby is not a failed traffic path; old observations cannot confirm current selection.

Reviewed preparation actions show the exact selected source/target interface. They change only bounded startup/acceleration settings, record original values and verify readback. They never restart the network or force-unload acceleration. Runtime blockers and restart requirements remain enforced. [Control effects](CONTROL-AND-SETUP.md) · [Codes](ERROR_CODES.md).

Existing monitoring, history, speed tests, terms, Telegram, training, keyboard focus and scroll behavior remain. Speed and fault tests never run on navigation. Artificial fault injection remains in test tooling. Terms acceptance belongs to the person and is preserved when the terms version is unchanged. Secrets stay on the router.

Continuous router-probed IPv4 Auto remains qualified only for the documented dedicated MT3000 / GL.iNet 4.11.0 arrangement. Router DNS/HTTPS success is not external LAN, IPv6, physical failover or unattended endurance acceptance. [Client trial](CLIENT-TRIAL.md) · [Recovery](../router-test-kit/EMERGENCY.md).

[History and retention / История и сроки хранения](HISTORY-RETENTION.md).

Diagnostics distinguish a partial HTTPS quorum failure from zero validated HTTPS responses and unavailable detail. Per-endpoint status is recorded without raw exceptions or credentials; an unsupported HTTP endpoint is a check-endpoint fault. Old incidents are never explained with today's profile state. Same-measurement incident/monitor rows are correlated only with retained matching timestamps. Vendor-worker contention is a temporary wait; an accepted Start with an old STOPPED observation is shown as pending Start. The diagnostic reference table wraps codes, descriptions and open explanations within the viewport, with a stacked mobile layout.

The final alpha33 observer preserves a bounded allowlist of endpoint diagnostics through the identity check and discards them with the rest of old-identity health on a rebind.
