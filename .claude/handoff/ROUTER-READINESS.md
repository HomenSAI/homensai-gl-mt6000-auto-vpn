# Independent physical-test readiness decision

This checkpoint does not certify production or authorize deployment. Answer separately for each stage:

| Stage | Decision required |
| --- | --- |
| Read-only device preparation | Can the owner authorize inventory/backup without changing routing? |
| Monitor-only installation | Are exact platform/dependencies, package integrity, storage, backup and recovery validated? |
| Bounded switching/rollback trial | Are every guard, vendor procedure, LAN witness, deadline and recovery condition satisfied? |
| Unattended operation | Is there sufficient actual-device evidence for the supported scenario? Virtual evidence alone is insufficient. |

## Mandatory review gates before proposing a switching trial

1. Identify exact GL-MT6000/Flint 2 model, firmware/OpenWrt/kernel, LuCI components and dependencies from a newly authorized read-only device inventory. Dated snapshots are context only.
2. Verify selected package/revision/hash, compatibility and free writable storage. A generic x86 VM or interpreted package build is not proof of matched vendor SDK/platform behavior.
3. Make a recoverable private configuration/state backup; verify how the owner can restore it. Never place secrets in the review, Git or public artifacts.
4. Preserve an independently checked management path and recovery access; separate client cable tests from Windows Wi-Fi-preferred traffic. Current Windows network/NordVPN and router SSH state are unknown here.
5. Verify current VPN policy/profiles, source and reserves, active interfaces, priorities and unsupported special rules. Existing keys remain managed by the router.
6. Verify the native adapter's exact vendor-file hashes, locks/worker arbitration and supported board/firmware. A model adapter's success does not prove vendor workers.
7. Prove original and reserve LAN DNS/HTTPS/exit behavior using transaction-bound client evidence; router probes alone are insufficient.
8. Preserve Kill Switch/privacy policy; no silent direct-WAN fallback or IPv6 bypass. State unsupported IPv6 explicitly.
9. Establish bounded deadline, operator Stop, recovery/rollback certificate and behavior if primary remains unhealthy or foreign configuration changes.
10. Verify actual acceleration state and supported handling. Do not infer safe disabling from settings alone or unload drivers/modules blindly.
11. Obtain a fresh user-approved interruption window, session-reconnection acceptance and explicit authorization for the proposed device actions.
12. Define precise success, failure, abort, evidence collection and independent cleanup checks before starting. Never promote RUNNING/STOPPED/unknown evidence to PASS.

## Requested conclusion

Return one justified verdict for each stage: NOT READY / READY SUBJECT TO LISTED PRECONDITIONS / READY FOR THE SPECIFIC AUTHORIZED TEST. List P0 blockers, safe next actions and required owner inputs. Explain which optional backlog items do not block a controlled trial.

Full unattended native server/channel/protocol cascade, inactive-provider startup, real LAN IPv6/Kill Switch behavior and physical power/flash reliability remain unverified in this checkpoint. Do not require all optional UI features before recommending a carefully bounded validation, and do not use an unfinished soak as a completed reliability certificate.
