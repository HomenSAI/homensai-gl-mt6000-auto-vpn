<!-- doc-role: versioned-evidence -->
# HomenS.AI Auto VPN 0.9.1-alpha21

Упрощённый интерфейс теперь доступен всегда при подтверждённом включённом Auto, независимо от завершённости мастера и отметок тестов. Работающий Auto также открывает карточку при обычном входе без принудительного незавершённого мастера. Эти отметки не изменяются автоматически.

При выключенном/неподтверждённом Auto кнопка красная. Наведение, фокус или тап показывают подсказку о необходимости настроить систему и включить Auto; Escape скрывает её. Нажатие красной кнопки не открывает карточку и не запускает Auto. Ошибки, переключение и отсутствие данных каналов отображаются внутри карточки без выдуманных сведений. Требования реального запуска Auto и отдельное соглашение сохранены.

Confirmed enabled Auto always grants simplified-view access, independently of setup/test completion markers. Off/unconfirmed Auto has a red, focusable shortcut with a hover/focus/tap setup tooltip and Escape dismissal. Unavailable clicks never start Auto. Channel faults, handovers and missing data are displayed honestly; actual controller startup protections remain unchanged.

Final exact-source dual-runtimeCI774application/112QA each/52UI passed; complementary skips recorded. A flaky worker-test/UCI-cache dependency was found and isolated; the first patch used the wrong import boundary and was corrected.28native tests then passed independently in both runtimes before the final full CI. These were test-only changes; the canonical production payload hash stayed unchanged. Both failed attempts are retained in QA.

MT3000 actual normal update/87files/modes/RPC/HTTP/pinnedHTTPS passed. Actual OFF data denied access with a setup tooltip; actual ON data granted access while setup_complete/onboarding_complete remainedfalse. No completion flags were changed to make the test pass. Auto left ON/confirmedreserve, both VPN DNS/HTTPS healthy; settings, terms, history and four speed results retained; encrypted backups before/after independently decrypted/read.

Native-browser visual/hover acceptance not performed. Experimental prerelease; main/stable0.9.0 unchanged.

## Evidence

Final tested source `4ae700097b3b921d9cf7b396e98f661fd18c8f7c`.849653byteIPK SHA256 `caadfa384d048c384f3efc3ca9f27dcf9e019420a77879d187cd13581865d29e`. [QA](../qa/AUTO-ACCESS-ALPHA21-2026-10-25.json) · [MT3000](../qa/MT3000-ALPHA21-2026-10-25.json) · [Current access rule](SIMPLE-HOME-2026-10-25.md).

Actual off-state snapshot was captured after necessary installation Stop and before Start, adding no extra interruption. Actual on-state snapshot followed normal Start/reserve restoration. Current router data with unfinished setup markers enabled the header shortcut and rendered actual bound profiles/endpoints; there was no completed-setup projection in this acceptance. Native browser paint/hover/click is not claimed.

Preserved1729closedlegacy latency rows, open minute excluded; four speed results retained. Before/after encrypted backups193/193entries independently decrypted/read. Only expected native_trial/native_until lifecycle values changed; all other own settings retained. No hostnetwork/mainMT6000/firmware changes or synthetic device data.

Initialf004055CI failed inPython3.9 when global Popen mock intercepted expired UCI configured_days lookup. The first fixture patchf9589fb targeted a nonexistent native_history attribute (configured_days is imported locally), causing28setup errors. Final4ae7000 patch targets retention_settings.configured_days; actual History/rollback/certificate assertions remain. Production payload unchanged; all failures and final proof are separate.

Publication next, product unchanged after final CI.

## Published

[GitHub alpha21](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha21) · [Gitea alpha21](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha21). Actual non-draft prereleases, four assets/server downloaded/SHA256verified. Canonical source/tag `c54ccd42efbf95f41f1609e448bde333a9e856ed`, GitHub source/tag `7ab8fb6a85812ecb4ea1cfc4078fdd7c1b6386cf`, equal release tree `60dbddd08d752870b3c6b6729a60d1eb619b46c4`. Product unchanged after final CI; main/stable preserved. Docs-only closure follows.
