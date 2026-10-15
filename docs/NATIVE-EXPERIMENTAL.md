# Experimental native controller

2026-10-15. Candidate: **0.4.0-alpha8**. Installed device: **0.4.0-alpha7**, monitor mode, native controller **DISABLED**. Candidate alpha8 has not been installed while the owner works remotely. Production automatic failover is not validated.

## Implemented subset

A separate procd process supervises a deadline-limited change in the order of exactly two adjacent, unrestricted, already connected GL.iNet VPN rules. Special rules must precede them; all active VPN rules must have Kill Switch enabled and direct-WAN fallback must be disabled. It never edits keys, creates profiles or intentionally stops VPN interfaces. It invokes the vendor rtp2.sh procedure, which can rebuild DNS/firewall state, clean conntrack and interrupt existing sessions. This is not a guarantee of uninterrupted service.

The controller pins four audited vendor-file hashes and GL-MT6000/4.11.0, checks IPv6 disabled, rejects unverified acceleration and busy vendor locks, uses a private checksummed durable journal and a separate supervisor. A private nftables FORWARD guard blocks forwarded LAN traffic during changes, then allows only existing VPN output devices and blocks forwarded IPv6 while awaiting client confirmation. It does not install an INPUT rule. The guard and vendor apply have not yet been tested together on the real router. Concurrent vendor writers remain an experimental risk: before/after fingerprints detect changes but are not a complete shared-lock protocol.

A trial must prove that the LAN client's baseline exit IP equals the chosen source, that the reserve exit differs, and that after the change the client can resolve DNS and use HTTPS through the expected reserve exit. Router-originated probes alone do not satisfy this. No client confirmation within 90 seconds means rollback. A successful trial restores the original order and issues a certificate bound to this policy, pair, order direction and time window. Only then can three fresh source failures plus two fresh reserve successes trigger an automatic attempt. Every attempt still requires external client confirmation. There is no automatic failback or inactive-profile startup. Each window is limited to four hours, three attempts and a 180-second cooldown. Trial tokens and attempts survive supervisor restart.

Rollback restores only an owned rule order, never a foreign configuration. Unknown/corrupt journal, changed policy or unverified rollback retain/block the guard. A supervisor restart recovers pending work; an expired/disabled experiment restores the original order. Whole-router power loss, flash failure and vendor worker races are not device-tested. Own procd service upgrades now restart only the project's service, allowing graceful checkpointing and controller recovery; no unconditional rpcd/network restart is added.

## Acceleration preparation

Preparation requires a separate explicit authenticated own-config request; package installation does not disable acceleration by default. Original nonsecret acceleration parameters are kept privately on the device. The implementation uses vendor settings/services, verifies runtime state and permits normal rmmod only for accelerator modules. It never uses forced unload, removes packages, or unloads Ethernet/Wi-Fi drivers. The kernel refuses removal of modules in use. Preparation stops after three failed attempts.

Actual device observations: mtkhnat enable was already 0; shortcut_fe was loaded and was successfully unloaded during the authorised preparation. The mtkhnat module remains loaded; its debugfs hook file returns an empty body and normal unloading did not succeed. Hardware disable is therefore **not verified**. Alpha8 adds bounded diagnosis of fresh kernel-ring responses; old logs and messages announcing an intended change are not accepted as proof. This fallback is unit-tested, not device-verified.

[GL.iNet documents](https://docs.gl-inet.com/router/en/4/interface_guide/network_acceleration/) acceleration's effect on client traffic/speed statistics. The related [MediaTek-derived 5.4 driver source](https://github.com/hanwckf/immortalwrt-mt798x/blob/ba554197ed7e252fd3c1ee023621e1d1d009d323/target/linux/mediatek/files-5.4/drivers/net/ethernet/mediatek/mtk_hnat/hnat.c) explains hook/cache disable, but does not prove this device's exact driver behaviour. No competitor/driver code was copied.

## Current safe state and remaining work

The owner subsequently prioritised a live remote work connection. Native mode was explicitly saved disabled and the preparation request removed through LuCI's normal uci.apply/confirm workflow. Direct uci.commit was denied by this device API; set alone did not persist settings. No VPN rule order or route was changed by the new controller. Three active profiles continued to pass router-originated HTTPS/DNS checks. No real automatic switch, native guard exercise or native rollback is claimed.

The execution computer's selected internet next hop is not this router. Its own internet requests cannot certify the router's LAN VPN path. A separate verified LAN client and an agreed interruption window are still required. Do not enable the experimental fields by guessing their values, bypass prerequisites, forge a client confirmation or force module removal. Public installation/AI prompts remain MONITOR-only. The interface displays controller state/blocking codes; an end-user native trial wizard is not supplied in this candidate.

Read-only observations run every 30 seconds until 14:00 Europe/Berlin; thread follow-ups inspect them every five minutes. These observations do not automatically repair internet connectivity and cannot guarantee remote access if the control path fails. No further outage-producing tests are authorised while the owner's remote session has priority.

## Evidence

52 monitor/package/controller unit tests and 9 lab transaction tests pass. The 200-case transaction contract remains a model; it is not 200 native GL.iNet driver tests. At the 11:40 Berlin intermediate checkpoint, the separate baseline soak had 21 completed cycles / 105 suite runs: 2,100 distinct new seeded scenarios, 945,000 model steps, 37,687,012 assertions, zero model failures; 420 real child-process crash cases passed. These are container processes, not router power cuts. The baseline soak uses commit 386b4b3, not the new native controller. It continues until 14:00; the above is not the final report.

## Historical scope

This candidate report describes the earlier stage. Later verified device results and current limits are recorded in WORKLOG.md and STATE.md.
