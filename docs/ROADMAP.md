# Remaining work / Оставшиеся работы

Current version and completed behavior: [CURRENT-STATUS](CURRENT-STATUS.md). The working two-channel controller, manual override, UI changes, setup/help and persistent statistics are implemented; they must not remain described as merely planned.

Open acceptance/product work:

1. Independent LAN-client DNS/HTTPS/traffic-path verification for the current continuous mode.
2. A completed24-hour traffic soak, clearly separating real provider failures, planned simulations and unobserved gaps.
3. Physical power-loss/recovery tests and a separately designed explicit boot-auto-resume policy; current Auto stays off after restart.
4. Current continuous-mode hardware acceptance on MT6000 and any other firmware/model. Do not infer it from a model selector or Architecture:all.
5. IPv6 policy/failover acceptance, broader multireserve hierarchy, captive/interception scenarios and the remaining protocol/stress lab scope.
6. Diagnosis of intermittent OpenVPN AUTH_FAILED startup rejections without hiding them, changing unrelated credentials or bypassing readiness/attempt budgets.

Exact vendor-SDK and hosted/server-CI work remain separate from successful interpreted-IPK/local-container checks. Historical numbered proposals remain available in archived task documents; they are not a new authorization to deploy, run faults or change the primary network.
