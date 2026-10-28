<!-- doc-role: versioned-evidence -->
# Alpha51 installed on the dedicated MT3000 — 28 October 2026

**Installation: PASS. Auto process: RUNNING / OBSERVING. Publication: PASS.** [GitHub prerelease v0.9.1-alpha51](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha51) is not a draft. The package and checksum were downloaded and verified. The canonical feature branch was saved in Gitea and a separate push confirmed it was up to date. GitHub latest remains v0.9.0. See the follow-up functional failure below.

Package **0.9.1-alpha51-1**, `homensai-auto-vpn_0.9.1-alpha51-1_all.ipk`, **902881 bytes**. SHA256:

```text
e87946336bcf39981cda27132c14f44a3dfb848eeccc4901fd62fbfee5786e8b
```

Tested code commit: `4c0ecda151106eab0c7be1569276dcd28ddb6637`. Package-record commit: `0a83d88b978afa26c0ac1d1d29ea8a8b35dc0967`. This batch implements Tasks 1–3 of the [work order](handoff/SOL-6.1-WORK-ORDER-2026-10-28.md): a narrowly checked record commit can reuse its direct parent's CI receipt, CI records tools/lab/Lua coverage, and dashboard patches assert their expected anchor counts. The assertion conversion preserved the generated page content; new publication diagnostics are separately included in the catalogue.

## Source and package verification

Frozen-source CI passed on Python **3.11.2** and **3.9.15**, producing the same package hash. Counts include explicitly reported skips:

| Check | Python 3.11 full matrix | Python 3.9 runtime matrix |
|---|---|---|
| Application tests | 889, 0 skipped | 889, 0 skipped |
| QA tests | 147, 2 skipped | 147, 37 skipped |
| Tools tests | 20, 0 skipped | 20, 20 skipped |
| Offline lab cases | 60, 0 skipped | 60, 0 skipped |
| Separate Lua-backed verification | 13 executed | 13 executed |
| UI suites | 69 passed | Not run in the runtime-only row |
| Lab Node suites | 2 passed | Not run in the runtime-only row |

The Python 3.11 row covers the tools cases skipped in the Python 3.9 environment. VM/router/network lab entry points are explicitly excluded from offline CI. The separate Lua run proves actual Lua execution; its count is not added to the application-test total.

An isolated Python 3.9 build of the same code commit produced the identical **902881-byte** package and SHA256. The record commit adds the package and release record; its restricted scope is checked instead of repeating full CI on that record commit. Publication through this exact parent-receipt path passed; the record commit was not subjected to another full CI run.

## Physical installation and normal Start

The dedicated **GL-MT3000** passed encrypted backups before and after installation, including independent decryption and archive readback. Installation followed the normal Stop/install/verify/Start procedure.

Verification passed for **89 payload files**, protected configurations, retained terms, routes, actual HTTP-served **dashboard126.js / ui92.css**, and fresh RPC data. After installation verification passed, normal Start reached **RUNNING / OBSERVING in 21.4 seconds**. Readiness was verified with no blockers; both VPN channels passed router DNS and two HTTPS checks. Protected configurations and interfaces were unchanged across Start.

Normal Start encountered a failing stock-VPN-boot preparation check and repaired it through the reviewed preparation writer. The resulting preparation check was read back as PASS. This bounded preparation change is part of the recorded Start result.

## Follow-up functional failure

After delivery the owner reproduced **SOURCE-ORDER-MISMATCH** when requesting the reserve manually. Read-only evidence showed the configured reserve already ahead of the primary, while the displayed channel path incorrectly treated the unchanged startup order as primary selection. The inspected kernel also lacked the expected stock RTP marking chains; tunnel-bound DNS/HTTPS probes do not establish the general LAN path. This is **FAIL / under correction in alpha52**, not a completed manual-switch or LAN acceptance result. The existing refusal guard was not bypassed.

## Limits

This is installed-package, router-observation and normal-Start evidence for the dedicated MT3000. It does not establish external LAN-client acceptance, a 24-hour soak, power-cut recovery, IPv6 acceptance or MT6000 continuous-mode acceptance. It does not claim a native-browser interaction test or another physical fault/switching test for alpha51.

