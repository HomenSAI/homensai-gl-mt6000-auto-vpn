<!-- doc-role: versioned-candidate -->
# Auto VPN — Minimum UI · 0.9.1-alpha26

## English

This design prerelease replaces the crowded daily view with Minimum: current Auto state, the confirmed channel, the existing guarded Auto button, reserve health and an explicit Advanced menu. The accepted Calm/B palette, local IBM Plex fonts and power control are retained.

Advanced menu has five sections:

- **Channels:** the selected primary/reserve pair; profile details and other profiles open on demand.
- **Diagnostics:** bounded connection checks, explicit bandwidth tests, recovery and technical observations.
- **Events:** recent events, period/type filters, retained history and traffic; detailed analytics is collapsed.
- **Settings:** a persistent pair editor with explicit review, Save/Cancel and protection against leaving an unsaved draft. Optional settings remain in disclosures and their validated editors.
- **Help:** four common tasks, full instructions/code lookup, optional training and About.

Minimum is accessible when Auto is off or status is unknown. Display access never authorizes Start. Both views reuse the same actual Auto control, including immediate cancellation of pending Start. Its handler rechecks freshness at click time. Navigation and display changes do not call command RPCs. Old section links map to the new sections; language changes retain the subsection.

Upgrade preserves application data, terms and unrelated settings. Old layout preferences no longer select alternate designs; language and theme remain available. Initial setup retains eight validated internal stages, grouped into three semantic phases. Saving settings does not start Auto.

This is a prerelease for testing. Exact source/package, CI, VM and browser outcomes belong in [verification](VERIFICATION-ALPHA26-2026-10-26.md). The current device installation remains separately recorded in [Current status](CURRENT-STATUS.md). No new physical MT3000 installation, external LAN/fault/power-loss proof or 24-hour soak is implied by this design release. MT6000 and IPv6 qualification remain separate.

Recovery: stop Auto and confirm the actual result before a package change. Use a verified private backup and the matching installation/recovery kit. Do not downgrade an active device or overwrite a published package/tag. Follow [installation](INSTALL.en.md), [validation](VALIDATION.md) and [recovery](../router-test-kit/EMERGENCY.md).

## Русский

Отдельный prerelease нового дизайна заменяет перегруженный ежедневный экран на «Минимум»: состояние Auto, подтверждённый канал, прежняя защищённая кнопка Auto, состояние резерва и заметное «Расширенное меню». Сохранены принятые цвета B, локальные шрифты IBM Plex и круглая кнопка.

В расширенном меню пять разделов:

- **Каналы:** выбранные основной и резервный; сведения и остальные профили раскрываются по необходимости.
- **Диагностика:** ограниченная проверка соединения, явный запуск скорости, восстановление и технические наблюдения.
- **События:** последние записи, фильтры периода/типа, сохранённая история и трафик; подробная аналитика свернута.
- **Настройки:** сохраняемый в сессии черновик пары, проверка изменений, Save/Cancel и защита от случайного ухода. Необязательные настройки доступны в раскрываемых группах и проверяемых редакторах.
- **Помощь:** четыре частые задачи, полные инструкции/коды, необязательное обучение и «О программе».

«Минимум» доступен при выключенном Auto и неизвестном состоянии. Доступ к экрану не разрешает Start. На обоих экранах используется один реальный элемент управления, в том числе для немедленной отмены ожидающего запуска. Свежесть повторно проверяется при клике. Навигация не отправляет команды. Старые ссылки ведут в соответствующие новые разделы; смена языка сохраняет подраздел.

Обновление сохраняет данные, условия и посторонние параметры. Старое предпочтение оформления больше не переключает разные дизайны; язык и тема доступны. В первичной настройке сохранены восемь внутренних проверяемых стадий, объединённых в три смысловые группы. Сохранение настроек не включает Auto.

Это выпуск для тестирования. Точный исходник/пакет и результаты CI, VM и браузера указаны в [отчёте](VERIFICATION-ALPHA26-2026-10-26.md). Установленная на устройстве версия отдельно записана в [Current status](CURRENT-STATUS.md). Выпуск не означает новую установку на MT3000, проверку внешнего LAN, физических отказов/питания или суточную работу. MT6000 и IPv6 требуют отдельной квалификации.

Для отката сначала остановить Auto и подтвердить фактическое состояние. Использовать проверенную приватную копию и комплект установки/восстановления нужной версии. Не понижать версию на активном устройстве и не заменять опубликованные пакеты/теги. См. [установку](INSTALL.ru.md), [проверку](VALIDATION.md) и [восстановление](../router-test-kit/EMERGENCY.md).
