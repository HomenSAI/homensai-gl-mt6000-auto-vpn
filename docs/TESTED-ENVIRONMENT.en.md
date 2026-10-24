# Tested environment and limits

Current full guide: [CURRENT-STATE.en.md](CURRENT-STATE.en.md).

## Installation and evidence

For public stable installation use [the guide](INSTALL.en.md), pinned v0.9.0 tag and matching IPK/checksum/verification/install kit. Do not downgrade a newer installation. For a candidate use `releases/`, VERSION.json and checksum from the same exact branch commit; the stable kit is not the candidate kit. Verify model/firmware, private backup and readiness; do not bypass refusals or flash firmware to install this app.

[Alpha10 VM audit](handoff/VM-AUDIT-2026-10-24.md): two in-OpenWrt builds matched the package; install/update/rollback/restart/reboot passed;86files/modes matched.76prompts were inventoried with explicit command-recipe coverage. This is not named external-model execution or exhaustive fault combinations. Real GL/LAN, native browser visual acceptance and several fault scenarios remain untested. [Matrix](../qa/OWNER-PROMPT-VM-ALPHA10-2026-10-24.json).

Dated reports and old release notes retain their historical evidence. The [index](DOCUMENTATION-INDEX.md) distinguishes current instructions from history. Never publish keys, passwords, VPN files or unredacted backups in chat/Git.