[Current status](CURRENT-STATUS.md) · [Project review](REVIEW-2026-10-28.md) · [Installation guide](INSTALL.en.md)

---

# Alpha51 установлена на выделенном MT3000 — 28 октября 2026 года

**Установка: PASS. Процесс Auto: RUNNING / OBSERVING. Публикация: PASS.** [GitHub prerelease v0.9.1-alpha51](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha51) опубликована, Draft выключен. Пакет и контрольная сумма скачаны и проверены. Исходная feature-ветка сохранена в Gitea; отдельный push подтвердил актуальность. Стабильная latest остаётся v0.9.0. Ниже отдельно указан выявленный функциональный отказ.

Установлен пакет **0.9.1-alpha51-1**, размер **902881 байт**, SHA256 указан выше. Проверенный код: `4c0ecda151106eab0c7be1569276dcd28ddb6637`; коммит с пакетом: `0a83d88b978afa26c0ac1d1d29ea8a8b35dc0967`.

Выполнены задачи 1–3: публикация проверяет строго ограниченный коммит с пакетом по квитанции его прямого родителя; CI учитывает тесты инструментов, безопасные проверки стенда и фактическое выполнение Lua; каждая текстовая правка страницы проверяет ожидаемое число совпадений. Сам перевод правок на строгие проверки не изменил содержимое страницы; новые коды публикации добавлены отдельно.

CI прошёл на Python **3.11.2** и **3.9.15** с одинаковым хешем пакета. В каждой среде: **889 тестов приложения без пропусков**, **147 QA-тестов** с 2 пропусками на 3.11 и 37 на 3.9; **60 проверок стенда без пропусков** и отдельный прогон **13 Lua-тестов**. Из 20 тестов инструментов все выполнены на 3.11 и все явно пропущены на 3.9. На полной среде 3.11 также прошли **69 UI-наборов и 2 Node-набора стенда**. Эти наборы не выполняются в строке, предназначенной только для Python 3.9. Скрипты, которым нужны VM, роутер или сеть, явно исключены из автономного CI.

Изолированная сборка того же коммита на Python 3.9 дала пакет того же размера и хеша. Для следующего коммита, который только записывает пакет и его контрольные значения, предусмотрена строгая проверка состава изменений вместо второго полного CI. Публикация с квитанцией родительского коммита успешно проверена; второй полный CI на записи пакета не выполнялся.

До установки и после неё сделаны зашифрованные резервные копии с независимой расшифровкой и чтением архива. Выполнены штатные Стоп, установка, проверка и Старт. Проверены **89 файлов пакета**, сохранность защищённых конфигураций, условий использования и маршрутов, реальные HTTP-файлы **dashboard126.js / ui92.css** и свежие данные RPC.

После успешной проверки установки обычный Старт за **21,4 секунды** вывел Auto в **RUNNING / OBSERVING**. Готовность подтверждена, блокирующих причин нет; оба VPN прошли DNS и две HTTPS-проверки самим роутером. Защищённые конфигурации и интерфейсы при Старт не изменились. При запуске обнаружена мешающая настройка штатного автозапуска VPN; обычный механизм подготовки исправил её через проверенный механизм записи, затем результат прочитан повторно и получил PASS.

После доставки владелец воспроизвёл **SOURCE-ORDER-MISMATCH** при ручном выборе резерва. Резерв уже стоял выше основного в сохранённых правилах, а индикация ошибочно считала неизменившийся порядок признаком выбора основного. В просмотренных правилах ядра также отсутствовали ожидаемые цепочки маркировки RTP; отдельные DNS/HTTPS-пробы внутри туннелей не доказывают путь общего трафика LAN. Ручное переключение — **FAIL, исправляется в alpha52**. Защита отказа не обходилась.

Эти результаты не подтверждают приёмку внешнего клиента LAN, суточную работу, восстановление после отключения питания, IPv6 или непрерывный режим MT6000. Для alpha51 здесь не заявлены проверка действий в настоящем браузере или новый физический тест сбоя/переключения.

[Текущее состояние](CURRENT-STATUS.md) · [Разбор проекта](REVIEW-2026-10-28.md) · [Установка](INSTALL.ru.md)
