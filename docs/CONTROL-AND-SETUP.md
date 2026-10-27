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

## Auto switching rules / Правила переключения Auto

The **Settings → Auto switching rules** form edits check interval (10–300 s), source failures (3–10), reserve successes (2–10), cooldown (60–1800 s), minimum dwell (60–3600 s), forward attempt limit (1–10) and rolling window (1–15 minutes), primary return successes (2–10), primary stability (30–600 s), and return policy. The Default values selection restores 10 s / 3 / 2 / 60 s / 60 s / 3 per 15 minutes / 2 over 30 s / healthy-primary return. Existing saved values survive upgrade.

«**Настройки → Правила переключения Auto**»: интервал 10–300 с; ошибки основного 3–10; проверки резерва 2–10; пауза 60–1800 с; пребывание 60–3600 с; 1–10 попыток за 1–15 минут; проверки основного 2–10 и стабильность 30–600 с; политика возврата. Кнопка «Значения по умолчанию» восстанавливает 10 с / 3 / 2 / 60 с / 60 с / 3 за 15 мин / 2 за 30 с / автоматический возврат. Уже сохранённые настройки при обновлении не сбрасываются.

Stop Auto and confirm managed recovery before saving. Review the values; saving changes only the application settings and does not start Auto. Attempt history is retained for the full maximum window, even when a shorter window is chosen, so changing the policy or starting a new session does not erase attempts. / Перед сохранением остановите Auto и дождитесь подтверждённого восстановления. Сохранение меняет только настройки приложения и не запускает Auto. История попыток сохраняется за полный максимальный период, даже если выбран более короткий; изменение правил и новый запуск её не стирают.
