# Switching speed measured on the GL-MT3000

All numbers come from the dedicated GL-MT3000 (OpenWrt 21.02 / GL firmware 4.11). The primary channel is WireGuard and the reserve is OpenVPN. Measured on 30 Oct 2026.

The faults were controlled: the Tests page function blocks the primary's traffic for a fixed time. Times are seconds from the fault start or from the click. Russian version: [MEASUREMENTS.ru.md](MEASUREMENTS.ru.md).

Key numbers:
- Auto: time to traffic on the reserve went from 153 s to 129–136 s.
- The automatic switch itself went from 60 s to 39–44 s.
- The return to the primary is about twice as fast: 50 s to 24–25 s.
- The manual button went from 42 s to 16.6 s (beta8) and then to 9.9 s (beta9) until done, with traffic moved after 8.2 s.

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

Measured on the router on 30 Oct 2026 with 1.0.0-beta9. Total RAM is 480 MB (491,320 kB).

| What | Size | Share of RAM |
|---|---|---|
| Available to programs (MemAvailable) | 109 MB | 22.7% |
| Monitor service (agent, including the status kept in memory) | 45.3 MB | 9.4% |
| Auto service (native_switch, including the history kept in memory) | 40.0 MB | 8.3% |
| **Both of our services** | **85.3 MB** | **17.8%** |
| For comparison: GL web server (nginx, 3 processes) | 99 MB | 20.6% |

What one service is made of (measured in a separate process):

| Part | Size |
|---|---|
| Bare Python | 6.5 MB |
| Program code (import) | +9.4 MB, about 16 MB in total |
| Event history kept in memory (Auto service only) | +7.8 MB (1.6% of RAM) |
| Page status: the observation file and the finished reply (monitor service only) | +3.0 MB (0.6% of RAM) |

Before the resident copies (beta6 and earlier), the services used about 11 MB less, around 2.2% of RAM. Peak use while recording an event was the same, because the history was read in full anyway. Now that memory is simply not released between events.

Safeguard: from beta10, the history is kept in memory only while at least 64 MB is available. Otherwise the service reads the file as before.

Other resources:
- state files in RAM (/var/run/homensai-vpn): 0.6 MB;
- data on flash (/etc/homensai-vpn): 4.1 MB, of which the history takes 2 × 1.27 MB;
- the flash overlay partition is 18% used (24 of 139 MB).
