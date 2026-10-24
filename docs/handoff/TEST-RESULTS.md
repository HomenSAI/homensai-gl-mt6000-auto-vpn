<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](../CURRENT-STATUS.md) · [documentation index](../DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Alpha6 offline results

232 application Python + 5 QA tests, 8 Node UI suites, 54 responsive/language checks, 256 cascade series/2048 steps, 200 statistics series/12000 steps. Broader prototype/demo regression and 50000-tick soak passed. Detailed report: ../../qa/ALPHA6-LOCAL-REPORT.json. QEMU was not resumed.

# Tests and evidence

| Evidence | Result | Scope |
|---|---|---|
| Alpha4 guest suite | PASS, 194 tests, reproducible package | qa/openwrt-vm-alpha4-final.json |
| Alpha5 Debian suite | PASS, 202 tests | Canonical Linux source; full suite includes package alignment |
| Alpha5 guest suite | PASS, 202 tests in 68.269 guest seconds | qa/openwrt-vm-alpha5-final.json; network/firewall unchanged; Auto disabled |
| Five Node suites | PASS | Inventory, recovery, setup, traffic, Auto (15 invariants) |
| Actual VM browser | PASS for stated desktop checks | EN -> RU -> EN, eight sections, three wizard openings/cancellations; qa/openwrt-alpha5-*.png/json |
| Nested publication scan | PASS, 276 indexed files at that checkpoint | Includes new alpha5 IPK; final handoff additions require another scan |
| Git archive-privacy suite | PASS, 23 tests | Disposable repositories; compressed secrets and unsafe archive paths refused |
| Cold start with cache limit | PASS at initial cache128 start | Same disk, 256 MiB guest, network/firewall preserved |
| Warm reboot with cache limit | UNCONFIRMED, 180-second timeout | qa/openwrt-vm-warm-reboot-cache128.json; preserve previous failures too |
| Cold restoration after that failure | NOT ACCEPTED | Runner stopped on user request, then QEMU paused |
| Physical alpha5 transition/deployment | NOT RUN | User authorized local work only |

Historical physical results remain in ../WORKLOG.md and ../TESTED-ENVIRONMENT.en.md. Do not combine them with the alpha5 VM evidence into a claim that every current feature works on hardware.
