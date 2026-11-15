<!-- doc-role: rules · перенесено из CLAUDE.md/AGENTS.md 15.11.2026 без изменения смысла (экономия лимитов, решение владельца) -->
## NanoGPT models (owner decision 13.11.2026; measured on 12-13.11.2026)

Use NanoGPT (monthly subscription endpoint `https://nano-gpt.com/api/subscription/v1/chat/completions`, key from the user environment
`NANOGPT_API_KEY`, never printed or committed). **Use `z-ai/glm-5.3:thinking` as much as possible for everything** - it counts x1
against the subscription; the other two count x2 and are used only rarely:

| Use | Model | Subscription multiplier | reasoning_effort | max_tokens |
|---|---|---|---|---|
| **Everything by default**: code, code review, error/log diagnosis, tests, texts, translations | `z-ai/glm-5.3:thinking` | **x1** | high | 100000 |
| Rarely: a second opinion on a hard problem, or after GLM-5.3 failed 5 times | `deepseek/deepseek-v4-pro-0813:thinking` | x2 | high | 100000 |
| Rarely: C code ONLY (e.g. a Lua->C port) | `moonshotai/kimi-k2.7-code` | x2 | not sent | 65536 (model ceiling) |

Rules:
- At most **2 requests at once per model** (total <= 8); stream responses; on 429/503 wait `Retry-After` and retry.
- Answer limit 100 000 tokens. An EMPTY answer (stream cut, or the model spent the budget thinking) is re-sent up to **5 times** in
  total, only then stop. Never pin a provider (`X-Provider` is billed pay-as-you-go outside the subscription).
- Every complex problem goes to GLM-5.3 with a full dossier; Claude writes its own answer first (sealed) and compares.
- Model output is a proposal: nothing is accepted without our own tests and a Claude review. No secrets or personal data in prompts.
- Not used (measured weaker or unreliable): GLM-5.2, Nemotron 3 Ultra, Qwen3 Coder, DeepSeek V4.1 flash-1017, MiniMax M3, Devstral 2.

Why (12-13.11.2026 benchmark on real project tasks): GLM-5.3 was first in error diagnosis (found bugs and causes the others and Claude
missed), code review, our own functions graded by our unit tests (53 %), long tasks and test generation (74/75 cases consistent), and
it costs x1. DeepSeek V4 Pro was the most reliable second opinion; Kimi K2.7 Code wrote the best C port (20 000-case differential
check: 0 failures) but is weak on Python. Both cost x2.
