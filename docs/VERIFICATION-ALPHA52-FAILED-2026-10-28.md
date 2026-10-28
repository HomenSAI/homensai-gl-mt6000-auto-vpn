<!-- doc-role: versioned-evidence -->
# Alpha52 physical start refused / Отказ физического запуска alpha52

The dedicated GL-MT3000 with GL.iNet 4.11.0 received `0.9.1-alpha52-1` on 28 October 2026. Code `f1435bdeefa0a1052e63add5c1625e1e00da3684`, package-record child `cc5eb7dab02ee2aa5b25e5aec032334d9f38a5fc`; package 947688 bytes, SHA256 `6aca80703165b0c70932cb8754b7bb1e676baba448086a4b3cac4b2126a4b774`.

Dual-runtime CI and the independent Python 3.9 build passed with that hash. Each runtime passed 975 application tests without skips, 150 QA tests (2/37 skips), 60 offline lab cases and 13 Lua cases. The full Python 3.11 row also ran 20 tools tests, 77 UI suites and two Node lab suites; tools were explicitly skipped on runtime-only 3.9. Installation verified all 93 payload files, protected settings, terms, main routes and served dashboard127/ui93/help127. Encrypted backups before installation and after the failed start/Stop passed independent decryption and complete archive reads.

**Auto start failed; alpha52 was not published.** The first recorded refusal was `VENDOR-WORKER-QUIET-UNVERIFIED`, followed by `KERNEL-POLICY-UNVERIFIED` and a retained recovery journal. Bound DNS and two HTTPS checks passed on both VPNs; that did not establish a working general traffic path. The normal Stop turned Auto off and removed the owned guard, but reported `PAIR-EXTERNAL-POLICY-CHANGE`; the failed reapply journal remained `RESTORING`.

Read-only inspection proved that `/tmp/run/vpn-client-booted` was absent. The pinned stock `rtp2.sh` returns exit 0 before doing any work when that file is absent. The stock VPN init creates it in `boot()`, while the application's preparation disables stock boot. The generated VPN hotplug rule file was absent too. Thus a successful command exit was a no-op, and the new kernel attestation correctly refused to declare the route ready. Four subsequent worker observations were verified and idle; the precise transient process-read cause of the first quiet refusal was not established by those later samples.

Independent reproduction also confirmed that Stop did not close an owned failed no-order-change activation journal even when the original missing kernel graph was preserved. This requires a guarded recovery correction, not a blind journal deletion or an unverified stock reload. The next candidate must preserve this evidence, retain the alpha52 package, rerun CI/build/install gates and obtain actual switching/browser acceptance. No external LAN, physical fault, power-cut, IPv6 or full-day claim follows from this failed installation.

---

На выделенный MT3000 установлена alpha52 с указанным выше хешем. CI двух сред, отдельная сборка, проверка 93 файлов, новых HTTP-ресурсов, сохранности настроек и условий прошли. Зашифрованные копии до установки и после отказа с последующим Stop независимо расшифрованы и полностью прочитаны.

**Запуск Auto не прошёл, alpha52 не опубликована.** Сначала получен `VENDOR-WORKER-QUIET-UNVERIFIED`, затем `KERNEL-POLICY-UNVERIFIED`. Оба VPN отдельно проходили DNS и две HTTPS-проверки; это не доказывало общий путь трафика. Штатный Stop выключил Auto и снял его защитную блокировку, но сообщил `PAIR-EXTERNAL-POLICY-CHANGE`; журнал неудачного применения остался в `RESTORING`.

Причина неприменённых правил подтверждена чтением: отсутствовал `/tmp/run/vpn-client-booted`. Без него закреплённый штатный скрипт немедленно возвращает «успех», ничего не делая. Штатный init создаёт флаг при загрузке, а подготовка приложения отключает этот штатный автозапуск. Новая проверка kernel-правил правильно обнаружила отсутствие результата. Последующие четыре наблюдения процессов были достоверными и свободными; они не объясняют точную кратковременную ошибку чтения процессов при первом отказе.

Отдельно воспроизведён дефект закрытия собственной неудачной операции, не менявшей порядок правил. Исправление должно подтверждать исходное состояние и принадлежность операции, сохраняя отказ на чужих изменениях. Неудачные доказательства и пакет alpha52 сохраняются; следующий кандидат проходит все этапы заново. Фактическая приёмка ручного переключения и браузера ещё необходима.
