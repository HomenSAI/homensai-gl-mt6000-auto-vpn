# Combined owner UI batch / Общая партия интерфейса

## English

Version0.9.1-alpha22 combines13 owner corrections. Language changes keep the active page and full/simplified mode. Explicit simplified-view entry starts at the page top; polling preserves reading position. Its exit button is now Advanced menu.

The original Auto power control is the only stop/cancel control in the full view and setup wizard. Stop can supersede an in-flight Start and remains retryable after transport failure. Stop acknowledgment is not controller completion. Monitoring continues. The technical/emergency section and forecast card were removed without changing backend startup certification or recovery.

Persistent preparation now has four columns. WireGuard/OpenVPN startup control describes independent boot startup separately from current connection or Auto state. Latency line samples identify primary/reserve; current route is a separate fresh observation. Eight statistical notes are collapsed and retain expansion during refresh. Roleless archive records remain stored/exportable without a separate archive counter block or invented roles.

Long journal/history messages are plain text. Only short blue event/state/cause links open their dictionary definitions, with underline on hover or keyboard focus. Wizard labels/buttons/inputs share typography and spacing; checkbox labels use one native accessible control.

## Русский

Версия0.9.1-alpha22 объединяет13 правок. Смена языка сохраняет фактический раздел и обычный/упрощённый режим. Явный переход на упрощённый интерфейс открывает верх страницы; обновления сохраняют прокрутку. Кнопка выхода — «Расширенное меню».

Единственная кнопка Auto останавливает режим и отменяет ожидающий запуск, в том числе в мастере. Ошибка связи допускает повторную остановку; принятый запрос не выдаётся за подтверждённую остановку. Мониторинг продолжается. Убраны отдельные технические действия и прогноз; реальные проверки контроллера и восстановление сохранены.

В постоянной подготовке четыре столбца. Управление запуском WireGuard/OpenVPN объясняет отдельный запуск при загрузке, не текущее соединение. Образцы линий обозначают основной и резервный каналы; текущий маршрут указан отдельно по свежим данным. Восемь пояснений статистики свёрнуты. Архив без роли сохраняется в данных и экспорте, но отдельный счётчик скрыт; исторические роли не выдумываются.

Длинные сообщения журнала и истории — обычный текст. Короткие синие коды/статусы открывают словарь; подчёркивание только при наведении и фокусе. В мастере согласованы шрифты, переносы и отступы, используется один нативный чекбокс с доступной подписью.

## Verification boundary / Проверка

All13 changes implemented. Final exact-source dual-runtime CI,54Node UI suites, canonical build and dedicated MT3000 update/readback passed. Publication follows this evidence commit. Native browser layout/hover proof must be reported separately from Node/HTTP/device data checks.
