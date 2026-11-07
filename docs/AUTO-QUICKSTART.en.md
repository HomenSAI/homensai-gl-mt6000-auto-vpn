<!-- doc-role: current -->
# Quick start

[Full guide](CURRENT-STATE.en.md) · [Actual installed/released state](CURRENT-STATUS.md)

**License:** [HomenSAI Personal & Commercial Source License v1.0](../LICENSE) — source-available, not open source.

1. Open the intended router's Auto VPN page. Verify the device and management path; identical private IPs on two adapters can lead to different routers.
2. The first-run wizard opens by itself: Router → Channels → Behaviour → Terms and start. Accept the current terms yourself at its last step if not already accepted; a prior acceptance is skipped on later visits. Training is optional: Settings → Reference → Help and training.
3. Configure servers/keys in stock GL.iNet VPN. Choose two distinct, already bound clients in wizard step 2 (Channels) as Primary and Reserve; later in Settings → Channels: primary and reserve. A stopped configured client is not proof of health.
4. In step 3 (Behaviour) review How fast to switch and Router load; Telegram is optional. History (live log 1–2000, detail days 1–7) and speed tests are in Settings later. "Save without starting" writes the settings; it does not start Auto.
5. Check Router readiness (wizard step 1, later Settings → System and diagnostics; Console: System tab) and the status on Home. Prepared continuous MT3000 router-probed mode does not need a LAN certificate; a separate client-confirmed trial does. Do not bypass a refused prerequisite.
6. Press Check now for fresh observations, then turn the Auto switch on (or use "Accept terms and turn Auto on" in the wizard) when the selected mode is ready. Wait for confirmed selection and fresh DNS/HTTPS; a queued ACK or Connected interface is insufficient.
7. Manual switching ("Switch here" on a channel card) can work while Auto runs and never turns it off: Auto keeps watching the chosen channel and moves traffic to the other one if it fails. A working reserve is normal. Return only under current readiness, policy and operator intent; the hold-reserve policy keeps a working reserve, while a pinned reserve that itself fails (proven by a fresh check) is rescued to a healthy primary after a short stability wait. A lower-delay recommendation never switches traffic itself.
8. To finish, turn the Auto switch off and verify the actual restoration/cleanup. A retained reserve or failed recovery is a separate outcome, not successful restoration. Auto that you turned on comes back by itself after a reboot or power cut, with every start check; turning it off cancels that.

Timing (dedicated MT3000, Lua line; a historical measurement made with the previous "failures in a row" detector): with fast detection (on by default since alpha24) Auto decided about 26-28 s after an outage at probe level 1, because that detector needs 3 failed checks in a row. The default detector is now the HMM probability model, which decides from the probability that the outage will last (see [how it works](HOW-IT-WORKS.en.md)); its decision time differs and is not covered by this figure; traffic moves 1.3-1.6 s after the decision, and a manual click is done in about 0.7 s. [Numbers per layer](MEASUREMENTS.en.md#8-runtime-pyramid-and-switch-times).

Events and reasons on Home shows the latest 5 (or 20) rows with filters, newest first; tap a row for "why". The Console Log tab shows 20 rows plus the live log. Confirmed route selection ("Traffic here") and channel health (the lamp) are distinct.

[No internet / recovery](../router-test-kit/EMERGENCY.md) · [LAN modes](LAN-HELPER.en.md) · [Retention](HISTORY-RETENTION.md).
