# HomenS.AI Auto VPN — maintainer entry

Read docs/SESSION_STATE.md first (short current state); open docs/CURRENT-STATUS.md, docs/RELEASE-0.9.0.md and docs/handoff/CURRENT.md only for the section you need. README.md/README.ru.md describe the current release. Main contains the released application; old prototype-only/stopped-window descriptions are historical.

Before device work consult private/ACTIVE-EXECUTOR.local.json and the current owner instruction. Only one executor may operate the dedicated MT3000 at a time. Do not resume historical observers or fault rules. Primary MT6000 and Windows networking remain excluded unless separately authorized. Model selection never bypasses detected hardware/firmware/readiness checks. Never accept terms for the owner or silently start Auto.

Respect verified facts and scope: router-probed IPv4 continuous mode/actual operator switching are implemented; external LAN,24-hour soak,power-cut,IPv6 and MT6000 continuous-mode acceptance remain separate. Preserve failed evidence. Save checkpoints/restore-verified source bundles and private encrypted backups; publish only the owner-authorized refs/assets. Never force-push or overwrite historical tags/packages. GitHub and canonical Gitea histories may differ while reviewed trees match. Documentation-only changes do not require another router reinstall.

Historical independent-review proposals remain in .claude/handoff and dated reports. They are not current approvals, pauses or instructions to execute every old backlog item. Use docs/ROADMAP.md for current open work.

<!-- HSAI-CLAUDE-CONTEXT-PREFLIGHT:BEGIN -->
Предварительное чтение и кэширование промптов (кэш 1 ч всегда включён): [docs/rules/AI-PREFLIGHT-CACHING.md](docs/rules/AI-PREFLIGHT-CACHING.md) — читать по необходимости.
<!-- HSAI-CLAUDE-CONTEXT-PREFLIGHT:END -->

## Модели агентов и порядок сессий (решение владельца 15.11.2026, экономия лимитов)
- Модель и effort для каждой задачи выбирает оркестратор и пишет их в отчёте: механика (прогон тестов, перенос по готовому образцу, поиск, форматирование, документы) — Sonnet, effort medium; код с логикой (переключение каналов, деньги, безопасность, параллельность, непонятная ошибка) — Opus, effort medium или high; Fable — только по решению владельца (отдельные сложные решения, итоговое ревью).
- Модель указывать явно в каждом запуске агента (worker, general-purpose) — никогда «как у основной сессии». Sonnet дважды не справился — та же задача тому же агенту (SendMessage) на Opus, а не новый агент.
- Не больше 2 агентов одновременно; соседнюю задачу — продолжением агента (SendMessage), а не новым.
- Одна задача — одна сессия; в конце — состояние в docs/SESSION_STATE.md (что сделано, что дальше), затем новая сессия.
- Смена задачи — /clear; длинная сессия — /compact после каждого крупного шага.
- Не держать сессию ради ожидания: ежечасные проверки и ночные наблюдения — запланированными задачами с чистым контекстом.

## Ссылки на правила (читать по необходимости)
- Коды ошибок — только из базы HomenSAI/ERROR-DATABASE (пространство VPN 005): [docs/rules/ERROR-CODES.md](docs/rules/ERROR-CODES.md).
- Модели NanoGPT (GLM-5.3 thinking по умолчанию): [docs/rules/NANOGPT.md](docs/rules/NANOGPT.md).
