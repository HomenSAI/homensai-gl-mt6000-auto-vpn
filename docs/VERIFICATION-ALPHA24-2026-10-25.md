# HomenS.AI Auto VPN 0.9.1-alpha24

## Русский

Исправлен прыжок страницы при выборе ответов в обучении. Раньше каждое изменение чекбокса удаляло и строило весь блок заново. Теперь обновляются только выбранные ответы и доступность кнопки «Проверить ответ». Текущий вопрос, его элементы, прокрутка и фокус сохраняются. При автообновлении данных фокус восстанавливается на тот же чекбокс, а не на первый элемент с одинаковой пустой подписью. Оценка, повтор ошибок, снятие отметок и защита от старых/повторных действий сохранены.

Проверки:56UI-наборов,778application/112QA в каждой из двух изолированных сред; дополнительные проверки всех11вопросов EN/RU с моделированием потери прокрутки/фокуса при удалении DOM. Та же регрессия выполнена на точном Linux-модуле из канонического IPK, совпадающем с установленными HTTP/HTTPS-байтами. Рабочий Windows-файл CRLF отдельно не выдавался за канонические Linux-байты. Нативная визуальная проверка/клики браузера не выполнены.

MT3000 обновлён штатно:87файлов/права/RPC/HTTP/HTTPS сверены; Auto включён и оставлен на подтверждённом резерве, оба VPN DNS/HTTPS исправны. Сохранены2001закрытых прежних строк задержек, все6результатов скорости, соглашение и несвязанные настройки. Новые тесты скорости не запускались.193-entry зашифрованные копии до/после независимо прочитаны в памяти. Основной MT6000, сеть компьютера и стабильный0.9.0 не изменены.

## English

Training checkbox changes now update choices and Check-answer availability in place, preserving the current question, DOM, scroll and focus. Polling restores the exact retained checkbox instead of the first otherwise-identical control. Dynamic disabled guards, grading, wrong-only retry and stale-action protection remain.

Exact source `87a3439b766fe6fab1bfbd1bb7f4d02ac089ee54` passed dual-runtime CI778application/112QA each and56UI suites, with complementary skips retained. All11questions EN/RU were tested for in-place selection/clearing/bursts and focus/viewport preservation; the same regression passed on canonical generated code matching installed bytes. Native browser visual/click proof remains unverified. MT3000 normal update/AutoONreserve/health/settings/history preservation and independent encrypted backup reads passed. Canonical856098bytes, SHA256 `9cb411017f9c38e7092030b3a523a01477f9abab5af10ecea7a08bdc7f541c20`. Actual non-draft prerelease; stable0.9.0 remains unchanged.

[QA](../qa/LEARN-POSITION-ALPHA24-2026-10-25.json) · [MT3000](../qa/MT3000-ALPHA24-2026-10-25.json)

## Published / Опубликовано

[GitHub alpha24](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha24) · [Gitea alpha24](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha24). Actual non-draft prereleases, four assets each downloaded and SHA256verified. Canonical release/tag `01fdcd81da4f7415897cf558a9d2c3fb32b2be46`, public release/tag `e7a06764898f01698f0b12cc0af95deeb616457c`, equal release tree `05b65fa491c57787c253ba397c60d8d9412af8ec`. Stable/main unchanged; documentation-only closure follows.
