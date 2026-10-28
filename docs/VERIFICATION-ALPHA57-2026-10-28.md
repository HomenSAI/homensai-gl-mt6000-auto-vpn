<!-- doc-role: versioned-evidence -->
# Alpha57 installed and published / Alpha57 установлена и опубликована

Dedicated GL-MT3000, GL.iNet 4.11.0, 28 October 2026. Package **0.9.1-alpha57-1**, dashboard132/ui98/help132, **972857 bytes**, SHA256 `49a322109064bda030b6234fae589f307b5ba792ee2580d831795dbd3b82692f`. Code `9bb8ac709f9ec6cabc33a66fcb159a71bc55b186`, record `9c33183b10eb79ad45e50588d71f7ad98113284e`; identical-tree GitHub snapshot `2e738353804c1aae3c70bda34b06ee472414a1ce`.

[GitHub prerelease](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha57) and GitHub main were published; the downloaded IPK and checksum matched, and Gitea save plus explicit feature-branch push passed. Stable Latest remains v0.9.0, as selected by the owner. Historical packages/modules and failed intermediate evidence remain preserved. An earlier [emergency checkpoint](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/59ba093369e5f55baf6e698a68b82869b2c0ebc2/docs/handoff/EMERGENCY-SOL61-STATUS-2026-10-28.ru.md) records the state before final publication.

Both immutable CI runtimes passed **1122 application tests, zero skips**, 150 QA tests with 2/37 explicit skips, 60 offline lab cases and 13 executed Lua tests. Full 3.11 additionally passed 20 tools tests, **81 UI suites** and two Node lab suites. The isolated Python 3.9 build matched. Strict direct-child verification accepted only the five record files; a second record-only CI was not run. Local privacy inspected all 1463 public source files. Twelve real Lua/Linux reorder/CAS/Stop/budget cases and three safe-diagnostic cases are included.

Two first local full-run failures were fixtures: a test expected writes for an already-correct order, and a diagnostic test left global proof scope changed for a later legacy-history case. Corrected fixtures passed targeted checks and both full single-process runs; failed logs remain. No production guard was removed to make them pass. A record-preparation invocation before the separate builder finished was refused by its missing-proof gate before any record file changed; preparation succeeded only after isolated equality passed.

Installation verified **99 payload files**, actual HTTP resources and fresh RPC. Protected settings, accepted terms, interfaces and main routes were preserved. Normal Start passed in **38.1 seconds** after transient vendor settling. Encrypted before/after backups passed independent decrypt and complete archive reads, with no persisted plaintext; files and keys remain local/private.

Actual normal manual API acceptance passed with matching completed request IDs and fresh FW3 kernel marking:

| Action | Result | Observed seconds | Preserved evidence |
|---|---|---:|---|
| Same selected reserve | PASS | 14.8 | Identical policy, journal transaction and budget; hold target |
| Reserve → configured primary | PASS | 74.9 | Kernel source, protected config and policy fields unchanged |
| Same selected primary | PASS | 13.8 | No route write or budget debit |
| Primary → configured reserve | PASS | 94.9 | Kernel target, protected config and policy fields unchanged |
| Same primary before Resume | PASS | 13.4 | No route write/debit; establishes an actual hold for the Resume check |
| Resume | PASS | 6.4 | Hold cleared; Auto ON/RUNNING, kernel source; budget unchanged |

The first Resume observation returned WAIT_CONTROL because no manual hold remained; it was not counted as PASS. The later explicit same-channel hold followed by one accepted Resume passed. Final observation confirmed **alpha57, Auto ON/RUNNING, native OBSERVING, no manual hold, fresh kernel-confirmed primary and both VPNs healthy**. One target DNS failure after the reserve test is retained; intermittent provider/check failures are not erased by successful acceptance. No quota or cooldown setting was reset. Kernel proof covers new IPv4 catch-all LAN marking without an existing VPN connmark; it is not independent client or existing-connection migration proof.

