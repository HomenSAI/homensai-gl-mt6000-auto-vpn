# Проверенная система / Tested and operational system

## Русский

Система протестирована и работает в подтверждённой конфигурации: GL.iNet GL-MT3000, прошивка 4.11.0, приложение 0.9.1-alpha25-1. По явному запросу владельца проверенная версия переносится в GitHub main с сохранением истории коммитов. Статус версии остаётся alpha/prerelease.

- Успешная CI в двух изолированных средах: Python 3.11 и 3.9; в каждом прогоне778 тестов приложения и 112 QA-проверок.57 UI-наборов выполнены в основной среде. Пропуски 16 тестов приложения/2 QA-проверок в основной и 17 QA-проверок во второй среде указаны в исходных квитанциях.
- На выделенном MT3000 проверены 87 файлов и права, RPC, HTTP и HTTPS с закреплённым сертификатом. Auto включён и оставлен на подтверждённом резервном канале; оба VPN прошли DNS/HTTPS.
- Проверены 11 вопросов/8 уроков RU/EN, сохранение позиции при проверке ответа, переходах, результатах, повторе и работе схем. Регрессия выполнена на каноническом модуле, совпадающем с установленными байтами.
- Сохранены настройки, соглашение, 2046 прежних закрытых строк задержек и все 6 результатов скорости. Зашифрованные копии до/после независимо прочитаны в памяти.

Нативные визуальные проверки/клики браузера не подтверждены. Этот отчёт описывает указанную конфигурацию и фактически выполненные проверки.

## English

The system is tested and operational in the verified configuration: GL.iNet GL-MT3000, firmware 4.11.0, application 0.9.1-alpha25-1. The owner explicitly requested promotion of this verified version to GitHub main while retaining commit history. The version remains an alpha/prerelease.

- Dual-runtime isolated CI passed on Python 3.11 and 3.9: 778 application/112 QA tests per run, with 57 UI suites in the primary runtime. The original receipts record 16 application/2 QA skips in the primary and 17 QA skips in the second runtime.
- The dedicated MT3000 passed 87 file/mode checks, RPC and served HTTP/pinned HTTPS verification. Auto was left ON with the reserve path confirmed; both VPNs passed DNS/HTTPS.
- All 11 questions/8 lessons EN/RU were checked, including viewport preservation through grading, navigation, results/retries and scenes. The canonical-module regression matches the installed bytes.
- Settings, terms, 2046 closed prior latency rows and all 6 speed results were preserved. Pre/post encrypted backups were independently decrypted/read in memory.

Native browser visual/click acceptance remains unverified. This report describes the specified configuration and checks actually performed.

## Evidence / Подтверждение

- [UI and CI receipt](../qa/LEARN-ACTIONS-ALPHA25-2026-10-25.json)
- [Physical MT3000 receipt](../qa/MT3000-ALPHA25-2026-10-25.json)
- [Detailed verification](VERIFICATION-ALPHA25-2026-10-25.md)
- [Live speed verification](VERIFICATION-ALPHA23-2026-10-25.md)
- Tested product source: `4811e3c7e7ee0070fee913bf7d6d783f7780d86b`
- Verified public source before documentation promotion: `c2b95aee4241d45d1da4f199d86c646c1a9518ca`
- Package: `homensai-auto-vpn_0.9.1-alpha25-1_all.ipk` (856917 bytes)
- SHA256: `38b377ad2e3522405450942e5f918f565b90ac2f6abdc825302b4c03022f8d3a`

The product source and package are unchanged by the bilingual main-branch description. / Двуязычное описание main не меняет исходники продукта и проверенный пакет.
