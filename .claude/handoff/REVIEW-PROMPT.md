# Prompt for Claude: independent completion and readiness audit

You are reviewing HomenSAI Auto VPN at a stopped checkpoint. Read CLAUDE.md and every file in .claude/handoff/, then inspect the actual source and referenced receipts. The owner wants an independent answer: what is implemented, what is actually verified, what remains, and whether we can begin a controlled test on GL.iNet GL-MT6000.

Do not assume the previous assistant's reports are correct. Cross-check claims against source, tests, exact SHA/version, timestamps and evidence scope. The partial 12-hour run is STOPPED by request, with independent cleanup; it is not PASS. Some earlier state documents and viewport claims were superseded; do not silently repeat them.

Work as an audit first. Do not install anything on a physical router, restart stopped tests, start background jobs, change Windows networking/VPN, or enable Auto. If your current direct user instruction authorizes bounded offline checks, identify their scope and record results; otherwise propose the necessary checks. Do not launch another agent or delegate unless directly authorized by the user or applicable project instructions.

Deliver:
1. REVIEW-REPORT.md: map ALL A01-A50 to DONE / PARTIAL / NOT DONE / UNVERIFIED / BLOCKED, with source file+line, test/receipt, limitation and next action. Identify already implemented features rather than reinventing them.
2. PHYSICAL-TEST-VERDICT.md: separate read-only preparation, monitor installation, bounded switching/rollback and unattended use. Use ROUTER-READINESS.md gates, explain exact P0 blockers and which optional items are not blockers.
3. A short ordered next-step plan with measurable acceptance and rollback/recovery requirements. Do not implement the entire backlog as a side effect of reviewing it.
4. Report security/logic defects with reproduction or evidence. Preserve unknown causes and failed attempts. Do not include keys, tokens, passwords, session cookies, raw private archives or unrelated personal data.

Read current code around agent.py/checkpoint_schema.py, native_switch/native_supervisor/native_lease/auto_control, cascade_executor/candidate_runtime, setup_config/recovery_settings, RPC ACL/plugin and UI generator/panels. Reconcile with docs/PRODUCT_REQUIREMENTS.md, docs/CASCADE-ADAPTER-CONTRACT.md, docs/CLIENT-TRIAL.md, docs/TESTED-ENVIRONMENT.en.md and timestamped WORKLOG.

Use the current canonical checkout, not an older Docker source mirror. Local Git/Gitea is primary. GitHub public history differs; never push the full canonical history, force main, merge unrelated roots to silence errors or overwrite historical tags. No publication is required merely to produce the review; follow the current user's explicit scope.
