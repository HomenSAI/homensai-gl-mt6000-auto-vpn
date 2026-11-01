# Switching speed measured on the GL-MT3000

**License:** [HomenSAI Personal & Commercial Source License v1.0](../LICENSE) — source-available, not open source. Earlier versions released under MIT keep their MIT grant ([LICENSE-MIT-LEGACY](../LICENSE-MIT-LEGACY), [details](../LICENSING.md)).

All numbers come from the dedicated GL-MT3000 (OpenWrt 21.02 / GL firmware 4.11). The primary channel is WireGuard and the reserve is OpenVPN. Measured on 30 Oct 2026.

The faults were controlled: the Tests page function blocks the primary's traffic for a fixed time. Times are seconds from the fault start or from the click. Russian version: [MEASUREMENTS.ru.md](MEASUREMENTS.ru.md).

Key numbers:
- Auto: time to traffic on the reserve went from 153 s to 129–136 s.
- The automatic switch itself went from 60 s to 39–44 s.
- The return to the primary is about twice as fast: 50 s to 24–25 s.
- The manual button went from 42 s to 16.6 s (beta8) and then to 9.9 s (beta9) until done, with traffic moved after 8.2 s.

These key numbers and sections 1–5 describe the Python line of 30 Oct 2026 and stay as a record. The current 2.0.0-alpha24 line (Lua services, C JSON module, fast detection) is in [section 7](#7-lua-line-after-alpha6-200-alpha13-to-alpha24-31-oct-to-1-nov-2026) and [section 8, runtime pyramid and switch times](#8-runtime-pyramid-and-switch-times): manual switch done about 0.7 s, automatic decision 26–28 s after an outage.

## 1. Speed by version

### Auto: fault start to traffic on the reserve

Probe level 3 with boost, 150 s faults. The values are means.

![Auto by version](measurements/auto-by-version.svg)

| Version | How | Runs | Not yet noticed | Confirming | Switch itself | Total to reserve | Return |
|---|---|---|---|---|---|---|---|
| 0.9.1-alpha82 | GL rebuild (rtp2) | 4 | 29.5 s | 63.3 s | 60.5 s | **153.3 s** | 50 s |
| 1.0.0-beta5 | fast switch | 3 of 4 | 28 s | 57 s | 44 s | **129 s** | 23.7 s |
| 1.0.0-beta7 | fast switch | 3 | 28.3 s | 68.3 s | 39.3 s | **136 s** | 25.3 s |

What this shows:
- The fast switch cut the switch itself by about a third and halved the return.
- Most of the time is now detection and confirmation of the failure: about 85–97 s. That time is set by the probe level and the number of required failed checks.
- In beta5, one run in four rolled back because the GL worker was busy (VENDOR-WORKER-BUSY). Beta7 fixes this: the router waits up to 20 s for the GL worker.

### Manual button with Auto on: click to done

![Manual button by version](measurements/manual-by-version.svg)

| Version | How | Runs | Button request | Waiting for Auto | Checks before | Route change | Checks after and confirmation | Saving and display | Total | Traffic moved at |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.0.0-beta7 | full guarded transaction | 1 | 4.6 s | 2.8 s | 12.1 s | 5.5 s | 15.7 s | 1.5 s | **42.2 s** | ~25 s |
| 1.0.0-beta8 | instant manual switch | 6 | 3.5 s | 1.7 s | 5.3 s | 0.3 s | 3.7 s | 2.1 s | **16.6 s** (14.5–20.2) | 10.8 s (10.1–12.6) |
| 1.0.0-beta9 | click and history in memory | 6 | 3.3 s | 1.4 s | 2.3 s | 1.2 s | 0.7 s | 1.0 s | **9.9 s** (8.2–12.6) | 8.2 s (6.3–11.0) |
| 1.0.0-beta10 | light gate, faster parsing | 6 | 0.6 s | 0.9 s | 1.5 s | 1.1 s | 0.3 s | 0.9 s | **5.4 s** (4.2–6.6) | 4.2 s (3.2–5.3) |

Page buttons (router answer):

| Button | beta9 | beta10 |
|---|---|---|
| Start Auto | 1.06 s | 0.30 s |
| Cancel failure test | 1.04 s | 0.21 s |
| Manual click | 0.9–3.1 s | 0.5–0.8 s |

Beta9 stamps every stage itself:
- checks before the switch: full diagnostic 1.0 s, kernel proof 1.1 s;
- route change: writing the rule order 1.1 s, the atomic kernel switch 0.14–0.27 s.

## 2. Separate experiments

### GL rebuild (rtp2) window, 1.0.0-beta2, 5 cycles

- A switch took 53–60 s, of which the rtp2 rebuild itself took 20–33 s.
- One cycle rolled back with VENDOR-WORKER-BUSY.
- What rtp2 does:
  - swaps the two tunnel jumps in the mangle ROUTE_POLICY chain;
  - rewrites uci route_policy;
  - reloads the firewall (fw3);
  - restarts every dnsmasq, which interrupts DNS for about 2 s.

### Fast rule swap, 5 cycles

The rule was changed by one atomic `iptables-restore --noflush` of the ROUTE_POLICY chain, then old flows were dropped with `conntrack -D`.

- The rule change took 8–33 ms.
- A LAN test client saw the new country after 0.07–1.8 s.
- No request failed and DNS was never interrupted.

## 3. Cost of single steps on the router

Measured idle.

| Step | Time |
|---|---|
| Full pair diagnostic | 0.94–1.13 s |
| Kernel policy attestation | 0.52–0.60 s |
| Manual button controls | 0.62 s |
| Fresh channel probe (DNS + 2 HTTPS) | 0.63 s |
| Kernel fingerprint | 0.27 s |
| python3 start | 0.11 s |
| Application import | 0.71 s |
| Reading the rule order and settings | 0.02 s |
| `uci show` / `iptables-save` | 0.01 s |
| Event history read (1.27 MB, checksummed) | 0.42 s |
| Encoding the history as JSON | 0.19 s |
| Writing 1.27 MB to flash with fsync | 0.11 s |

### Finding: the event history

The history file was 1.27 MB, and every event rewrote it twice: the main file and a full backup copy. That came to about 2.5 MB written to flash and 1.5–2 s per event, with several events per switch.

In 1.0.0-beta9 the Auto service keeps the history in memory, and the backup is made by renaming the previous file instead of writing a second copy. The result is one write per event and half the flash wear.

## 4. What is kept in memory

| Service | Since | Effect |
|---|---|---|
| Page status (status.sock) | 1.0.0-beta7 | Status reply in 0.19 s instead of 0.26–3.1 s |
| Auto wakes up on a click | 1.0.0-beta8 | A click is taken without waiting for the next cycle |
| Manual button through the same service | 1.0.0-beta9 | No Python start per click (3.5 s in beta8). An empty request is answered in 0.15 s. |
| Event history in the Auto service | 1.0.0-beta9 | One flash write per event instead of two full copies, and no re-reading of the file |
| Start/Stop Auto, failure test, probe level and response method through the same service | 1.0.0-beta10 | No Python start per click |
| Light check of a manual click | 1.0.0-beta10 | No rebuild of the whole button model, which took 2.5–6 s under load in beta9 |
| Kernel rule parsing and state reading without repeated work | 1.0.0-beta10 | A profile on the router showed: of a 1.37 s diagnostic, 0.42 s went on checking JSON numbers; of a 0.77 s kernel proof, 0.55 s went on parsing the same rules again |

## 5. Memory used by the services

Total RAM is 480 MB. Measured on 30 Oct 2026.

| Service | beta9, long running | beta10, 6 min after start | Share of RAM |
|---|---|---|---|
| Monitor service (agent) | 45.3 MB | 48.1 MB | ~10% |
| Auto service (native_switch) | 40.0 MB | 41.4 MB | ~9% |
| Sum of the two figures | 85.3 MB | 89.5 MB | ~18% |

How to read these figures (from the router's /proc, beta10):

| Part of one service | Monitor | Auto |
|---|---|---|
| Python and libraries mapped from flash (RssFile) | 6.8 MB | 6.8 MB |
| The service's working memory (RssAnon) | 41.3 MB | 34.6 MB |
| Peak since start (VmHWM) | 52.1 MB | 45.7 MB |

- Python and its libraries (about 7 MB) are physically shared by both services but appear in each figure. The truly unique memory is about 83 MB, not 89.5 MB.
- Working memory is everything a service works with:
  - the observation file and the finished page replies (about 3 MB);
  - the Auto service's copy of the event history (about 8 MB);
  - journals, the latency history, kernel rules and probe data;
  - the Python objects and imported code themselves (about 9 MB per service).
- Python does not return freed memory to the system; it keeps it for reuse. So the figure stays near the working peak: parsing the status, the history and the kernel rules.

A separate measurement of a bare Python process on the router:
- bare Python: 6.5 MB;
- with the program code loaded: 16.3 MB;
- after reading the history: +7.9 MB;
- after the status and the finished reply: +3 MB.

These are parts, not the whole service. The rest is working data and Python's reserve, as described above.

Before the resident copies (beta6 and earlier), the services held about 11 MB less. Peak use while recording an event was the same, because the history was read in full then too.

Safeguard: from beta10, the history copy is kept in memory only while at least 64 MB of RAM is available.

Other resources:
- state files in RAM (/var/run/homensai-vpn): 0.6 MB;
- data on flash (/etc/homensai-vpn): 4.1 MB, of which the history takes 2 × 1.27 MB;
- the flash overlay partition is 18% used (24 of 139 MB).

## 6. Lua line: the Auto supervisor in Lua (2.0.0-alpha3/alpha4, 31 Oct 2026)

Same MT3000 and channels. Compared with Python 1.0.0-beta13. The Auto supervisor runs in Lua 5.1 (`option lua_auto '1'`); monitoring and the page stay in Python.

| | Python (beta13) | Lua (alpha3) |
|---|---|---|
| Idle Auto, CPU (240 s window) | 55.7 % of a core | **22.5 %** (alpha3) → **15.7 %** (alpha6: 12.4 % itself + 3.3 % child processes) |
| Auto, memory (RSS) | 40.6 MB | **12.1 MB** (alpha3) → **9.1 MB** (alpha6) |
| Manual button: traffic on the new channel | 4.1 s | **2.6 s** (1.9–3.6), 6 of 6 |
| Manual button: done | 5.5 s | **4.0 s** (3.3–4.9) |

Automatic faults (150 s fault of the primary, probe level unchanged), Lua alpha3:

| Fault | Detected | Switch started | Reserve confirmed | Back on the primary |
|---|---|---|---|---|
| 1 | 41 s | 76 s | 97 s | 216 s |
| 2 | 13 s | 44 s | 65 s | 211 s |

Resilience (alpha4): `kill -9` of the Lua process during APPLYING — procd restarted it after 5 s, the journal was rolled back 9.5 s after the kill (SUPERVISOR-RECOVERY), the pair cleanup finished and the LAN guard was removed. Auto is off afterwards — by design, as in Python (a restarted supervisor never resumes the intent). Stop during APPLYING (alpha6): the switch was rolled back after 5 s, the cleanup finished, Auto stopped, the LAN guard was removed, the Lua process was not restarted.

Where Lua's CPU went (alpha5 profiler, 60 s): ~40 % parsing the monitor's `status.json` (230 KB every 10.5 s, the exact Lua parser takes 360 ms, and it ran twice). alpha5 parses once per file version, alpha6 builds only the 7 fields the supervisor reads (170 ms). The rest: the GL process check in `/proc` (~9 %), JSON encoding and Python number format (~10 %), the kernel rule proof (~8 %). The next step is plan item 8 (monitor and Auto in one process, no file between them).

Monitor in Lua (items 2–3, alpha9, same conditions: level 1, a probe every 60 s): CPU 3.4 % of a core against 4.6 % for the Python monitor, memory 8 MB against ~37 MB, `status` answer 0.09 s against 0.14 s. Both services in Lua together: ~22 MB against ~78 MB for the two Python services. Until the buttons move to Lua (item 4) they go through `agent.py`, so a manual switch is slower: done after 6.0 s (4.0 s with the Python monitor).

Item 4, first step (alpha10–11, both services in Lua): the manual click request is answered by the Lua monitor in 0.04 s; traffic on the new channel after 2.7–2.9 s, done after 5.0–5.3 s (3+3). In the hold after a manual switch the Lua supervisor uses 15.6 % of a core (alpha10: 37.6 %, every re-check of the held channel started Python). Both services in Lua together at idle: about 19 % of a core and ~20 MB against ~60 % and ~78 MB for the two Python services.

What the first router runs found (and the PC tests with a fake system layer could not): quotes in the LAN guard release job, nixio argument forms (modes as strings, open flags), no `stat` command, the stdin of the in-process network write script. All fixed; a router self-test of the system layer (17 checks) now runs before Lua is enabled.

## 7. Lua line after alpha6 (2.0.0-alpha13 to alpha24, 31 Oct to 1 Nov 2026)

Same MT3000 and channels. The sources are the release notes of 2.0.0-alpha17 to alpha24 and the dated reports in `docs/architecture/` ([SOAK-LUA-VS-C](architecture/SOAK-LUA-VS-C-2026-11-01.ru.md), [SWITCH-SPEED](architecture/SWITCH-SPEED-2026-11-01.ru.md), [VENDOR-SETTLING](architecture/VENDOR-SETTLING-2026-11-01.ru.md), [HISTORY-JOURNAL](architecture/HISTORY-JOURNAL-2026-11-01.ru.md); these reports are in Russian). A manual switch to the reserve and back, a `status` call every 1 s.

Manual switch, two Lua services:

| Version | What changed | Traffic moved | Switch done | Longest `status` during switches |
|---|---|---|---|---|
| alpha16 | baseline | 3.7 s | 7.2–7.4 s | 8 of 49 answers over 1 s |
| alpha19 | history encoded once per event | 1.4–1.6 s | 2.5–2.9 s | 2.0–2.2 s (6 of 40 over 1 s) |
| alpha20 | history projection built by a child process | 1.4–1.7 s | 2.6–3.4 s | 0.42–0.50 s |
| alpha21, pure Lua | history journal, diagnostic cache | 0.6–0.8 s | 1.05–1.3 s | 0.15 s |
| alpha21, with C (`canon_c.so`) | C module for the canonical JSON | 0.5 s | 0.7 s | 0.09 s |
| alpha22, two services (default) | same | 0.49–0.59 s | 0.71–0.81 s | 0.12–0.14 s |
| alpha22, one process `hv-core` | optional | 0.48–0.61 s | 0.81–0.94 s | 0.13–0.26 s |

Auto CPU: 14–15 % (alpha20), 10.1 % (alpha21 pure Lua), 7.8 % (alpha21 with C). Memory of both services: about 36 MB (alpha20), about 18 MB (alpha21). `hv-core` saves about 5 MB more (about 15.5 MB against about 20.5 MB, alpha22).

Automatic switch after a fault (primary WireGuard cut for 150 s, probe level 1, MT3000, alpha23, times from the start of the fault):

| | Dense checks start | Auto decision (APPLYING) | Traffic on the reserve | Confirmed (COMMITTED) |
|---|---|---|---|---|
| Fast detection off, boost already running | none | 29.5 s | 31.0 s | 36.3 s |
| Fast detection on, boost running | 2.6 s | 25.8 s | 27.4 s | 32.1 s |
| Fast detection on, from cold | 3.1 s | 28.2 s | 29.5 s | 35.2 s |
| For comparison: 3-hour soaks, from cold, without fast detection | none | 58–88 s | not measured | not measured |

- From the decision to the traffic leaving takes 1.3–1.6 s (checks and kernel confirmation about 0.5 s, UCI about 0.5 s, iptables about 0.5 s). The 3–5 s up to COMMITTED come after the traffic has moved (the reserve is checked through the new path).
- The remaining 23 s or so are three failed full checks in a row (the `failures` rule, default 3). Each check of a cut channel waits for the DNS and HTTPS timeouts.
- Since alpha24 fast detection is on by default, the monitor's HTTPS wait during a dense confirmation is 3 s instead of 6 s, and the vendor settle period is at most 45 s. These two alpha24 changes have **not been measured on the router yet**; the table above is alpha23.

Automatic switch inside the 3-hour soaks (a fault every 3 minutes, APPLYING to COMMITTED): Lua alpha20 5.0–8.0 s (median 6.05 s); with C, alpha21 4.4–7.8 s (median 4.6 s). Outside the external provider outage of that run, alpha21 with C finished 33 of 33 cycles in normal operation (alpha20 on Lua: 39 of 46).

Power cut (instant reboot `sysrq-b`, not a physical plug pull):
- alpha22, a manual switch interrupted while the journal was APPLYING: 2 of 2 recovered by themselves. The journal ended ROLLED-BACK (SUPERVISOR-RECOVERY), Start was not needed, Auto was OBSERVING on the primary 255 s after the boot, the LAN had internet and the "VPN only" guard was in place.
- In the 3-hour soaks the time from the reboot to normal operation was 235–563 s (Lua alpha20) and 258–498 s (alpha21 with C).

Waiting for the firmware after a tunnel rebuild (`VENDOR-SETTLING`):
- Soaks, probe level 1: about 120 s per rebuild, between 0 and 228 s observed.
- alpha23 (faster monitor passes, variant A): 119–139 s. Variant A changed almost nothing, because the 120 s settle period dominates.
- alpha24 (settle period of at most 45 s, variant B): not measured.

Switch history as a journal (schema 2, alpha21). Measured on x86 in a Docker image with Python 3.11 and Lua 5.1 (not on the router), 1285 events in 7 days:

| | schema 1 (alpha20) | schema 2 (journal) |
|---|---|---|
| File the page reads | 899.6 KB | 134.4 KB (state) |
| Event archive | none | 978.8 KB |
| Python, one event written | 93.2 ms | 35.2 ms |
| Lua, one event written (CPU / wall) | 102.4 / 119.4 ms | 23.6 / 35.4 ms |

Flash written per event: about 0.9 MB before, about 134 KB of state plus one archive line of about 760 bytes now. The C JSON module, measured in an aarch64 emulator on a 1 MB history document: encode 5.5 times, decode 18 times faster; on real router files (read only) parsing 10–12 times and building 4–7 times faster, output byte-identical to Lua.

## 8. Runtime pyramid and switch times

Each layer runs the same files and the same rules; a lower layer takes over when the one above fails. The times are the documented MT3000 measurements above. "Not measured" means no number exists in the project documents; nothing here is estimated. The Python figures come from older versions (1.0.0-beta5 to beta13, probe level 3 with boost for automatic faults) and are not a like-for-like comparison with the Lua figures.

| Layer | What runs there | Manual switch: traffic moved / done | Automatic: Auto decision after an outage | Automatic: traffic moved after the decision | Power cut during a switch |
|---|---|---|---|---|---|
| C + Lua (default, `canon_c.so` on) | Lua 5.1 monitor and Auto as two services (optional single process `hv-core`); the C module does the canonical JSON inside Lua | 0.5 s / 0.7 s (alpha21); 0.49–0.59 s / 0.71–0.81 s (alpha22) | 26–28 s with fast detection at probe level 1 (25.8–29.5 s in the table); 58–88 s before | 1.3–1.6 s | recovered by itself, 2 of 2; normal operation 255 s after the boot (soaks: 258–498 s) |
| Pure Lua (`HOMENSAI_CANON_C=0`, or the module fails to load or its self-probe) | the same Lua services, canonical JSON in Lua | 0.6–0.8 s / 1.05–1.3 s (alpha21) | not measured (fast detection was measured with the C module on) | not measured | not measured for alpha21; the Lua-only alpha20 soak: 235–563 s to normal operation |
| Python fallback (Python 3.9 `agent.py` and `native_switch.py`; used when the Lua options are off or after `LUA-AUTO-FALLBACK`) | everything in Python | 4.1 s / 5.5 s (1.0.0-beta13); with Auto on 3.2–5.3 s / 4.2–6.6 s (1.0.0-beta10 runs) | 129–136 s from the fault to traffic on the reserve (1.0.0-beta5 and beta7 means), of which the switch itself 39–44 s; fast detection on Python: not measured | included in the 39–44 s above | not measured |

Notes:
- Fast detection (`option lua_fast_detect '0'` turns it off), the 3 s HTTPS wait and the 45 s vendor settle period are rules of both the Python and the Lua core, but only the Lua core with the C module has been measured with fast detection, and the 3 s and 45 s changes have not been measured at all.
- Since 2.0.0-alpha24 the Lua services and fast detection are the installed default (owner decision: the fastest measured configuration); `option lua_monitor '0'` / `option lua_auto '0'` start the Python services. The fallback steps and their codes: `HV-CORE-FALLBACK`, `LUA-AUTO-FALLBACK`.
- Not measured anywhere in the project documents: a physical power cut, a 24-hour soak of the current build, the hand-over time of `LUA-AUTO-FALLBACK`, MT6000.
