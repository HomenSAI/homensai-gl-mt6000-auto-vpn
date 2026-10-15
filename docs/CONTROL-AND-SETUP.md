# Auto control and setup — 0.6 experimental series

The Overview power control requests Start or Stop. Its colour follows fresh controller observations; a queued request is not evidence of enabled switching. Start resumes only an already LAN-certified policy within its unchanged bounded deadline. It does not fabricate a trial, start inactive profiles or enable reboot autostart. Run the LAN helper when the window is absent/expired.

A durable Stop request cancels an in-flight attempt and requests verified rollback. If the original VPN is not healthy, the controller may keep a confirmed reserve and explicitly report STOPPED-ON-RESERVE. This is not restoration of the original route. The monitor continues separately.

Settings provides a three-step system wizard: existing profiles, names/channel groups/priorities, review. Saving changes only application metadata and monitoring settings. It does not change VPN keys or immediately apply route priorities. Unsupported profile pairs remain blocked by the native adapter.

The Telegram channel wizard accepts a secret token, destination and report interval. Blank token keeps an existing valid token. Add the bot to a channel with permission to post; use its numeric channel ID or public @username. A separate authenticated Test delivery button sends a clearly labelled test and reports API acceptance. This is not proof of the recipient reading it. Token values are never returned or exported.

Limits: bounded LAN-confirmed native operation, IPv4 acceptance only, two adjacent already-connected catch-all rules. Multi-server/channel hierarchy, inactive-profile activation and unattended production acceptance remain pending. Physical power loss is not covered by mocked process-crash tests.
