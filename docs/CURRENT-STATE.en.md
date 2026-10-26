<!-- doc-role: current-canonical -->
# Auto VPN — current source behavior

Current source: **0.9.1-alpha30**, package **0.9.1-alpha30-1**. The new Minimum and former expanded interface are installed on the dedicated MT3000; ordinary Auto Start is verified RUNNING / OBSERVING. [Current delivery](CURRENT-STATUS.md) · [Physical proof and limits](VERIFICATION-ALPHA30-INSTALLED-2026-10-26.md).

Minimum remains accessible with Auto OFF, unknown data or errors. It shows the real Auto state, confirmed traffic channel and independent reserve health. Its button opens the former Overview. The expanded interface retains its twelve destinations, legacy page content, additional-navigation group, settings and A/B/C appearance selection. Return to Minimum reuses the same actual Auto button and action label without cloning handlers. Old beta nested links map to the corresponding legacy pages. Navigation does not run command RPCs.

Start requests are pending until the controller confirms them. A preflight refusal consumes only the matching accepted request and reports FAILED plus the specific BLOCKED reason, allowing retry without indefinite Starting. A late failure cannot overwrite a newer Start or Stop. Stop retains the existing recovery contract. Restart requires explicit Start.

The pair uses exact, distinct selected vendor tunnel identities, including a second OpenVPN client slot after channels have been removed. Readiness, startup preparation, firmware-zone checks and network compare-and-swap use those identities. Disabled historical profiles do not consume the active-probe limit. A healthy standby is not a failed traffic path; old observations cannot confirm current selection.

Reviewed preparation actions show the exact selected source/target interface. They change only bounded startup/acceleration settings, record original values and verify readback. They never restart the network or force-unload acceleration. Runtime blockers and restart requirements remain enforced. [Control effects](CONTROL-AND-SETUP.md) · [Codes](ERROR_CODES.md).

Existing monitoring, history, speed tests, terms, Telegram, training, keyboard focus and scroll behavior remain. Speed and fault tests never run on navigation. Artificial fault injection remains in test tooling. Terms acceptance belongs to the person and is preserved when the terms version is unchanged. Secrets stay on the router.

Continuous router-probed IPv4 Auto remains qualified only for the documented dedicated MT3000 / GL.iNet 4.11.0 arrangement. Router DNS/HTTPS success is not external LAN, IPv6, physical failover or unattended endurance acceptance. [Client trial](CLIENT-TRIAL.md) · [Recovery](../router-test-kit/EMERGENCY.md).

[History and retention / История и сроки хранения](HISTORY-RETENTION.md).
