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
