# Alpha34 installed — instrument sidebar — 2026-10-26

**PASS:** dedicated GL-MT3000, GL.iNet 4.11.0; 0.9.1-alpha34-1, dashboard110/ui82. Product source `e0ba6a727288b9f901bc46c32a8f3d08c18dcd0f`, SHA256 `578becade469974284f2584778875fa83956b8372d257f12eff19e13011f2a1a`. [Device receipt](../qa/MT3000-ALPHA34-2026-10-26.json) · [Candidate CI](../qa/ICON-SIDEBAR-ALPHA34-2026-10-26.json).

Desktop appearance C uses an 84 px rail and a compact scrollbar. The Advanced control has a visible icon, a 48 px target, full localized accessible name and tooltip, keyboard focus and the same expand/collapse behavior. Existing destinations, current selection and stored expansion are retained. Desktop A/B and mobile retain their visible labels.

Native Chromium/CDP validated C in five normal-height and two constrained-height RU/EN cases; the latter produced a real scrollbar. Bounds checks covered the icon button and all expanded items, and actual Enter activation changed/restored aria-expanded without command RPC. Four additional A/B desktop cases confirmed visible labels. Screenshots were inspected. CI passed 839 application and 113 QA tests in each Python 3.11/3.9 runtime (application skips 23/0; QA skips 2/17), plus 64 UI suites.

Normal opkg install verified 92 payload files/modes, actual dashboard110/ui82 over HTTP, fresh RPC and the preserved configuration/terms/routes. Encrypted backups before and after were independently reopened, decrypted and tar-read. The prior ON Auto was restored to RUNNING / OBSERVING; both WG1/OV2 passed fresh DNS + two HTTPS checks. No VPN reconnect. No new bandwidth test or physical failover was performed for this UI change; alpha33's actual speed-pause proof is retained separately. External LAN, reboot and long endurance remain unverified. Main/stable, MT6000 and Windows networking unchanged. [GitHub release metadata](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha34) records publication separately.

---

# Физическая проверка alpha34

На выделенном MT3000 установлена alpha34. В варианте C расширенное меню открывается иконкой с полной подсказкой и клавиатурной доступностью; ширина колонки и прокрутка проверены, пункты не перекрываются. В A/B и на телефоне сохранён текст. Auto после обновления снова работает, оба VPN проходят свежие проверки. Нажмите Ctrl+F5, чтобы загрузить новую страницу.
