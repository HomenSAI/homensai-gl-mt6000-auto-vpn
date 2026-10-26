# Minimum UI alpha26 — release handoff / 26 October 2026

## Published / Опубликовано — 26.10.2026

Design prerelease `v0.9.1-alpha26` is published on [GitHub](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha26) and [Gitea](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha26). Six attachments per service were downloaded and SHA256 verified. Canonical tag source: `7e958ed83e90bcf917409c6a933519c86b2b8603`; public tag source: `4693aae997b2f370cc7affbdc270ddfb8382fe72`; equal tree `51d410661cd453d939c59e41f7214f3a8f62fd9b`. Product tested source remains `e2d67b38b235a42b55fa536a4c99cd443a1d59c1`. Immutable tags/assets must not be changed. Subsequent branch commits are documentation closure only.

Опубликован отдельный prerelease нового дизайна, пакет `0.9.1-alpha26-2`. Шесть файлов на каждом сервисе скачаны и проверены. Main/stable/latest сохранены. Собственные VM выключены; физический роутер не изменялся. Эксплуатационный допуск/LAN/отказы/питание/суточный тест остаются отдельным этапом. Перед повтором внешнего действия читать `private/minimum-ui-20261026/publication.json` и реальные refs.


## English

The owner executed revision 3. Minimum and the five-section Advanced menu are implemented, with the accepted palette B. Coordinator plus three fixed agents completed UI, behavior and independent QA work. Do not restart the original implementation plan blindly.

Final product source: `e2d67b38b235a42b55fa536a4c99cd443a1d59c1`; version `0.9.1-alpha26`, package `0.9.1-alpha26-2`, module `dashboard102`, stylesheet `ui74.css`. IPK SHA256 `84c9c58f79915681163c8c0fab3f56a976f902dcdfcd0bf3c866a308abadb2d8`, 866573 bytes. Later commits may add evidence/documents only; verify the product diff before reusing these receipts.

Read `docs/VERIFICATION-ALPHA26-2026-10-26.md`, `qa/MINIMUM-UI-ALPHA26-2026-10-26.json`, `docs/CURRENT-STATUS.md`, and the live Git state. Publication/readback is recorded in `private/minimum-ui-20261026/publication.json`; inspect actual remote refs before retrying any external action.

Passed gates: dual pinned Linux CI with equal IPK hashes; 778 app /112 QA tests each with explicit complementary skips, 60 UI suites; canonical-payload native Chromium 26 groups ×41 checks; real isolated x86 OpenWrt normal package upgrades including final revision2, protected configs/terms/persistence marker preserved, Auto off, fresh RPC and 87 files/modes/served assets. Native browser proof uses synthetic RPC, not the physical router. Initial failures and corrections are retained privately.

Fixed integration findings include stale Start at click time, single actual control across views, pending cancellation, unsaved settings/deep-link handling, and selecting the real scan action rather than the monitor block sharing its class. Settings leads with pair fields; language/theme and technical data are disclosures. Experimental fault injection remains in test tooling.

No physical router installation or network change was performed. External LAN, actual-device browser, fault/power-loss and 24-hour acceptance remain open. Main/stable are outside this delivery. A next physical pilot requires the actual authorized target/window, fresh identity, verified private backup and Stop/install/verify/explicit Start workflow; old alpha25 authorization/receipts are not fresh acceptance.

Temporary preview: read `private/minimum-ui-20261026/preview.json` for PID/expiry; loopback `http://127.0.0.1:64173/?lang=ru#home`, synthetic data only, automatically bounded to three hours. Do not stop old gateways/previews or unrelated Docker processes. Disposable VM cleanup and final archive receipts belong in the private run folder. Do not restart stopped lab VMs unless new tests require them.

Next action: report/inspect the new prerelease or address a specific owner request. Do not reinstall or rerun bandwidth tests simply to continue this handoff. To claim operational readiness, finish the separate physical/LAN/fault/soak matrix on the exact candidate, preserving failures.

## Русский

Редакция 3 исполнена: «Минимум», принятые цвета и пять разделов расширенного меню реализованы. Работали координатор и три субагента; старый план не запускать заново автоматически.

Финальный пакет — **0.9.1-alpha26-2**, 866573 байта, SHA256 `84c9c58f79915681163c8c0fab3f56a976f902dcdfcd0bf3c866a308abadb2d8`. Проверенный исходник `e2d67b38b235a42b55fa536a4c99cd443a1d59c1`, dashboard102/ui74. Более поздние коммиты доказательств/документации допустимы только при неизменном продукте.

Доказательства: `docs/VERIFICATION-ALPHA26-2026-10-26.md` и `qa/MINIMUM-UI-ALPHA26-2026-10-26.json`. Фактическая публикация и скачивание assets — `private/minimum-ui-20261026/publication.json` плюс удалённые refs. Нельзя считать push/release состоявшимся только по этому тексту.

Прошли два Linux CI, 60 UI-наборов, 26×41 проверки настоящего Chromium на каноническом пакете и реальное обновление отдельной x86 VM с RPC/HTTP и 87 файлами/правами. Данные браузерного стенда явно синтетические; это не браузер физического роутера. Исправлены ошибки свежести Start, навигации/черновика и выбора реальной кнопки scan. Условия, конфигурации и тестовый маркер данных VM сохранились.

На физический роутер версия не устанавливалась. LAN/реальные отказы/питание/суточная работа остаются отдельной приёмкой. Main/stable не входят в изменения. Следующий пилот — только по соответствующему разрешённому scope, со свежей идентификацией, проверенной копией и контролируемым Stop/install/verify/явным Start.

Для просмотра реализации доступен временный локальный preview на порту 64173; PID/срок в preview.json. Старые шлюзы, чужие процессы и остановленные VM не трогать. Дальше выполнять конкретный запрос владельца либо отдельную эксплуатационную приёмку; повторять установку/измерения без причины не нужно.
