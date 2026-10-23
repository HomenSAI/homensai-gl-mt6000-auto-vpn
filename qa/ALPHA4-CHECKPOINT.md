<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../docs/CURRENT-STATUS.md) · [documentation index](../docs/DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Alpha4 development checkpoint — 2026-10-16

This snapshot adds reviewed priority application, supported recovery/monitoring wizards and a bounded operator traffic-fault tool. Physical GL-MT6000 access and deployment remain deferred.

## Changes and verified scope

- `priority_preview` gives an explicit ordered review; `priority_apply` rejects stale metadata and active/uncertain native recovery. Only own UCI metadata changes; no route/service commands.
- Recovery settings control consecutive failure/success counts, cooldown/dwell, stable primary-return observations and hold-reserve policy. Changing settings invalidates matching certification. Native policy layout validation now permits 2–16 contiguous unrestricted rules; automatic hierarchy beyond the configured pair is still unfinished.
- Operator fault requires an already certified observing Auto trial, current primary, a fresh healthy reserve and enough remaining window. It drops IPv4 traffic using only an owned nft table; VPN processes, INPUT, management paths and Kill Switch are not edited. Kernel set timeout bounds the drop independently of the watchdog. Stop Auto requests cancellation.
- Fault history is separately checksummed and bounded to 100 records; nonce/devices are not public status fields. A dedicated Operator tests page provides review, timed start and cancellation.
- Replaced the raw-UCI settings form with own RPC wizards. Application ACL no longer grants direct UCI read/write. This avoids legacy form writes bypassing recovery guards and avoids loading stored tokens into our page.
- Inventory RPC is validated, retried at most three read-only attempts and reported as unknown on failure. Numeric ubus errors cannot be mistaken for empty/default configuration. Requests use LuCI's explicit rejection behavior. Stale transition state keeps Stop available.

## Checks

- 194 Python tests PASS in Debian; all five Node suites PASS (inventory/recovery/setup/traffic/Auto).
- Actual nftables 0.9.6 / Linux 5.4.238 in the x86 OpenWrt VM: loopback traffic blocked, restored by kernel set timeout with no watchdog, owned table removed and firewall UCI unchanged. This is a kernel fault-rule check, not VPN failover.
- First nft preflight failed because `devices` is a reserved identifier. Changed set/chain names and declaration layout; the repeated kernel check passed in 9.2 guest-clock seconds. Original failure is retained in the work log.
- Actual virtual LuCI opened alpha4 and the recovery wizard saved default values through RPC. Own UCI values were independently read back. During reload an inventory request failed and the old UI displayed empty defaults despite preserved configuration; the final snapshot includes the explicit retry/unknown-state fix. That final UI revision still needs repeated real-LuCI browser acceptance.
- Final IPK 425313 bytes, SHA256 `e8a285924cccd69374422d6fdce7ea9f41bf343842ee10a4a2985c9096ee16c7`.

## Still open

Full hierarchy execution/cascaded rollback, inactive-profile activation, true vendor-writer coordination, native executor-crash tests, IPv6, real-device reboot/power loss and Telegram delivery acknowledgement. Generic VM correctly refuses GL.iNet native operation; do not remove its platform guards to obtain a passing test. Previous VM warm-reboot failures remain unresolved.
