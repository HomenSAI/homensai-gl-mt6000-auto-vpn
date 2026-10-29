#!/bin/sh
# usage: run_harness.sh <source-dir> <label> [cases]
S="C:/Users/hosePC/AppData/Local/Temp/claude/c--homensai-homensai-gl-mt6000-auto-vpn/3ea88335-da8f-49e3-be07-25aa5c192a99/scratchpad"
W="C:/homensai/homensai-gl-mt6000-auto-vpn/private/switching-finish-worktree"
MSYS_NO_PATHCONV=1 docker run --rm --init --name hv-qa-harness --network container:hv-qa-qemu-backend --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,exec --user 1000:1000 -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp \
 -v "$1:/src:ro" -v "$W/qa/evidence/switching-2026-10-28:/qa:ro" -v "$W/qa/evidence/switching-2026-10-28/finish/backend:/out" \
 -e QA_REPO=/src -e QA_REPRODUCTION=/qa/reproduction -e QA_OUTPUT=/out -e QA_LABEL="$2" -e QA_CASES="${3:-move1,move2,forward}" -w /tmp \
 --entrypoint python3 homensai-vpn-python311:local /qa/followup/reproduction/real_rollback_crash.py
