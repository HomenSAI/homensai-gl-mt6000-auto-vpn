# HomenS.AI Auto VPN 0.9.1-alpha25

## Русский

Исправление распространено на все внутренние кнопки обучения: «Проверить ответ», «Дальше/Назад», переходы к урокам и вопросам, оглавление, результаты, таблицу результатов, повтор ошибок и перезапуск. Обработаны сворачивание встроенного курса и обновления интерактивных схем. Общая перерисовка сохраняет прокрутку и подходящий фокус. Высота страницы не обрушивается во время замены содержимого; если новый блок короче, сохраняется только место, необходимое для текущей позиции. Прежнее обновление чекбоксов на месте, проверка ответов и защита от старых/повторных действий сохранены.

Проверки:57UI-наборов,778application/112QA в каждой из двух изолированных сред; дополнительные проверки всех11вопросов EN/RU с моделированием потери прокрутки/фокуса при удалении DOM. Та же регрессия выполнена на точном Linux-модуле из канонического IPK, совпадающем с установленными HTTP/HTTPS-байтами. Рабочий Windows-файл CRLF отдельно не выдавался за канонические Linux-байты. Нативная визуальная проверка/клики браузера не выполнены.

MT3000 обновлён штатно:87файлов/права/RPC/HTTP/HTTPS сверены; Auto включён и оставлен на подтверждённом резерве, оба VPN DNS/HTTPS исправны. Сохранены2046закрытых прежних строк задержек, все6результатов скорости, соглашение и несвязанные настройки. Новые тесты скорости не запускались.193-entry зашифрованные копии до/после независимо прочитаны в памяти. Основной MT6000, сеть компьютера и стабильный0.9.0 не изменены.

## English

All internal training redraws preserve viewport and meaningful focus: grading, Next/Back, lesson/question chips, contents, results/table jumps, retry/restart, embedded course toggles and scene frames. Temporary height retention prevents collapse during replacement, and only the required tail space is retained when a shorter document would clip the saved viewport. Existing in-place checkbox updates, score and stale-action guards remain.

Exact source `4811e3c7e7ee0070fee913bf7d6d783f7780d86b` passed dual-runtime CI778application/112QA each and57UI suites, with complementary skips retained. All11questions EN/RU were tested for in-place selection/clearing/bursts and focus/viewport preservation; the same regression passed on canonical generated code matching installed bytes. Native browser visual/click proof remains unverified. MT3000 normal update/AutoONreserve/health/settings/history preservation and independent encrypted backup reads passed. Canonical856917bytes, SHA256 `38b377ad2e3522405450942e5f918f565b90ac2f6abdc825302b4c03022f8d3a`. Actual non-draft prerelease; stable0.9.0 remains unchanged.

[QA](../qa/LEARN-ACTIONS-ALPHA25-2026-10-25.json) · [MT3000](../qa/MT3000-ALPHA25-2026-10-25.json)

## Published / Опубликовано

[GitHub alpha25](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha25) · [Gitea alpha25](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha25). Actual non-draft prereleases, four assets each downloaded and SHA256verified. Canonical release/tag `d0fc7dd82d15d5910fc8f4365eb633c1194fbd3a`, public release/tag `0533bf41dafff2db8824ffcd95d0fd42fb53a01b`, equal release tree `9a7c22e864511ab1c3c0989890e6e30c799bc6bb`. Stable/main unchanged; documentation-only closure follows.
