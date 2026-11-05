#!/bin/sh
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
# Manual, NOT part of CI: the unreduced profiles of the formal model (offline, standard-library Python 3.9+).
# held/restart/faults/server: about 1-2 minutes each; "full" (everything on): about 20 minutes and ~3 GB RAM.
# Results: results-<profile>.txt (traces) and results-<profile>.json (counts). The CI gate is ci_check.py (reduced bounds).
set -e
cd "$(dirname "$0")"
PY=${PY:-python3}
VARIANT=${VARIANT:-fix}   # alpha6 (before 58921e2f), fix (released code), fix2 (all K fixes of fix/formal-k2-k5-20261103)
$PY model.py --variant "$VARIANT" --no-crash --no-power --no-expire --out results-held.txt     --json results-held.json
$PY model.py --variant "$VARIANT" --no-gl                          --out results-restart.txt  --json results-restart.json
$PY model.py --variant "$VARIANT" --no-gl --no-power --faults      --out results-faults.txt   --json results-faults.json
$PY model.py --variant "$VARIANT" --no-gl --no-crash --faults      --out results-faults-power.txt --json results-faults-power.json
$PY model.py --variant "$VARIANT" --no-gl --no-power --server      --out results-server.txt   --json results-server.json
$PY model.py --variant "$VARIANT"                                  --out results-full.txt     --json results-full.json
