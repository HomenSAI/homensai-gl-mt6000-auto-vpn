# PAUSED — 2026-10-16T17:26:04.3633100+02:00

User requested a checkpoint and stop. Both QEMU guests were verified paused/running=false. No test was resumed. No physical-router changes, deployment, new release or GitHub write occurred in this work window.

## Verified code and artifacts

Branch: feature/local-completion-alpha6. Previous checkpoint: 740fe24. Last passing immutable application CI source: 15ab3814428f10b6c6176af39521950b5ee75905 (294 application, 9 QA, 9 UI checks; Python 3.9/Lua and control runtime). Alpha7-1 package: 452207 bytes; SHA256 a96aa7f785a78457fec48fadbcfda0c8e40074d72da787846e1b1f8f09e1cea4. Installed only in the isolated copy. Latest checkpoint commit is discoverable with git log -1 after this file is saved.

## Completed within scope

Offline cascade/proof/lease/recovery contracts; bounded inactive-profile mock scheduler; migrations; sidebar UI, EN/RU responsive matrix, timeline/aggregates/CSV; source-bound client-helper self-tests; immutable local CI/privacy/reproducible packaging. Actual isolated OpenWrt upgrade/rollback acceptance: 13 checks; UCI write-failure/procd acceptance: 11 checks. Signed protocol dependencies installed in the clone. Warm reboot passed on alpha5 direct-kernel baseline; alpha7 warm reboot remains unverified.

## Reopened blocker

Actual libuci reproducer showed unrelated pending delta interval=99 committed by setup_complete save while reporting OK. Root cause: shared saved UCI deltas are included in commit. Fix drafts are preserved in pending-uci-fix, outside package inputs. They have NOT passed tests or been installed. NEXT-11 and NEXT-15 are reopened for this finding; NEXT-24 is partial.

## Remaining

Validate pending-delta refusal and preservation; adapt Lua mocks, check all callers and lifecycle guard; full CI and new reproducible package; alpha7 reboot/interruption acceptance. NEXT-22/23 real OpenVPN/WireGuard network cascade, DNS/firewall/IPv6/conntrack matrix not run. NEXT-10 matching SDK and NEXT-13 restricted automatic Gitea runner remain blocked. Native full hierarchy remains mock-contract scope, not accepted GL.iNet integration.

## Safe next hardware step

After the user's next instruction, connect for read-only firmware/profile/service inventory, baseline and recovery planning. Do not deploy this unfinished candidate or inject live failures before closing the UCI blocker and repeating CI/package checks. Physical GL.iNet worker arbitration, LAN-bound path, DNS/Kill Switch, IPv6, offload and rollback require separate device acceptance. Existing physical-router state has not been freshly inspected in this pause checkpoint.

All recent reports are in qa/alpha7-*.json. No simulation is a claim of real-router uptime or failover. The original guest/disk and private backups are preserved. Idle loopback preview/asset HTTP servers are not acceptance tests; no network-test loop is running.
