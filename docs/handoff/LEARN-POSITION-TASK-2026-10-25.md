# Checkbox position / Позиция при выборе ответов

Owner reports that checking an answer in Help → training scrolls the page to the top. Selecting/deselecting must preserve the current question, viewport, focus and other choices; no navigation or state reset.

Cause: the change handler called draw(), which removed/rebuilt the entire training host. Fix the selection and enabled state of Check answer in place. Preserve dynamic disabled guards, stale-handler protection, grading and repeated/keyboard/label choices. Regression should model browser scroll/focus loss when connected nodes are removed, and assert unchanged DOM identity/location/viewport for all question choices EN/RU.

Status: source implemented and focused regression passed across all11questions EN/RU; full CI/install/publication pending in alpha24; alpha23 is the installed/published baseline. Next focused/UI/dual CI, new module100/CSS72, dedicated MT3000 normal backup/Stop/update/Start/reserve, GitHub/Gitea actual release and handoff. Private continuation: private/learn-position-alpha24-20261025. Native browser proof remains separate from automated DOM/device evidence.
