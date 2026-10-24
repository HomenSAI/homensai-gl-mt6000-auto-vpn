<!-- doc-role: versioned-evidence -->
# Auto VPN0.9.1-alpha14 — verification and delivery

## Выполнено

Актуальные RU/EN руководства, встроенная помощь, установка с AI, диагностика, обучение и мастер приведены к текущим режимам и управлению профилями. Полные справочники31тема/язык,458кодов и четыре промпта формируются из исходников;82промпта включены в матрицу рецептов. Старые свидетельства сохранены как архив, условия1 и лицензии не изменены. Два дефекта помощников исправлены: запросы управления через другой интерфейс и фиксация незавершённых правок/неудавшейся остановки. В мастер добавлены настройки хранения.

ПолнаяCI точногоfe3b492:771тест приложения+112QA в каждой из двух сред,46UI; пропуски сред указаны в квитанциях. Сборки одинаковы:829928байт,SHA256`49ffb3e57b288f899c84e77546e7b1a0e26243300765bf5927ef8270ae214342`. Ошибочный промежуточный8984120 отклонён из-за старого хеша установочного набора;fe3b492 исправляет его, новый полныйPASS получен.

НоваяOpenWrt21.02.7x86VM: проверенная стабильная0.9.0 установлена и повторена, затем обновлена до14;87файлов/прав,RPC/HTTP,мастерRU/EN,хранение100/1,1500/2,2000/7 и отказы неверных значений,компоненты,диагностика31темы,настоящий аварийный скрипт с незавершённой правкой. VM штатно выключена exit0. ПодменаGL-идентичности и обходguards не применялись.

MT3000/4.11.0: свежая шифрованная190-entry копия и независимая проверка → нормальныйStop →opkg14 →87файлов/прав иHTTP8080/HTTPS → нормальныйStart →резерв →свежиеDNS+2HTTPS обоихVPN →сравнение настроек/условий →шифрованная190-entry копия после. AutoоставленВКЛ на резерве. ОсновнойMT6000 и сетьWindows не менялись.

## English and scope

Current RU/EN docs, Help, AI prompts, training and setup are aligned with source behavior. Generated references and prompt digests detect drift. Exact-source dual-runtimeCI and new real isolatedOpenWrt installation/upgrade acceptance passed. DedicatedMT3000 is updated, AutoON/confirmedreserve, bothVPN DNS+2HTTPS healthy, with settings/terms and encrypted backups independently verified.

The82-prompt matrix validates actual recipes and native/mock helper paths, not autonomous ChatGPT/Claude execution. ActualWindowsCheckOnly refusedCLIENT-CABLE-PROBE-ROUTE-MISMATCH; the computer network was left unchanged. Native physical-browser visuals, independentLAN/IPv6/KillSwitch, every possible firmware/fault and physicalpower-loss durability remain unverified. No physical fault was injected and noTelegram message sent. [QA matrix](../qa/OWNER-DOCS-ALPHA14-2026-10-24.json) · [Physical receipt](../qa/MT3000-ALPHA14-2026-10-24.json) · [Audit](DOCUMENTATION-AUDIT-2026-10-24.md).

## Publication

Actual non-draft prereleases published: [GitHub alpha14](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha14) · [Gitea alpha14](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha14). Four assets each downloaded back and SHA256-verified. Canonical tag/source`388879bd1ef28a7bb0eb385cf10754bc97c84437`; public tag/source`17740c6e83cfd89a45b0f7947b81ace6f9eaa83a`; identical reviewed tree`b61b99e60c9eda6d0034d8ddf589f43749b594ed`. Both feature histories preserved; stable0.9.0 and main refs unchanged. A documentation-only closure follows; product bytes remain those tested atfe3b492.
