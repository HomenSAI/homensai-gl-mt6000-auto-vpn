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

The attempt limit never stops Auto from leaving a failed primary. From the failover that reaches the limit within the window, each further one doubles how long the primary must be stable before the return (up to 10 minutes); the hold shrinks as failovers leave the window ([flap damping](architecture/FLAP-DAMPING-2026-11-02.ru.md)). / Лимит попыток никогда не мешает уйти с упавшего основного. Начиная с ухода, достигшего лимита в окне, каждый следующий удваивает время стабильности основного перед возвратом (до 10 минут); по мере выхода уходов из окна время сокращается.

Large packets: the monitor also checks every 5 minutes (on every check while a hole is seen) that packets of the tunnel MTU pass; a tunnel that passes the small checks but loses all large ones reports VPN-MTU, which counts as a failure, so Auto prefers the other tunnel when it passes. TCP MSS on the tunnels is already clamped by the GL firewall zones. Optional SQM (cake) on the tunnel egress is off by default and is switched on only by SSH (`sqm_enabled`, `sqm_upload_kbit`) ([design note](architecture/MTU-SQM-2026-11-03.ru.md)). / Большие пакеты: монитор раз в 5 минут (а пока видна «дыра» — на каждой проверке) проверяет, что пакеты размером с MTU туннеля проходят; туннель, который проходит малые проверки, но теряет все большие, получает VPN-MTU — это сбой, и Auto предпочитает другой туннель, если тот проверку проходит. TCP MSS на туннелях уже ограничивают зоны брандмауэра GL. SQM (cake) на выходе туннеля по умолчанию выключен и включается только по SSH.

Stop Auto and confirm managed recovery before saving. Review the values; saving changes only the application settings and does not start Auto. Attempt history is retained for the full maximum window, even when a shorter window is chosen, so changing the policy or starting a new session does not erase attempts. / Перед сохранением остановите Auto и дождитесь подтверждённого восстановления. Сохранение меняет только настройки приложения и не запускает Auto. История попыток сохраняется за полный максимальный период, даже если выбран более короткий; изменение правил и новый запуск её не стирают.
