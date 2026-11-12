# HomenS.AI Auto VPN — maintainer entry

Read docs/CURRENT-STATUS.md, docs/RELEASE-0.9.0.md and docs/handoff/CURRENT.md first. README.md/README.ru.md describe the current release. Main contains the released application; old prototype-only/stopped-window descriptions are historical.

Before device work consult private/ACTIVE-EXECUTOR.local.json and the current owner instruction. Only one executor may operate the dedicated MT3000 at a time. Do not resume historical observers or fault rules. Primary MT6000 and Windows networking remain excluded unless separately authorized. Model selection never bypasses detected hardware/firmware/readiness checks. Never accept terms for the owner or silently start Auto.

Respect verified facts and scope: router-probed IPv4 continuous mode/actual operator switching are implemented; external LAN,24-hour soak,power-cut,IPv6 and MT6000 continuous-mode acceptance remain separate. Preserve failed evidence. Save checkpoints/restore-verified source bundles and private encrypted backups; publish only the owner-authorized refs/assets. Never force-push or overwrite historical tags/packages. GitHub and canonical Gitea histories may differ while reviewed trees match. Documentation-only changes do not require another router reinstall.

Historical independent-review proposals remain in .claude/handoff and dated reports. They are not current approvals, pauses or instructions to execute every old backlog item. Use docs/ROADMAP.md for current open work.

<!-- HSAI-CLAUDE-CONTEXT-PREFLIGHT:BEGIN -->
## Required preflight and prompt caching (owner instruction, 2026-11-12, updated with measurements)
Read **all of AGENTS.md** and its AI context/caching policy before substantive work. Inventory the project and current state; fully trace task-relevant code/docs; reuse a compact context map; targeted reads, trimmed tool output (`head`/`tail`/`cut`), no pasting of whole repositories, logs or JSON.
**Prompt caching is the main cost lever, always on.** Claude Code: user settings `~/.claude/settings.json` must contain `"promptCacheTtl": "1h"` and `"subagentPromptCacheTtl": "1h"` (documented settings; subagents otherwise get 5 min and every wait > 5 min rewrites their whole context). Do not switch model, effort or fast mode mid-session; continue a running agent (SendMessage) or fork instead of starting a fresh one; long commands in the background. Direct Claude Messages API: stable shared material first with `cache_control` at the end of it, the changing question after; cache only when the prefix is read again (1 task: no marks; 2+ tasks starting together: 5m + one `max_tokens: 0` pre-warm; 3+ queued: 1h); every report states **with cache $X vs old way $Y, saved $Z, ×K** from `cache_creation_input_tokens` / `cache_read_input_tokens`. Respect every existing project safety and release rule. Full policy: https://github.com/HomenSAI/homensai-core/blob/main/docs/AI_CONTEXT_EFFICIENCY_POLICY.md
<!-- HSAI-CLAUDE-CONTEXT-PREFLIGHT:END -->