The correction skips redundant UCI work: correct order needs no write/commit, and an adjacent swap needs one move and commit instead of six moves and commit. Fresh order/hash CAS, Stop and kernel fences remain before each actual write, with post-move/pre-commit/final checks. Worker/transaction bounds remain **50/90 seconds**. Safe parent stage/type/basename/line and child RTP dispatch/return metadata omit argv, stderr and exception text. In the successful primary run, saved `done - journal.started` was 46.826 seconds, including arming/release overhead; it is not an exact `process.wait` duration. Successful completion proves the unchanged worker cap did not expire. The original alpha56 timeout type was not recorded, so its precise cause remains a supported timing hypothesis rather than a claimed captured exception.

Actual complete **3/3 Google/Cloudflare/Wikipedia** measurements passed through both VPNs and were independently recomputed. One acceptance snapshot was primary 335.4 ms / reserve 2168.0 ms; the final state snapshot was 301.1 / 2192.0 ms. Values vary with measurement time. The [shared formula](WEBSITE-RESPONSE.md) times DNS/TCP/TLS/HTTP headers, never reads personal browsing and does not claim full page rendering. Older HTTPS/DoH and ICMP history remains separate. Large OpenVPN response was confirmed by the separate alpha55 phase diagnostic; no failure is converted to zero.

Actual isolated Edge/CDP acceptance passed **27 cases in each of C, B and intentional lazy-load-failure/Retry runs**: Help/Training/catalogue/deep links, every menu hover/hit region and top/reclick behavior, full-width disclosures, current footer, visible manual actions, configured Channel/Status table order, valid incoming three-site means, and card layout at 1920/1280/390 widths. Every temporary 15-minute root ubus session was destroyed; own contexts/browsers exited. Test profiles were intentionally retained as private evidence, not counted as successful deletion. Browser acceptance used read-only sessions; real route commands were separately exercised through the ordinary manual API.

Five actual status-driven draw samples per page, same appearance, versus installed alpha51:

| Page | Before median, ms | After median, ms | Change |
|---|---:|---:|---:|
| Overview | 189.1 | 48.9 | -74.14% |
| Channels | 112.0 | 44.0 | -60.71% |
| Events | 139.5 | 180.9 | **+29.68%** |
| Help | 144.1 | 39.3 | -72.73% |

The Events page is slower; do not claim every page improved. All recorded draws remain below 0.2 seconds in this sample. These are draw times, not complete RPC/network latency or a controlled causal benchmark with identical historical data. The before-run's known Events-menu functional failure remains a failure; only its valid timing observations form the baseline. Main module is **872094 LF bytes versus alpha51 1248776, 30.16% smaller**. Visible-only factories, fresh stale-page navigation, focus/scroll/timers/Back and all existing UI suites passed.

---

Alpha57 установлена и опубликована. Проверены 99 файлов, HTTP/RPC, настройки и условия, копии до и после. Auto включён и работает; финальная проверка подтвердила основной канал, отсутствие ручного удержания и здоровье обоих VPN. Ручные переходы прошли в обе стороны, same-channel не писал правила/не списывал попытку, Resume прошёл после настоящего удержания.

CI обеих сред PASS: 1122 теста приложения без пропусков, 150 QA с 2/37 явными пропусками, 81 UI-набор в полной среде, tools/lab/Lua. Отдельная сборка совпала. Скачанные пакет и checksum проверены, main и Gitea сохранены. Alpha52–56 не выдавались за принятые GitHub-релизы; их отказы сохранены.

Реальные ответы трёх сайтов и единая формула проверены. Три браузерных прохода по 27 случаев и замеры четырёх страниц прошли. Обзор, Каналы и Справка стали быстрее в этом измерении; События медленнее: 180,9 мс против 139,5. Главный модуль меньше на 30,16%. Пределы времени и проверки безопасности не ослаблены.

Independent external LAN-client, existing connections, full-day, controlled physical-fault, power-cut, IPv6 and MT6000 continuous-mode acceptance remain separate. Task 7 component profiling is optional and is not claimed complete here.
