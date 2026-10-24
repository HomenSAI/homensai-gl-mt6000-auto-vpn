<!-- doc-role: current -->
# Управление и настройка / Control and setup

[RU guide](CURRENT-STATE.ru.md) · [EN guide](CURRENT-STATE.en.md) · [First run](FIRST-RUN-SETUP.md)

| Действие / Action | Реальный результат / Effect |
|---|---|
| Проверить VPN / Check VPN now | Запрос свежих наблюдений; не выбирает маршрут / Requests observations without selecting a route |
| Сохранить мастер / Save setup | Собственные параметры приложения; не принимает условия и не включает Auto / Own app preferences, no terms acceptance or Auto start |
| Start Auto | Явный управляемый запуск подготовленного режима; ждите подтверждения / Explicit prepared-mode start, await confirmation |
| Ручной канал / Manual selection | Запрос выбранного канала с актуальными проверками; ACK не завершение / Guarded channel request, ACK is not completion |
| Stop Auto | Отмена ожидающего запуска и управляемое восстановление; итог проверяется / Revokes pending start, managed recovery must be verified |
| Тест сбоя / Fault test | Ограниченный сбой текущего туннеля, проверка другого маршрута / Bounded current-tunnel fault and alternate-route check |
| Мониторинг / Monitoring | Независимые измерения; часы журнала не ускоряют сетевые пробы / Independent measurements, log clock does not accelerate probes |

Два клиента выбираются на шаге 3 общего мастера. Для другой привязки сервера/протокола сначала используйте штатную VPN-панель, затем обновите Auto VPN и дождитесь согласованной идентичности. Не меняйте штатные профили во время управляемого перехода.

Storage controls are available in setup step 2 and Settings → Monitoring and history retention: live count1–2000, detail days1–7. Preserve existing values by default. Short monitor preferences supports profile limit1–16; the complete wizard can retain supported legacy values up to32. For a selected pair,2 is a useful starting limit; it does not activate stopped profiles by itself.

Для подтверждённой остановки проверяйте фазу/guard/восстановленный или удержанный маршрут. `STOPPED-ON-RESERVE` не означает успешный возврат исходного пути. [Аварийные команды](../router-test-kit/EMERGENCY.md) — осознанное восстановление, а не обычное чтение.
