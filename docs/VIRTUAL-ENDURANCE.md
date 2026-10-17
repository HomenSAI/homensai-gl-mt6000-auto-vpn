> Current checkpoint: the owner stopped the alpha2 run before its 12-hour deadline. See qa/alpha0802-endurance-stopped.json and .claude/handoff/STATE.md. Do not restart it automatically; the procedure below is reference for a future authorized run.

# Virtual endurance procedure and evidence boundaries

The runner operates only on marked Docker container homensai-vpn-qemu-alpha7, with network none, no host mounts and no privilege. It never contacts physical-router addresses. Keep the Windows host and Docker running.

Freeze run_virtual_endurance.py, endurance_state.py and virtual_endurance_watchdog.py from the exact tested Git commit into a private directory. The runner verifies all three frozen files against Git before starting. The manifest identifies source SHA, exact package hash and installed code hashes. No credentials, profile names, exit addresses or session data are collected.

First execute a 60-second smoke with --smoke --duration 60 --interval 30. This is not a 12-hour acceptance run. Both producer and independent cleanup must complete before PASS.

The real run uses --duration 43200 --interval 60. It observes monitor version/freshness, exact installed code, process count/RSS, own-config and network/firewall/main-route fingerprints and Auto remaining off. Events and status stay in the private run directory. The observer never resumes a stopped VPN or modifies a route. Connected-provider/native cascade and physical LAN availability are outside this test.

RUNNING is unfinished. A producer-only success remains MEASUREMENTS-PASS until the independent watchdog confirms pause of the same marked clone. Errors, missing coverage, unexpected source/config/route changes or early stop prevent PASS. A single isolated VM endurance pass is not a hardware resource/flash or provider reliability certificate.

To stop cooperatively, create an empty STOP file inside the exact current run output directory. Do not kill arbitrary Python/Docker processes. Avoid concurrent serial helpers while the observer owns the guest. QMP status is read-only; do not install a different guest package during a run.

The independent watchdog pauses the same clone at terminal completion or after the bounded deadline plus cleanup reserve. If the Windows host itself stops, neither process can continue; inspect the last timestamps and report incomplete coverage rather than inventing a successful run.

## Update 2026-10-17: host sleep and lost producer

The runner now compares wall-clock and monotonic time between samples (`endurance_state.slept`): a sleeping host or a clock jump counts as a gap in both directions, so a run that slept can no longer pass. The watchdog checks that the producer process is alive without signalling it (`pid_alive`; os.kill(pid, 0) would terminate a process on Windows) and marks a run whose producer was seen dead on three consecutive polls as STOPPED with reason PRODUCER-LOST at once, instead of waiting for the deadline. Neither change makes a short or interrupted run a PASS.
