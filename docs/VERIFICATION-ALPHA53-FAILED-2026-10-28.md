<!-- doc-role: versioned-evidence -->
# Alpha53 physical refusal / Физическая приёмка alpha53 не пройдена

Dedicated GL-MT3000, GL.iNet 4.11.0, 28 October 2026. Code `dc7cc9315d77652c535e17c94fbee8c9220bf775`, record `17b8ef35279d3f6e4241522990f8ea61335f95e7`; package 952264 bytes, SHA256 `a4d62a1b88366940c82289b64161c10c76d3388194f1a391001e001457eff97d`.

CI passed on Python 3.11/3.9 with equal hashes, and the independent Python 3.9 build matched. Each runtime ran 1004 application tests without skips, 150 QA tests (2/37 skips), 60 lab cases and 13 Lua cases. Full 3.11 additionally ran 20 tools tests, 77 UI suites and two Node lab suites; runtime-only tools were explicitly skipped. Installation verified all 95 payload files, protected settings, terms, main routes and actual dashboard128/ui94/help128 HTTP resources.

The guarded pre-upgrade recovery successfully archived and closed the exact inactive alpha52 no-op journal without changing configuration, kernel rules, boot gate or budget. A fresh encrypted backup preceded it. The alpha53 boot-prefix correction then worked: the gate was created and actual kernel attestation verified the reserve path. Saved ICMP results included 174.8 ms on OpenVPN and 55.1 ms on WireGuard, independently of HTTPS health.

**Auto acceptance nevertheless failed; alpha53 was not published.** The stock RTP script added `options_in_used='0'` to exactly the two no-override selected rules, and moved the WWAN interface before an IPv4-rule block. A RAM-only comparison with the verified encrypted pre-alpha53 backup established identical network values and multiplicity, identical IPv4-rule relative order and identical other-section relative order. Only their interleaving changed. Rule `via`, marks and user selectors did not change.

The controller hashed those derived details as identity, held Auto as `PAIR-EXTERNAL-NETWORK-CHANGE`, and the rollback writer persisted an incompatible `restore_before_order`. The file checksum remained valid, but its structure failed the journal reader. The Stop request was recorded OFF; the pair remained HELD with its VPN-only guard, while the kernel still verified the reserve path. This is not successful Auto or independent LAN-client acceptance.

Alpha54 must model only the proven derived changes, validate journal objects before writing, check live identity before rollback mutation, and reconcile this exact own state through a reviewed, archived, revision-fenced recovery. The independent old baseline was parsed with actual firmware libuci through anonymous RAM descriptors; the prior network identity, policy hash and order matched exactly, with zero plaintext files or UCI writes. This proof does not authorize accepting other differences. Hardware recovery and the next Start remain separate gates.

Native UI inspection during this failed state found the initial menu covered by the expected “Auto did not start” error dialog. The screenshot identified `modal_overlay` and its Close button; this was not proof of a navigation hit-area defect. Complete installed UI acceptance was not passed.

---

Alpha53 установлена и проверена, но полную физическую приёмку не прошла и не опубликована. Исправление штатного флага сработало: действующие правила подтвердили резервный канал, оба VPN проходили отдельные проверки, получен настоящий ICMP Ping.

Штатный RTP добавил только два служебных поля `options_in_used=0` и переместил интерфейс WWAN относительно блока IPv4-правил. Сравнение с зашифрованной копией доказало, что значения сети и взаимный порядок правил сохранились. Контроллер ошибочно счёл это чужой правкой. Затем откат сохранил несовместимые идентификаторы секций в журнале: контрольная сумма правильная, структура неправильная.

Запрос Auto выключен; пара остаётся HELD с собственной VPN-блокировкой, действующий путь резерва подтверждён ядром. Это не успешная работа Auto и не приёмка внешнего клиента LAN. Alpha54 должна строго распознать только доказанные служебные изменения и проверить журнал до записи. Исходная структура уже восстановлена исключительно в памяти и дала точное совпадение прежних хешей; остальные различия принимать нельзя.

Браузерная проверка первого перехода остановилась на штатном окне «Auto не запустился». Снимок подтвердил именно это перекрытие; полная проверка установленного интерфейса ещё необходима.
