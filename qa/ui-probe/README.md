# Current shipped UI browser gate

`python qa/ui-probe/current_gate.py` (also `probe.py gate` and `scripts/ui-probe.ps1`) tests the current `.hvx` Simple/Console/four-step wizard UI. It requires a clean known Git HEAD, no untracked files, and immutable in-memory public inputs. Dirty/unknown sources fail before a browser starts. `--smoke` is a one-group development check classified **NON_RELEASE-SMOKE**, never a publication PASS.

The full matrix uses one owned headless Edge process and reuses one same-origin frame sequentially: seven surfaces (`home`, `settings`, Console `ch/auto/srv/log/sys`) at 1440/390 px, RU/EN, light/dark: 56 page assertions plus 32 wizard-step assertions. Real view/tab clicks check hash, selected navigation and rendered content. Every current disclosure is opened, lazy help is rendered in a real modal, and Escape closes it. Header/footer identity permits the program version and forbids package/page metadata.

Primary and reserve active scenes each measure both Simple and Console channel cards. On applicable desktop layouts the active share is 0.618 with absolute tolerance 0.005 (0.5 percentage points), calculated from actual outer card widths excluding the gap. Golden columns and wizard columns use the same measured right-hand share. At 390 px the gate instead requires full-width, vertically separated physical boxes; computed style alone cannot pass it.

The wizard uses the existing synthetic pair fixture: natural first run, four steps, invalid equal channels, back/draft retention, unchecked terms/disabled Start, save-without-start, skip, incomplete-but-running, incomplete-with-existing-pair and explicitly opened wizard while running. `incomplete=1` changes only the RAM fixture marker. The test never presses Start or accepts terms; unexpected `native_*`/`terms_accept` calls fail. RAM fixture saves are not physical-router persistence proof.

Frozen identity covers index, stub, fixture-pair, all allowlisted view assets, the lazy module subtree, current module/CSS, and exact QA harness/PowerShell entrypoint hashes. The served analyzer must match its frozen hash. Current server routes never discover or contact a router. A dedicated ephemeral loopback port (never legacy 18898) and unique profile isolate each run. Shutdown targets only that run's Popen PID tree. No global Edge enumeration/cleanup is performed.

Source manifests, per-row checkpoints, Edge logs/profiles and final results have unique run names under `private/ui-probe/`; failed/incomplete attempts remain. Missing/duplicate surfaces, wizard steps, boundaries, geometry cases, script/resource failures and incomplete attempts fail closed. After a QA commit, rerun the full matrix on that clean exact HEAD. Root must repeat it on the final cherry-picked source; this synthetic browser gate does not replace full CI, the LuCI host or physical-router acceptance.

Verification: `python -m unittest discover -s qa/ui-probe -p test_current_gate.py -v`, `node --check qa/ui-probe/current_analyse.js`, then a NON_RELEASE smoke, commit without version bump, then the full clean-source matrix. No Docker/full CI is needed to run this host-side gate.

## Historical A/B/C harness and retained evidence

The original `analyse.js`, `scenarios.js`, onboarding and persona tools below describe the legacy UI. `probe.py legacy-gate` explicitly selects its old 24-case gate; `scen` remains historical. They do not establish current UI readiness: preview loads the menu-selected shipped module, whereas those analyzers expect `.hv-app`, `--dv-line`, old page hashes and design A/B/C controls. The current module renders `.hvx` with Simple/Console and a four-step wizard. Merely aliasing the old root selector would still test the wrong navigation and identity contract.

The legacy README and evidence are retained below without rewriting their historical claims.

---

<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../../docs/CURRENT-STATUS.md) · [documentation index](../../docs/DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# UI page probe

Offline check of every LuCI page in every design (A/B/C), theme and width. Synthetic fixture only; it never contacts a router.

- `probe.py` starts the loopback fixture server (port 18898, same handler as `scripts/serve-ui-preview.py`) and opens headless Microsoft Edge on a probe page. The page loads the app in a same-origin frame, waits until the app and its stylesheet are ready, and posts the result back; Edge is then stopped.
- `analyse.js` (matrix): horizontal page overflow and the elements that cause it, owner attributes visible (attribution line, author footer, version badge), DESIGN-VIEW-ERROR, script errors, text contrast below 3:1, clipped text.
- `scenarios.js` (scen): every section link opens its page (hash, visible page, aria-current); key 2 opens the second section only in design C; Settings > Page design applies each design at once, stores it, redraws the Overview in that design and keeps it after a reload.
- `summ.py result.json ...` prints the findings.

Known limits: the contrast rule reports false positives on gradient buttons (`cbi-button-action`) and on the gear symbol; a run whose stylesheet did not finish loading within 30 s reports unstyled overflow (rerun it alone). Results and Edge profiles are written to `private/ui-probe/`, which is git-ignored.

Run the bounded persona matrix with `python qa/ui-probe/probe.py fool 0-49 --workers 2` (use `--workers 1` to isolate a case). The persona clock starts only after a stable app, attribution and stylesheet are ready. Missing readiness remains a failure. Reloads have bounded waits; RPC calls and script errors are retained across documents.

Each batch serves an immutable in-memory copy of the allowlisted public preview assets. A `source-fool-*.json` manifest records their SHA256 values, the harness hash, Git HEAD, tracked-dirty state and recorded product identity. Each `case-fool-*.json` begins as an explicit incomplete attempt and is atomically completed; the aggregate `result-fool-*.json` is written after the batch. New attempts get new filenames. Failed and incomplete attempts remain available for review. The CLI exits nonzero for errors, missing interaction/app/owner attributes, out-of-range RPC values, call storms, large lags, DOM growth or horizontal overflow.
