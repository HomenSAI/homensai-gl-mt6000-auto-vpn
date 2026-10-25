<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# UCI correction results — 2026-10-16T17:46:34.8839610+02:00

| Check | Result | Evidence |
|---|---|---|
| Full application suite | 301 PASS in Python 3.9/Lua, no skips | ../qa/ALPHA7-REVISION2-CI.json |
| QA / UI | 9 QA per runtime; 9 UI suites PASS | ../qa/ALPHA7-REVISION2-CI.json |
| Real libuci interrupted-save / package refusal | 15 PASS | ../qa/alpha7-uci-delta-fixed.json |
| Read-only UCI writes / own service recovery | 11 PASS | ../qa/alpha7-revision2-uci-failures.json |
| Package rollback / reupgrade | 13 PASS | ../qa/alpha7-revision2-rollback.json |
| Warm reboot | PASS, 82.6 host seconds | ../qa/alpha7-revision2-warm-reboot.json |
| Physical GL-MT6000 | NOT TESTED in this work window | No installation performed |

Cause: libuci reused saved pending deltas from the previous process. Correction: refuse nonempty/unverifiable own-config staging before settings writes, preserve pending data, propagate fixed codes, refuse pending package lifecycle commits. Success requires exact writer OK plus zero return code. The actual opkg refusal is verified by unchanged state, not by process exit alone.

Payload: homensai-auto-vpn_0.7.0-alpha7-2_all.ipk; 452968 bytes; SHA256 9f8e952873dd236bbb6470bfffcbcb4e0daeb7501335f6ab2472cab6e19725ac. No public release or hardware acceptance claim.

Scope limits and next hardware gate: [current status](handoff/STATUS.md). Resolution steps: [UCI pending changes](UCI-PENDING-CHANGES.md). Broader virtual protocol/kernel acceptance remains separate.
