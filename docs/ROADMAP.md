<!-- doc-role: current -->
# Current roadmap / Текущие открытые задачи

[Фактическая версия и доказательства](CURRENT-STATUS.md) · [Последние изменения](LATEST-CHANGES.md)

## Implemented baseline

The prepared MT3000 two-client controller, guarded manual selection, router IPv4 evidence, grouped live/saved logs, event-time roles/latency, M/R diagrams, five-row server disclosures,20-row event history, configurable retention and interactive EN/RU training have versioned source/tests and stated acceptance. Current delivery must still be read from CURRENT-STATUS, not inferred from this list.

The comprehensive documentation/helper audit is tracked in the current handoff. Historical TODO files are dated plans, not a second live backlog or fresh permission.

## Still separate / Отдельные области приёмки

1. Native physical-browser visual acceptance, independent real-client LAN/DNS/exit and IPv6/KillSwitch failure acceptance.
2. Real supported-device controlled faults in both directions, broad provider/firmware combinations and full-day client soak.
3. Interrupted package/power/FS scenarios and all missing-dependency combinations, with actual recovery evidence rather than model-only proof.
4. MT6000 continuous-mode qualification and matching-SDK provenance/build boundaries.
5. Autonomous prompt execution by named external ChatGPT/Claude models; command recipes and simulations are different evidence.
6. Restricted server-triggered Gitea CI activation; current local exact-SHA CI does not create a trusted server runner or required PR check automatically.

## Lua line (2.0.0-alpha24) open work / Открытые задачи линии Lua

From [TODO-PERF](handoff/TODO-PERF-2026-11-01.ru.md), [MASTER-PLAN](architecture/MASTER-PLAN-2026-10-31.ru.md) and [VENDOR-SETTLING](architecture/VENDOR-SETTLING-2026-11-01.ru.md). Dated plans, not fresh permission.

1. Measure the two alpha24 timing changes on the MT3000: the 3 s HTTPS wait in a dense confirmation and the vendor settle period of at most 45 s (variant B). Measured so far with fast detection on: decision 26-28 s (alpha23).
2. 24-hour soak of the chosen variant with the fault matrix (master plan step 11 and report step 12), and a physical power cut. Only 3-hour soaks and instant-reboot simulations exist.
3. C reads and writes the history journal in the same format as Python and Lua (TODO-PERF 3.2); C core branch checks against the soak facts (master plan steps 14-15).
4. Diagnostic cache: C repeat, event-driven route/rule cache (4.2), `/proc` walk only before a kernel write (4.3), tests and router measurement (4.5).
5. Vendor wait after a tunnel rebuild: the third variant (В in the Russian report: do not stop healthy tunnels in recovery after an Auto kill) and a measurement of how long the firmware really needs. Source 03.11.2026 (not yet on the router): an Auto kill in the middle of an automatic switch to the reserve now finishes the switch and hands the kept tunnels to the restart Start ([BOOT-RECOVERY, 03.11](architecture/BOOT-RECOVERY-2026-11-01.ru.md)); a kill while idle still rebuilds.
6. Measurements missing for the Python fallback layer and for pure Lua: fast detection, power cut, `LUA-AUTO-FALLBACK` hand-over time ([MEASUREMENTS, section 8](MEASUREMENTS.en.md#8-runtime-pyramid-and-switch-times)).
7. The built-in Help topic "Program core" (source `router/core_help.inc.js`, shown in the application only) still calls the C layer a plan, does not mention the C JSON module `canon_c.so`, and says the single-process `hv-core` was tested on a PC and not yet on the router. It needs the next package build.

8. Offline evolution study 03.11.2026 ([design note](architecture/RESCUE-STABLE-2026-11-03.ru.md)): `rescue_stable`, `primary_stable` 120 s and two lost heartbeats are in the source; router acceptance (reserve-drop-carrying, phase-3 flap, phase-2 matrix) and the tunnel autostart restore after Stop are not yet measured. Future option, not enabled: `DENSE_INTERVAL` 6 s (model: unnecessary switches −90 %, each real outage ≥ 30 s 1.5–2.5 s longer) - owner decision after phase-2 measurements.
9. Integration 2.1.0-alpha8 (03.11.2026, `integ/alpha8-20261103`): one return rule for rescue_stable and the HMM detector ([rescue](architecture/RESCUE-STABLE-2026-11-03.ru.md), [HMM](architecture/HMM-DETECTOR-2026-11-03.ru.md)), HMM return threshold 0.90, the stock vpn-client start link restored after the owner's Stop, the approved UI with the new expert settings. Open: router acceptance of all of it; the simulated extra switch on a noisy day with two-loss heartbeat + HMM (1 standard / 2 fast per day) to be measured on the MT3000 (phase 2, 24 h); a tick-level test of the pair-tick return path (kernel on the reserve without a COMMITTED journal) — only the shared return_rule is tested there; `fix/formal-k2-k5-20261103` still to be merged last.

Задачи линии Lua: замерить на MT3000 ожидание HTTPS 3 с и срок успокоения прошивки до 45 с (alpha24); суточный прогон и физическое отключение питания; C читает и пишет журнал истории; кэш диагностики (пп. 4.2, 4.3, 4.5); вариант В для ожидания прошивки (не останавливать здоровые туннели при восстановлении после kill Auto); недостающие замеры для Python и чистого Lua; обновить тему справки «Ядро программы» (она ещё называет уровень C планом и не упоминает модуль `canon_c.so`) со следующей сборкой пакета.

Completed old alpha9/alpha10/alpha11/alpha12/alpha13 results remain in their dated reports. Never restart their old observers solely to continue reading documentation.
