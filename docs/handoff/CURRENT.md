# PLANNING CHECKPOINT — simplified UI / 26 October 2026

Start after reboot: [NEXT-AI-SIMPLIFIED-UI-2026-10-26.md](NEXT-AI-SIMPLIFIED-UI-2026-10-26.md).

Current owner request: preserve plans and three design mockups, save the feature branch to Gitea and GitHub before reboot. No new application implementation, device changes or 12-hour run started. Current execution proposal: [coordinator + three agents, up to 12 hours](../plans/AUTONOMOUS-12H-3-AGENTS-PLAN-2026-10-26.ru.md). The prompt inside that plan is for a future explicit start, not an active timer. Alpha25 product remains unchanged; all earlier delivery records below are history and not fresh commands.

После перезагрузки начать с указанного NEXT-AI: планы и макеты сохранены; автономная сессия ещё не запущена. Публикация checkpoint касается рабочей ветки, не main, релиза или роутера.

---

# COMPLETE alpha25 — all training action viewport / 25October2026

[GitHub alpha25](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha25) · [Gitea alpha25](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha25)

All internal training action redraws now preserve viewport: grading, Next/Back, chips, contents/results/table jumps, retry/restart, embedded course toggle and scene frames. A temporary height floor prevents collapse; shorter content keeps only required tail space. Meaningful focus restored without scrolling. Prior checkbox behavior retained: Change handler updates only answer selection and existing Check-answer disabled state; no course/question DOM redraw, no navigation/scroll/focus change. Disabled action guard evaluates current selection. Poll focus restoration prefers exact retained control instead of first otherwise-identical checkbox. Grading,11questions, first-attempt scores, wrong-only retries and stale/double-action guards preserved. Training invokes no router RPC.

Exactsource87a3439b766fe6fab1bfbd1bb7f4d02ac089ee54 dualCI778application/112QA each/57UI PASS (complementary skips in QA). All11questions/8lessons EN/RU complete action-position matrix including grading, navigation, results/retries, shrink-at-bottom and scenes with browser-removal scroll/focus simulation passed. Same regression executed against exact canonical Linux module101 matching installed HTTP/HTTPS bytes; WindowsCRLF working copy not mistaken for canonical byte identity. No production change was needed for that private proof adjustment. Canonical856917bytes SHA38b377ad2e3522405450942e5f918f565b90ac2f6abdc825302b4c03022f8d3a.

DedicatedMT3000alpha25/dashboard101/ui72/87immutablefiles+modes/RPC/HTTP/pinnedHTTPS passed. AutoONconfirmedreserve,bothVPNDNS/HTTPShealthy.2046closedoldlatencyrows,all6speedresults,35ownoptions/terms retained except expected native_trial/native_untilupdatelifecycle.193-entrypre/postencrypted backups independentlydecrypted/read. No new speed/fault test. ActualOFF/ONhomeaccess correct with incomplete setup flags untouched. No mainMT6000/hostnetwork/firmware changes. Native browser clicks/layout NOT_VERIFIED; do not claim automated generated-module proof as native browser acceptance.

Refresh browser once to load module101/style72, then checkbox changes stay in place. Keep gateway127.0.0.2:8080/designpreview64171 alive. Primaryreleasetagd0fc7dd82d15d5910fc8f4365eb633c1194fbd3a;publictag0533bf41dafff2db8824ffcd95d0fd42fb53a01b;equalreleaseTree9a7c22e864511ab1c3c0989890e6e30c799bc6bb. Actual non-draft prereleases/fourassets each downloaded/SHAverified. Docs-only branch closure in private/learn-actions-alpha25-20261025/publication.json.

Continuation: docs/handoff/LEARN-ACTIONS-TASK-2026-10-25.md;docs/VERIFICATION-ALPHA25-2026-10-25.md;qa/LEARN-ACTIONS-ALPHA25-2026-10-25.json;qa/MT3000-ALPHA25-2026-10-25.json. Private learn-actions-alpha25-20261025/FINAL.json;driver alpha25-install-20261025. No remaining implementation/publication/device work for this all-buttons viewport request. Never rerun completed device/backup steps blindly. Save new owner requests immediately.

# ALPHA25 INSTALLED — publication next

Owner all-training-actions viewport fix implemented: shared learnKeepViewport covers grade/navigation/contents/results/retry/restart/scenes/embedded toggles. Existing checkbox behavior: no course redraw on selection, same question/DOM/hash/scroll/focus retained; dynamic Check button availability and stale-action guard, exact retained-control focus on polling. Exactsource4811e3c7e7ee0070fee913bf7d6d783f7780d86b, dualCI778app/112QA each/57UI PASS. Canonical856917bytes SHA38b377ad2e3522405450942e5f918f565b90ac2f6abdc825302b4c03022f8d3a. All11questions/8lessons EN/RU action-position matrix repeated on canonical Linux module101 matching installed HTTP/HTTPS bytes; Windows CRLF working copy is not mistaken for canonical bytes. Native browser clicks NOT_VERIFIED.

MT3000alpha25/dashboard101/ui72/87files+modes/RPC/HTTP/pinnedHTTPS passed. AutoONconfirmedreserve,bothVPNhealthy;2046closedoldlatencyrows,all6speedresults,35ownoptions/terms preserved except expected native_trial/native_until lifecycle.193pre/postencrypted backups independently read. No new speed/fault test, mainMT6000/hostnetwork/firmware changes. ActualOFF/ON home access still correct with incomplete flags untouched.

Next evidence commit, publish_refs.py/publish_releases.py with LEARN-ACTIONS-ALPHA25 QA, verify4assets/server and docs-only closure. Private learn-actions-alpha25-20261025;driver alpha25-install-20261025. Do not rerun completed device steps. See docs/handoff/LEARN-POSITION-TASK-2026-10-25.md;docs/VERIFICATION-ALPHA25-2026-10-25.md. Keep gateways.

# ACTIVE alpha25 all training buttons

Owner extends checkbox-only fix to Check answer and all internal buttons. Shared learnKeepViewport now protects every course redraw, grading/navigation/results/retry/restart, Help expansion/collapse and scene frame updates. Saves viewport and semantic focus; prevents height collapse and retains only required space if a shorter document would clip saved scroll. Dynamic action/score guards unchanged. Focused EN/RU action matrix and prior tests passed. Next57UI/dualCI/new101+73build/MT3000/verified GitHub+Gitea delivery. Baseline physical/public24 complete. Private learn-actions-alpha25-20261025; LEARN-ACTIONS-TASK-2026-10-25.md. Native GUI unverified.

# COMPLETE alpha24 — quiz checkbox position / 25October2026

[GitHub alpha24](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha24) · [Gitea alpha24](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha24)

Owner Help/training checkbox jump fixed. Change handler updates only answer selection and existing Check-answer disabled state; no course/question DOM redraw, no navigation/scroll/focus change. Disabled action guard evaluates current selection. Poll focus restoration prefers exact retained control instead of first otherwise-identical checkbox. Grading,11questions, first-attempt scores, wrong-only retries and stale/double-action guards preserved. Training invokes no router RPC.

Exactsource87a3439b766fe6fab1bfbd1bb7f4d02ac089ee54 dualCI778application/112QA each/56UI PASS (complementary skips in QA). All11questions EN/RU select/deselect/bursts with browser-removal scroll/focus simulation passed. Same regression executed against exact canonical Linux module100 matching installed HTTP/HTTPS bytes; WindowsCRLF working copy not mistaken for canonical byte identity. No production change was needed for that private proof adjustment. Canonical856098bytes SHA9cb411017f9c38e7092030b3a523a01477f9abab5af10ecea7a08bdc7f541c20.

DedicatedMT3000alpha24/dashboard100/ui72/87immutablefiles+modes/RPC/HTTP/pinnedHTTPS passed. AutoONconfirmedreserve,bothVPNDNS/HTTPShealthy.2001closedoldlatencyrows,all6speedresults,35ownoptions/terms retained except expected native_trial/native_untilupdatelifecycle.193-entrypre/postencrypted backups independentlydecrypted/read. No new speed/fault test. ActualOFF/ONhomeaccess correct with incomplete setup flags untouched. No mainMT6000/hostnetwork/firmware changes. Native browser clicks/layout NOT_VERIFIED; do not claim automated generated-module proof as native browser acceptance.

Refresh browser once to load module100/style72, then checkbox changes stay in place. Keep gateway127.0.0.2:8080/designpreview64171 alive. Primaryreleasetag01fdcd81da4f7415897cf558a9d2c3fb32b2be46;publictage7a06764898f01698f0b12cc0af95deeb616457c;equalreleaseTree05b65fa491c57787c253ba397c60d8d9412af8ec. Actual non-draft prereleases/fourassets each downloaded/SHAverified. Docs-only branch closure in private/learn-position-alpha24-20261025/publication.json.

Continuation: docs/handoff/LEARN-POSITION-TASK-2026-10-25.md;docs/VERIFICATION-ALPHA24-2026-10-25.md;qa/LEARN-POSITION-ALPHA24-2026-10-25.json;qa/MT3000-ALPHA24-2026-10-25.json. Private learn-position-alpha24-20261025/FINAL.json;driver alpha24-install-20261025. No remaining implementation/publication/device work for this checkbox request. Never rerun completed device/backup steps blindly. Save new owner requests immediately.

# ALPHA24 INSTALLED — publication next

Owner checkbox-position fix implemented: no course redraw on selection, same question/DOM/hash/scroll/focus retained; dynamic Check button availability and stale-action guard, exact retained-control focus on polling. Exactsource87a3439b766fe6fab1bfbd1bb7f4d02ac089ee54, dualCI778app/112QA each/56UI PASS. Canonical856098bytes SHA9cb411017f9c38e7092030b3a523a01477f9abab5af10ecea7a08bdc7f541c20. All11questions EN/RU regression repeated on canonical Linux module100 matching installed HTTP/HTTPS bytes; Windows CRLF working copy is not mistaken for canonical bytes. Native browser clicks NOT_VERIFIED.

MT3000alpha24/dashboard100/ui72/87files+modes/RPC/HTTP/pinnedHTTPS passed. AutoONconfirmedreserve,bothVPNhealthy;2001closedoldlatencyrows,all6speedresults,35ownoptions/terms preserved except expected native_trial/native_until lifecycle.193pre/postencrypted backups independently read. No new speed/fault test, mainMT6000/hostnetwork/firmware changes. ActualOFF/ON home access still correct with incomplete flags untouched.

Next evidence commit, publish_refs.py/publish_releases.py with LEARN-POSITION-ALPHA24 QA, verify4assets/server and docs-only closure. Private learn-position-alpha24-20261025;driver alpha24-install-20261025. Do not rerun completed device steps. See docs/handoff/LEARN-POSITION-TASK-2026-10-25.md;docs/VERIFICATION-ALPHA24-2026-10-25.md. Keep gateways.

# ACTIVE alpha24 checkbox position

Owner reports Help training checkboxes scroll to top. Removed whole-course redraw from change handler; update only chosen answers and Check answer enabled state in place. Navigation disabled guard evaluates current selection, stale/double-action guards retained. Next regression/CI/new100+72build/MT3000/GitHub+Gitea. Baseline physical/public23 complete. Private learn-position-alpha24-20261025; LEARN-POSITION-TASK-2026-10-25.md.

# COMPLETE alpha23 — actual live speed graphs / 25October2026

[GitHub alpha23](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha23) · [Gitea alpha23](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha23)

Owner request implemented: two primary/reserve panels with real interval download/upload, green/blue, elapsed seconds, concrete server and explicit phase. Tests remain sequential/quotabound, waiting clear.128point/profile RAM traces(max8profiles), new read-only speed_live RPC,1s single-flight polling on active test section only. Old completed averages separate closed history. Missing/error/cancel directions not zeros; stale/otherjob/profile frames cannot contaminate current graph. Existing TLS/device-route/quota guards retained.

Final exactsource20ebcfd68f2dba279b96840248f6f579f5e9dfca dualCI778application/112QA each(runtimecomplementaryskipsretained)/55UI PASS;19focusedLinuxspeedtests include real local HTTP transfers, aggregation/bounds/job isolation. Initial ee4f63b CI failed only stale explicitreadACLtest expectation; updated speed_live test-only, production package unchanged. Canonical855870bytes SHA5b0c343f390b7040feef4df4285ab212ba69e5f0986114fb5e049e0575416324.

DedicatedMT3000alpha23/dashboard99/ui71/87immutablefiles+modes/RPC/HTTP/pinnedHTTPS passed. Actual bounded speed test bothVPNs passed:6realRPCframes,4RUNNINGframes with rendered points; primary4download/2upload,reserve7download/3upload. Four old speed results retained, six after test.8MiB/channel payload budget reserved, protocoloverheadextra. Test did not change app/network config. AutoONconfirmedreserve/bothVPNDNS/HTTPShealthy.1974closedoldlatencyrows,35ownoptions/terms preserved exceptexpectednative_trial/native_untilupdatelifecycle;193-entry pre/postencrypted backups independentlydecrypted/read. ActualOFF/ONhomeaccessverified without fake setupflags. No mainMT6000/hostnetwork/firmware changes.

Actual frames rendered in real UI model; native browser visual/click proof NOT_VERIFIED. No newLAN/power-loss proof claimed. Keep gateway127.0.0.2:8080 and prototype64171 alive. Refresh existing browser page to load module99/ui71. Primaryreleasetag7c91703929d343df3a825e24368fa7e712b42de6;publictag402c42683f56f736cbe2c0704d78d6e56691d5ff;equalreleaseTree409d1872ba9327e36811f95e838defa613bb1845. Actual non-draft prereleases/fourassets each downloaded/SHAverified. Docs-only branch closure in private/speed-live-alpha23-20261025/publication.json.

Continuation: docs/handoff/SPEED-LIVE-TASK-2026-10-25.md;docs/VERIFICATION-ALPHA23-2026-10-25.md;qa/LIVE-SPEED-ALPHA23-2026-10-25.json;qa/MT3000-ALPHA23-2026-10-25.json. Private speed-live-alpha23-20261025/FINAL.json;driver alpha23-install-20261025. No remaining implementation/publication/device work for this speed request. Do not rerun completed tests/installations blindly: real test spent quota and added legitimate results. Save new owner requests immediately.

# ALPHA23 INSTALLED — publication next

Owner live speed request implemented: measured download/upload progress, two primary/reserve graphs, explicit sequential waiting, bounded128point/profile RAM traces, read-only speed_live1s single-flight polling; old averages collapsed. Exactsource20ebcfd68f2dba279b96840248f6f579f5e9dfca, dualCI778app/112QA each/55UI PASS;19focusedLinuxspeedtestsPASS. Initial stale ACL allowlist expectation updated test-only; production package unchanged. Canonical855870bytes SHA5b0c343f390b7040feef4df4285ab212ba69e5f0986114fb5e049e0575416324.

MT3000alpha23/dashboard99/ui71/87files+modes/RPC/HTTP/pinnedHTTPS/AutoONreserve/bothVPNhealthy. Actual bounded test passed:6RPCframes/4RUNNINGframeswithpoints; primary4down/2up,reserve7down/3up. Four prior speed results retained, six aftertest;8MiB/channel reserved, no speed-setting/network changes.1974closedoldlatencyrows preserved;193pre/postencryptedbackups independentlyread. Nativevisual NOT_VERIFIED; actual frames rendered via real UI model, no fake samples written to device. No mainMT6000/hostnetwork changes.

Next commit evidence, publish_refs.py/publish_releases.py with LIVE-SPEED-ALPHA23 QA, verify4assets/server, docs-only closure. Private speed-live-alpha23-20261025;driver alpha23-install-20261025. Do not rerun completed install or live test; it spent quota legitimately. Keep gateways. See docs/VERIFICATION-ALPHA23-2026-10-25.md and qa/LIVE-SPEED-ALPHA23-2026-10-25.json.

# ACTIVE alpha23 live speed graphs

Owner wants real-time download/upload for both channels. See SPEED-LIVE-TASK-2026-10-25.md, private/speed-live-alpha23-20261025. Alpha22 remains physical/public baseline until delivery.

# COMPLETE alpha22 — combined13 owner tasks / 25October2026

[GitHub alpha22](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha22) · [Gitea alpha22](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha22)

All13tasks from BATCH-TASKS-2026-10-25.md implemented together and delivered. Language preserves actualpage/mode; single power button cancels pending Start/stops Auto, including wizard, handles late responses/lost Stop reply; no separate emergency section/forecast/archive-role block. Four preparation columns and clear independent-boot startup wording. Latency series/currentroute clarified, eight notes collapsed. Wizard native checkbox/typography/spacing fixed. Long journal/history sentences plain; short blue code/state links underline only hover/focus. Explicit simplified entry resets top, normal refresh retains scroll; Advanced menu label.

Exact tested source27a0280267d0a7d07ecb0e5092a5fc58d1c18cff:774application/112QA each runtime,54UI primary, complementary skips in QA. Canonical850115bytes SHAfaf4ee1e218dbc70d2810784404727b640510ae9803f9ccd84a2a98fee3307ca. PhysicalMT3000alpha22/dashboard98/ui70/87immutablefiles+modes/RPC/HTTP/pinnedHTTPS verified. AutoONconfirmedreserve,bothVPNDNS/HTTPShealthy;1881closedoldlatencyrows,35ownoptions/terms retained except expected native_trial/native_until lifecycle.193-entry encrypted backups before/after independently decrypted/read. ActualOFF/ON home access verified with setup flags unchangedfalse. No mainMT6000/hostnetwork/firmware changes.

Native browser layout/hover/click remains NOT_VERIFIED; do not confuse automated/source/CSS proof with native visuals. No new traffic-fault/power-loss/LAN-witness acceptance claimed. Keep gateway127.0.0.2:8080 and prototype64171 alive. GUI module names are98/70; do not reuse cachedalpha21. Primary canonical release/tag7881db0ca2ba3412bd2db838278ec53056694d5d;publictag4db626152874d9e6d36e507dc7c5e15908bbd842;equalreleaseTree5c547ea4c3a11c0220e3069c7b037dd5c46d93b6. Actual non-draft prereleases, four assets each downloaded/hashverified. Branch docs-only closure is recorded privately in private/batch-alpha22-20261025/publication.json.

Continuation: docs/handoff/BATCH-TASKS-2026-10-25.md; docs/VERIFICATION-ALPHA22-2026-10-25.md; qa/OWNER-BATCH-ALPHA22-2026-10-25.json;qa/MT3000-ALPHA22-2026-10-25.json. Private batch-alpha22-20261025/FINAL.json, driver alpha22-install-20261025. No remaining implementation/publication/device work for this13-task batch. Historical partial scopes remain explicitly partial. Never rerun completed installation/backup or non-idempotent prepare scripts blindly. Save new owner requests immediately.

# ALPHA22 INSTALLED — publication next

All13 owner tasks implemented together. Exact-source 27a0280267d0a7d07ecb0e5092a5fc58d1c18cff, canonical850115bytes SHAfaf4ee1e218dbc70d2810784404727b640510ae9803f9ccd84a2a98fee3307ca; dualCI774app/112QA each/54UI PASS. MT3000alpha22/dashboard98/ui70/87files+modes/RPC/HTTP/pinnedHTTPS verified; AutoONconfirmedreserve and bothVPNhealthy. 1881closedoldlatencyrows/settings/terms retained;193entrypre/postbackups independentlyread. Native browser visual NOT_VERIFIED. No mainMT6000/host-network changes.

Next commit evidence, publish_refs.py/publish_releases.py, verify4assets/server, docs-only closure. Do not rerun completed device steps. Private continuation: private/batch-alpha22-20261025; driver private/alpha22-install-20261025. Handoff docs/handoff/BATCH-TASKS-2026-10-25.md; reports qa/OWNER-BATCH-ALPHA22-2026-10-25.json,qa/MT3000-ALPHA22-2026-10-25.json. Keep gateway127.0.0.2:8080 alive.

# ACTIVE: combined owner batch alpha22 / 25 October2026

All13 tasks accepted; implementation and joint verification in progress. No intermediate publication or router update. Tasks01–13 source edits present; next: regression tests, bilingual generated documentation, one canonical build/exact dual CI, dedicated MT3000 backup/normal Stop/update/Start/reserve, GitHub and Gitea prereleases. Physical/published baseline remains alpha21 until verified delivery. Private continuation: private/batch-alpha22-20261025. No new GUI visual proof yet.

# COLLECTING OWNER BATCH —25 October2026

Latest owner directs about15 sequential tasks, immediate persistent list/rephrasing and response ready for next. Do not build/publish/install interim changes. One combined delivery after owner finishes the list. Primary list: docs/handoff/BATCH-TASKS-2026-10-25.md. Task01: language switch preserves actual section/full-simple mode, local implementation and two targeted Node suites passed, no full CI/build/install yet. Current physical/public alpha21 remains baseline; private gateways keep running. Local uncommitted source/WIP includes temporary regenerated dashboard97, so create proper new module/version before final combined build; never overwrite published21 payload. No device/package writer active. Receive and save next task now.

# COMPLETE alpha21 / owner77 —25 October2026

[GitHub alpha21](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha21) · [Gitea alpha21](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha21)

Latest owner rule supersedes earlier setup-gated display access. Enabled Auto always permits simplified view independently of setup/test markers. Off/unconfirmed button red with tooltip on hover/focus/tap, Escape dismisses; unavailable click only explains and never starts Auto. Actual controller start protection unchanged. Running Auto skips only unfinished-wizard entry; existing current-terms gate remains. Missing channels/faults/handovers display honestly rather than denying entry. Auto21power/menu controls retained.

Final4ae700097b3b921d9cf7b396e98f661fd18c8f7c dualCI774app/112QA each/52UI PASS. Two earlier fixture CI failures retained: f004055global Popen/UCI cache expiry; f9589fb wrong patch target (local import). Corrected retention_settings fixture,28targeted native tests each runtimePASS. Runtime package unchanged across test fixes:849653bytes SHAcaadfa384d048c384f3efc3ca9f27dcf9e019420a77879d187cd13581865d29e.

MT3000alpha21/dashboard97/ui69/87files/modes/RPC/HTTP/pinnedHTTPS passed. ActualOFF during normal installation denied access and supplied tooltip; actualON after Start/reserve enabled access with setup_complete/onboarding_complete stillFALSE. No fabricated completion flags, projections or synthetic observations. AutoONconfirmedreserve/bothVPNhealthy;1729closedoldlatencyrows/4speedresults/settings/terms1 retained,193-entry pre/post encrypted backups independently decrypted/read. No hostnetwork/mainMT6000 changes. Native-browser visual NOT_VERIFIED; no Computer Use this turn. Keep actualgateway127.0.0.2:8080/designpreview64171 running; normal entry now shows home under ON even when wizard unfinished.

Canonical release/tagc54ccd42efbf95f41f1609e448bde333a9e856ed;public7ab8fb6a85812ecb4ea1cfc4078fdd7c1b6386cf;equalTree60dbddd08d752870b3c6b6729a60d1eb619b46c4;both actual prereleases/four downloads eachverified. Docs-only branch closure will be recorded privately in auto-access-alpha21-20261025/publication.json. Read docs/VERIFICATION-ALPHA21-2026-10-25.md and qa/AUTO-ACCESS-ALPHA21-2026-10-25.json,qa/MT3000-ALPHA21-2026-10-25.json. Never rerun completed device steps or source/prepare scripts blindly. No remaining owner77 work. Save new requests immediately; source/task history below may describe earlier superseded gates.

# ALPHA21 INSTALLED / PUBLICATION NEXT — owner77

Latest rule implemented: confirmed enabled Auto grants display access regardless of setup/tests markers; off/unconfirmed red shortcut with hover/focus/tap tooltip and Escape. Initial unfinished wizard skipped while AutoON without changing its markers. Missing-channel/transition/fault states rendered honestly. Real startup protections unchanged. Final4ae700097b3b921d9cf7b396e98f661fd18c8f7c dualCI774app/112QA each/52UI PASS. Two test-fixture CI failures retained;28targeted native tests passed in both environments, production package unchanged. Canonical849653bytes SHAcaadfa384d048c384f3efc3ca9f27dcf9e019420a77879d187cd13581865d29e.

Physical MT3000alpha21/dashboard97/ui69/87files/modes/RPC/HTTP/HTTPS passed. ActualOFF then actualON snapshots: off denies; on grants with setup_complete/onboarding_completeFALSE. No fake completion flags or synthetic observations. AutoONreserve/bothVPN healthy;1729closedoldlatencyrows/4speedresults/settings/terms preserved;193-entry pre/post encrypted backups independently read. Native visual NOT_VERIFIED, no Computer Use this turn. Keep both gateways. Next commit evidence, prepared publish_refs.py/publish_releases.py, verify assets then docs-only closure. Read docs/VERIFICATION-ALPHA21-2026-10-25.md and qa/AUTO-ACCESS-ALPHA21-2026-10-25.json,qa/MT3000-ALPHA21-2026-10-25.json. Do not rerun completed device steps.

# ACTIVE alpha21 / owner77

Latest owner rule supersedes setup-gated access: enabled Auto always permits simplified view even with unfinished setup/tests; off/unconfirmed shortcut red with hover/focus/tap tooltip and Escape. Source implemented with resilient missing-profile/transition/error rendering; real Auto startup protection unchanged. Next52UI/build/exact dualCI/normal MT3000 install/Auto reserve/real incomplete-marker home entry checks. Current physical20AutoONreserve. No Computer Use this turn. Private auto-access-alpha21-20261025; save new dictation immediately. Earlier strict-gate notes below superseded.

# COMPLETE alpha20 / owner76 —25 October2026

[GitHub alpha20](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha20) · [Gitea alpha20](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha20)

Owner76 complete: guarded «Упрощённый интерфейс» beside actual heading, current readiness and click-time validation, readable unavailable reason, correct lost-RPC message. Upper-left partial blue skip link fixed with full clipping before focus and fixed/unclipped keyboard focus; completed steps opacity1/foreground. Original strict terms/setup/current-pair/running Auto gate retained; no navigation RPC/config writes. Source tests EN/RU and generated route/header checks passed. Exact2ce089091eb6851af8741b604154979a71905eb9 dualCI774app/112QA each/52UI PASS. Canonical849731bytes SHA8947728ed475072e457bfb90ffdc90d4a62e989eab6c85d3c6ff627f45233bdf.

MT3000/4.11.0alpha20/dashboard96/ui68 installed;87files/modes/RPC/HTTP/pinnedHTTPS verified. AutoON confirmedreserve/bothVPN healthy;1644closedoldlatencyrows/4speedrows/settings/terms1 preserved,193-entry encrypted pre/post backups independently read. Actual setup_complete/onboarding_complete stillFALSE, header correctly disabled with «Сначала завершите первичную настройку». Ready transition tested against actual frame with completed flags only in memory, never persisted. Native-browser visual NOT_VERIFIED; no Computer Use attempted this turn, no physical button-click/layout claim. MainMT6000/hostnetwork unchanged. Keep gateway127.0.0.2:8080 and designpreview64171 running.

Canonical release source/tag174b4d551c44af984f83680a1bda04d66a5a42ab;public source/tag65926127a65583af3e2c02c3792065a80499bf36;equalTreeebb2b01b338d295b49bbfed80c1c0a06f7aa7952. Actual both prereleases/four assets each downloaded/hash verified. Final docs-only branch closure recorded privately in header-alpha20-20261025/publication.json. No remaining owner76 work. Alpha19 earlier GitHub/Gitea release also complete; old quota blockers below superseded. Read docs/VERIFICATION-ALPHA20-2026-10-25.md and qa/HEADER-ALPHA20-2026-10-25.json,qa/MT3000-ALPHA20-2026-10-25.json.

For nextAI: inspect live state/ledger before writes; never rerun completed install/prepare scripts blindly. Normal entry remains wizard until explicit setup completion. Do not auto-mark it complete; existing onboarding=defer recovery link opens full panel but never grants home readiness. To review header in full Getting started use http://127.0.0.2:8080/cgi-bin/luci/admin/services/homensai-vpn?onboarding=defer&lang=ru#start . New user requests save immediately. No old observer/app writer remains after closure.

# ALPHA20 INSTALLED / PUBLICATION NEXT —25 October2026

Owner76 implemented: guarded shortcut beside actual heading, clear reason if unavailable, current model and click-time recheck, lost-RPC copy; clipped skip link fixed without losing keyboard focus, done-step opacity1. Exact2ce089091eb6851af8741b604154979a71905eb9 dualCI774app/112QA each/52UI PASS. Canonical849731bytes SHA 8947728ed475072e457bfb90ffdc90d4a62e989eab6c85d3c6ff627f45233bdf.

MT3000alpha20/dashboard96/ui68/87files/modes/RPC/HTTP/pinnedHTTPS verified. AutoONreserve/bothVPNDNS+2HTTPS;1644closedoldlatencyrows/4speedrows/settings/terms retained,193-entry pre/post encrypted backups independently read. Stored setup/onboarding stillFALSE; header disabled reason is correct, completed projection in memory only. No native visual claim. No hostnetwork/mainMT6000 changes. Keep both local gateways. Read docs/VERIFICATION-ALPHA20-2026-10-25.md and qa/HEADER-ALPHA20-2026-10-25.json,qa/MT3000-ALPHA20-2026-10-25.json.

Next commit evidence and run prepared private/header-alpha20-20261025/publish_refs.py then publish_releases.py, verify both downloads, close owner76 and docs-only publish_closure.py. Do not rerun completed device steps. Alpha19 actual GitHub/Gitea releases already verified; old quota blockers below superseded. Source guards must remain unchanged after2ce0890. Native Computer Use not attempted this turn.

# ACTIVE alpha20 header/shortcut candidate —25 October2026

Owner76 recorded: clipped blue skip-link at upper-left and readable completed steps; guarded Simplified interface button beside actual heading. Source helper updates on draw/1s freshness and revalidates click; navigation only, no Auto/config writes. Original strict terms/setup/current-pair/running gate retained. alpha20/dashboard96/ui68; tests/build/CI/physical update next. Current physical19AutoONreserve, unfinished setup preserved. Alpha19 GitHub and Gitea releases now both published and four assets downloaded/hash verified; old API-blocker instructions below superseded. Private header-alpha20-20261025. No Computer Use actions this turn, previous visual limit remains. Keep router/design gateways running.

# ACTIVE owner76 / alpha20 header correction

Alpha19 GitHub release now published and all assets downloaded/hash verified; Gitea reverified. New owner76 recorded in TODO: clipped skip link and guarded top-right simplified-interface shortcut. Source in progress, not installed20. Current device19AutoONreserve/setup incomplete. Keep both gateways; no native Computer Use attempted this turn.

# ALPHA19 INSTALLED AND TESTED — GitHub release pending

Owner74 implementation/install/tests are complete with native visual limit. AutoON/confirmedreserve/bothVPN healthy;193-entry before/after backups,1545closedlegacy latency rows/4speed rows/settings/terms retained. Setup/onboarding completion FALSE preserved: correct first entry is the existing wizard. Do not mark it complete automatically. Projected ready-card test used actual data with completed flags in memory only.

ExactCI source3d759a889c71e771afd1b2747facd8c7539b00af,774app/112QA each/52UI;848531byteIPK SHA d0a79466a8e79afb948f5eeb17bb195d39b5be01e022f84218b02a50ccb715cd. ActualHTTP/HTTPS/87files/RPC/current-data semantics passed. Native browser visual NOT_VERIFIED: connected-browser inventory empty; alternate Computer Use could list Edge but stopped before any app input because current URL could not be confidently determined. Do not bypass/reset to evade that stop in the same turn.

Canonical/Gitea source/tag0d82f73da20eb1112da05c73ea8fb0de3150d75a,GitHub source/tag1332d3158b5fe40c3dbd88d57d2b09a1e3c378c0,equalTreead9ddfb6ddd42392c844aa40acf48665d8aeb151; both feature refs/tag verified through standard Git transport; main/stable unchanged. Actual Gitea non-draft prerelease with four downloaded/hash-checked assets: http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha19.

GitHub RELEASE WITH ASSETS IS NOT CREATED. RESTcore quota0,reset1792920908=2026-10-25 09:35:08UTC/10:35:08Berlin. Do not repeatedly poll limited endpoints. After reset, run private/simple-home-alpha19-20261025/publish_releases.py (idempotent existing Gitea assets) and verify downloads. DO NOT rerun publish_refs.py after docs closure because ledger source is fixed to0d82f73; feature code and tags already saved. Then record actual GitHub release link, close ownerTODO75, commit docs-only closure and run prepared publish_closure.py; it uses REST so wait until available. New local docs closure may be ahead of release refs, product must stay unchanged from3d759a8. Current ledger private/simple-home-alpha19-20261025/publication.json and FINAL.json.

Read docs/VERIFICATION-ALPHA19-2026-10-25.md and qa/SIMPLE-HOME-ALPHA19-2026-10-25.json,qa/MT3000-ALPHA19-2026-10-25.json. Keep actual router gateway127.0.0.2:8080 and preview64171 running. No old installation/VM observer remains. No hostnetwork/mainMT6000 changes. Restore tasks from this checkpoint; never rerun completed device steps blindly.

# ALPHA19 INSTALLED / PUBLICATION PENDING —25 October2026

Explicit owner requested build, physical installation and tests of the selected startup card. Implemented actual model/render/router-entry integration, existing power control forwarding, required terms/setup/current-pair/fresh Auto gate and stale-home watchdog. Source tests cover primary/reserve, incomplete/wrong/stale/pending evidence and generated deep-link/full-menu routing. Exact3d759a889c71e771afd1b2747facd8c7539b00af dualCI774app/112QA each/52UI passed. Canonical848531bytes SHA d0a79466a8e79afb948f5eeb17bb195d39b5be01e022f84218b02a50ccb715cd.

MT3000/4.11.0 alpha19/dashboard95/ui67 installed;87files/modes/RPC/HTTP8080/pinnedHTTPS verified. NormalStop16.093s/Start58.265s/reserve47.672s. AutoON confirmedreserve/bothVPNDNS+2HTTPS.1545closedoldlatencyrows/4speedresults/settings/terms1 retained,193-entry encrypted pre/post backups independently decrypted/read. No hostnetwork/mainMT6000 changes. Fresh source/data proof passed using actual current vendor/path/health models: saved setup_complete/onboarding_complete remainFALSE, so correct actual first entry is the existing wizard. In-memory-only completed flags render the ready card with actual bound profiles/addresses; NEVER saved to router. Do not claim completed master or native visual acceptance. Native browser inventory empty, visuals NOT_VERIFIED.

Read docs/VERIFICATION-ALPHA19-2026-10-25.md,qa/SIMPLE-HOME-ALPHA19-2026-10-25.json,qa/MT3000-ALPHA19-2026-10-25.json. Private proof simple-home-alpha19-20261025; driver alpha19-install-20261025. Never rerun completed install steps. Keep AutoONreserve, router gateway127.0.0.2:8080 and designpreview64171 running. Next commit evidence, run prepared publish_refs.py then publish_releases.py, verify both actual prereleases/assets, docs-only closure/publish_closure.py. Main/stable0.9.0 unchanged. OwnerTODO74 closes after delivery; no automatic setup acceptance.

# BUILDING alpha19 — selected startup card

Explicit owner authorized build/install/test. Source integrated actual models/routes/original controller button and fresh-state watchdog. All52UI initially passed; added generated-routing test passed after fixture bi injection. Current physical18AutoON but setup/onboarding markers false, preserve them: new entry must show wizard. No browser surfaces available. Next exact committed archive/build/CI, fresh verified backup/Stop/install/Start/restore reserve, actual served95/ui67/gate/frame/settings/history checks. Do not claim master completed or fabricate tests. Private simple-home-alpha19-20261025, ownerTODO74.

# ACTIVE DESIGN CANDIDATE: selected startup card —25 October2026

Owner approved Карточка, original project button under Auto status, red50%. New startup policy and prototype gates are implemented/tested locally: terms → complete setup/current pair → required pair-specific tests → fresh confirmed Auto/current path → home. Stop/stale/incomplete never show ready card; working reserve is accepted. Read docs/SIMPLE-HOME-2026-10-25.md and ownerTODO74. Production integration with actual RPC/entry routing/card and full acceptance is still pending; alpha18 installed/published baseline unchanged. New router/simple_home_policy.inc.js and test_simple_home_policy_ui.js are uncommitted candidate source; do not claim delivered or rebuild/retag18. Keep preview64171 and router gateway running.

# COMPLETE: alpha18 Help training and meaningful events —25 October2026

[GitHub alpha18](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha18) · [Gitea alpha18](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha18)

Owner72/73 completed together. Help directly after Settings has8lessons/11questions, explanations before answers, any-question/lesson navigation, checked/current/first-attempt statistics and wrong/unanswered-only retry preserving correct answers. Training does not control the router. All event/state labels open dictionary explanations; diagnostic causes separately linked, checks not falsely treated as switches, historical missing data never guessed.

Exact tested product76498b5db82e8f5fa25f22d946b338c26b39c869; dualCI774app/112QA each/50UI PASS. Canonical845457bytes SHA f38a7f8926a6e717841af5cac0d13dfda9207fa3e9338bde6f624fc7c88fc81f. Physical MT3000/4.11.0 alpha18 AutoON/confirmedreserve/bothVPNDNS+2HTTPS.87immutablefiles/modes/RPC/HTTP8080/pinnedHTTPS/newHelp/course/dictionary source/CSS verified; settings/terms1/918closedlegacy latency rows/4speedresults retained.193-entry encrypted pre/post backups independently decrypted/read. No synthetic physical data, speedtest or fault injected. Gateway127.0.0.2:8080 remains running; no hostnetwork/mainMT6000 changes.

Actual releases/assets downloaded/SHA256verified on both services. Canonicaltag/sourcec6f03ff98ace29f844011929b38620d3ed636a29;publictag/source12b716ce8ae9fd4377ec05a1e6044711e9f4b5a3;equalreleaseTreea2bdb8680ed1b751269a3fb8cdcaddb43b57d596. Documentation-only closure follows; no product changes, main/stable0.9.0 unchanged. Read docs/VERIFICATION-ALPHA18-2026-10-25.md,qa/EVENTS-HELP-ALPHA18-2026-10-25.json,qa/MT3000-ALPHA18-2026-10-25.json. Final branch closure identities are private/owner72-73-20261024/publication.json. No pending owner72/73 work. Native browser visuals NOT_VERIFIED; source/data/installed bytes are not native clicking. Alpha17 weeklyVM evidence remains separate/poweredoff, no newVMrequired forUI-only18. ExternalLAN/IPv6/KillSwitch/powerloss unverified.

For nextAI: inspect CURRENT.md and latest private ledger before acting. Do not rerun completed install/prepare/publication scripts blindly. Keep AutoONreserve and gatewayalive. Save new dictation immediately in ownerTODO; use standing owner install/publication authorization. Earlier candidate/active headers below are superseded.

# Alpha18 physically accepted —25 October2026

Owner72/73 complete in installed product: semantic clickable events and Help course (8 lessons/11 questions, scores, any-question navigation, wrong-only retry). Exact tested source76498b5db82e8f5fa25f22d946b338c26b39c869; dualCI774app/112QA each/50UI PASS. Canonical845457bytes SHA f38a7f8926a6e717841af5cac0d13dfda9207fa3e9338bde6f624fc7c88fc81f. Physical MT3000 alpha18 AutoON/confirmedreserve/bothVPNhealthy, 87files/modes/RPC/HTTP/HTTPS, settings/terms1/918closedlegacy latencyrows/4speedresults preserved,193-entry encrypted pre/post backups independently read. Native browser visuals NOT_VERIFIED. No new VM needed for UI-only18; alpha17 weeklyVM remains separate/poweredoff. Keep gateway127.0.0.2:8080 alive.

Next: commit release evidence, run private/owner72-73-20261024/publish_refs.py then publish_releases.py, verify both actual releases/assets; docs-only closure and publish_closure.py. Do not rerun completed installation steps. Current references in private/owner72-73-20261024/publication.json once created. No main/stable changes. Product source must remain unchanged from76498b5. New dictation saved immediately in owner TODO.

# VALIDATING alpha18 —25October2026 (owner72/73 started24October)

All50NodeUI suites PASS, including newjournal_semantics/learning_retry/help_learning EN/RU and existing history/terminal/scene/adversarial navigation. Sourcecandidate18/dashboard94/ui66 notdelivered. Source-generated490dictionaryentries/31topics perlocale/8lessons/11questions;9MD+manifest outputs synchronized. Next exactGitarchive canonicalLinuxbuild, recordSHA/kit and onefinaldualCI, then standingauthorized MT3000acceptance and combinedpublication. No newVMneeded forUIonly; weekly17 VMpoweredoff andphysical17AutoONreserve remainbaseline. Newprotocol/data/storageunchanged. GuardMeaning source/actor/history gaps neverguessed. Partialdictionary/learningtest failures were intentionalcontract mismatches and a missingresultquestionnav; corrected and newtestsPASS. Keep private/owner72-73-20261024/all-ui.json andpending-task record.

# CANDIDATE: owner72/73 alpha18 events/Help learning —24October2026

Bothimplemented beforedelivery. Candidate18/dashboard94/ui66, notinstalled/published. Eventtaxonomy32uniqueeventcodes/490mergeddictionaryentries: successfulcheck is notswitch; requests/preparation/application/confirmation/recovery/retainedreserve separated; event andstate linkdictionary, cause hasownlink; rawprovenance/search/grouping preserved; knowncurrentcontrollerliteralstates covered; legacy missing/conflictingrecords described honestly. Programmaticcommands notlabelledhumanclicks; retained-reserve transaction notglobalAutoOFF. Scopedlayout16+weekly17 preserved.

HelpvisibleafterSettingsinCalm too (CSSpreviouslyhidHelp); lazyembeddedcourse8lessons/11questions, explanations, anylesson/questionjumpincludingresult, firstattempt/current/checked/attemptstatistics, wrong/unanswered-onlyremediation retainingcorrectanswers, incompletecoursecannotpass, staleactions guarded. NewNodejournal_semantics/learning_retry/help_learning tests PASSENRU; oldjournal/history/learn/scenes/help focusedPASS afterintentionalcopycount/rawunknown assertionsupdated. TrainingneverRPC. Addedsource-generatedTRAININGen/ru;syncoutputs9MD+manifest=10,31Helptopics/locale,490codes; normativeTerms1/licencesunchanged. Sourceversionjustbumped; full50UI/dualCI/canonicalartifact/actualMT3000/publishing stillpending. Sourceonlyfrontendexceptversionmetadata, no newbackendstate/storageAPI.

Lastcompletebaseline17: actualMT3000AutoONreserve/bothVPNhealthy,193entrybackups,824closedoldlatencyrows/4speedrows preserved; weeklyVMoffexit0.17publishedGitHub/Gitea,canonicalclosurea31f88b3/public196db6a8 equalTreece13627c. Private72/73tasks savedimmediately,nowinownerTODO. Keep usergateway127.0.0.2:8080alive. Next: allUI/full exactCI+canonicalLinux build fromcommittedarchive (onefinalCI afterrecordSHA), review/sourceguards, dedicatedMT3000 backup/normalStop/install/Start/reserve/read-onlyUI/dictionary/course/legacydata checks, combinedfeature/prerelease delivery. No newVMneededforUIonlyunlessnewfailure; nativebrowseravailability previouslyempty, no visualclaim. Old privateprepare scripts are non-idempotent; do notrerunblindly.

# ACTIVE: owner72/73 event semantics and Help training —24October2026

Latest owner72: meaningless«OK» row must say exactevent/state and open an explanation linked to dictionary; no false switch/unknown assertions. Owner73: Help immediately after Settings, explanation→question flow, jumpanylesson/question, finalscore/statistics and retrywrongonly. Bothsaved immediately in private/owner72-73-20261024/PENDING-OWNER-TASKS.json and ownerTODO. Finishboth before nextcandidatealpha18/delivery, usingstandingauthorization.

Alpha17 prior task is COMPLETE: actual prereleases/tags/assets onGitHub/Gitea verified, canonicalclosurea31f88b3f5a85f4abf7e8b0fc2ef8c837d0fe8f0/public196db6a86738d82b4826fc3313d21a404d2f084d equal treece13627c4cdb1ba56ad91cbdc1eaa23ebcf07a2c. Primarysave240stimeout was safelyrecovered: importedbundle/branchverified, sameofficialgitflowSAVED,tagverified; incrementalclosurekeepspriorverifiedfullbundle. See private/latency-alpha17-20261024/publication.json and primary-save-timeout-recovery.json. Physicalalpha17AutoONreserve/bothVPNhealthy,193entrybackups,824legacyclosedlatencyrows and4speedrows preserved; VMoff0. No oldobservers toresume. Keepgatewayalive and no hostnetwork/mainMT6000 changes.

Relevant source: journal_panel.inc.js journalRows/journalMessage/renderEventHistory, live_terminal.inc.js terminalLine/updateLine; error_table/error_rows_extra/summary showErrorCode. OKmonitor events emitted when a profile first appears or itscodechanges toNone; this onlymeans a probe observed noerror, not a traffic switch. Preserve rawprovenance and do not infer oldroles/actors from today'spair. ExistingrenderLearn has8lessons/8questions, lessonchips but noquestionjump/wrong-onlyretry. Mainnav alreadyincludesHelp/Training afterSettings incompiled93, but screenshot15cached; strengthenHelp landing/course entry and currentstate explanations, notduplicate conflictingcourse. Current quizorange=reserve isvalid, legendwronglyclaimsprimaryout evenmanualreserve; fixwording. Need specific tests for semantic/registry coverage and quizjump/retry/scores/staleactions; no sourcechanges made yet for72/73.

# COMPLETE: owner71 weekly latency alpha17 delivered —24October2026

[GitHub alpha17](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha17) · [Gitea alpha17](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha17). Actualnon-draft prereleases,fourassets/server downloaded/SHA256verified;canonicaltag/source1b8296d8a1f09d1925299023d8cc1d63bee2ef43 /publictag/sourcea4ed7b7cd582944e59b772606b745ec5f63eba58,identicaltreebde07c49a7760c4d83ff8e132211df5db426f3b0. Main/stable0.9.0/oldreleases unchanged. Exact01b5740d8a8771881d95b26f2922a80d76457581 dualCI774app/112QA each/47UI PASS. Canonical832683bytes SHA344c60ab5eaa9dc3f8cf1ddb1bddf19500c189dce3d2264d24f1ecff36425102. Productunchanged afterfinalCI; docs-onlyclosure follows.

Feature: realconfigured1–7daylatency/MAX10081minute/2MiB,1–168hwindow/weekpan,label«Просмотрпоследних7суток»,datedwideaxes,720markers/channel,allretained-minute lines/stats,oldschema1checkpoint compatibility. Fullweekrows_json+rows_count andlegacy1441tail avoid largeRPCarrayfailure; frontend850kchar/shape/count guards. No fabricatedpastdays, no routing/probeRPC fromsliders. Olddeletedhistory cannotreturn.

Newactualx86VM installed17/87files/RPC/HTTP; trackedfinalproofPASS10081rows/685748filebytes/707573compactRPCbytes,1dayprune/no-backfill,statusrestored/AutoOFF/workerfinished; VM e48ea670f9fc7f2039adeaafda10b3675cde8c44f2574fbbc3e8b4c94d710f16 offexit0. RawRPCtimeout7,unregisteredobject4,interactiveopkg/longserialtimeouts retained/resolved by compactfreshregistration/closedstdin/trackedjob. No GLidentityspoof or nativequalification claim.

ActualMT3000/4.11.0alpha17/dashboard93/ui65,AutoON/confirmedreserve/bothVPNDNS+2HTTPS.87files/modes/RPC/actualHTTP8080+pinnedHTTPS/new7dayAPI/UIverified; encryptedprebackup compared824closedoldlatencyrows preserved (825oldfile→829newatcheck), currentobservationsonly/no syntheticweekdata. Settings/terms1/4speedrows retained,193before/193afterencryptedbackups independentlydecrypted/read. NormalStart59.359s,reserve41.14s. No Windowsnetwork/mainMT6000/physicalfault/newspeedtests.

Read docs/VERIFICATION-ALPHA17-2026-10-24.md,qa/LATENCY-ALPHA17-2026-10-24.json,qa/MT3000-ALPHA17-2026-10-24.json. Privateevidence private/latency-alpha17-20261024 and private/alpha17-install-20261024. Nativebrowservisual/externalLAN/IPv6/KillSwitch/powerloss remainunverified. LeaveAutoONreserve/usergateway127.0.0.2:8080alive. UserCtrlF5/#channels loadsnew93module. Newdictationrecord immediately; neverrerun privateprepare/rewrites/completedinstall scripts blindly. Earlier activeheadersbelow superseded; no pendingVMobserver/appwriter.

# READY FOR PUBLICATION: alpha17 weekly latency physically accepted —24October2026

Exact01b5740d8a8771881d95b26f2922a80d76457581 dualCI774app/112QA each/47UI PASS. Canonical832683bytes SHA344c60ab5eaa9dc3f8cf1ddb1bddf19500c189dce3d2264d24f1ecff36425102. True1–7daylatency storage/MAX10081minute/2MiB,1–168hwindow/weekpan,datedaxes,720markers/channel,all-minute lines/statistics,oldschema1checkpoints,compactfullweekrows_json pluslegacy1441tail; no backfill or routing/probeRPC fromslider.

Newactualx86VM installed17verified87files/RPC/HTTP; finaltrackedjobPASS10081rows/685748filebytes/707573compactRPCbytes,1dayprune/no-backfill,statusrestored,workerfinished; VM e48ea670f9fc7f2039adeaafda10b3675cde8c44f2574fbbc3e8b4c94d710f16 offexit0. RawRPCtimeout7,unregisteredobject4,opkginteractive/longserial harness timeouts retained/resolved by compactfreshregistration/closedstdin/trackedbackgroundproof. NoGLidentityspoof or synthetic physicaldata.

MT3000alpha17/dashboard93/ui65,AutoONreserve/bothVPNDNS+2HTTPS;87files/modes/RPC/HTTP8080+pinnedHTTPS/newweekAPI/oldclosedlatencyrows/settings/terms1/4speedrows/backups verified. Read docs/VERIFICATION-ALPHA17-2026-10-24.md,qa/LATENCY-ALPHA17-2026-10-24.json,qa/MT3000-ALPHA17-2026-10-24.json. Privateevidence private/latency-alpha17-20261024 and private/alpha17-install-20261024. NextstandingauthorizedcombinedGitHub/Giteafeature/prerelease then docs-onlyclosure. Keepusergateway/AutoONreserve. Earlier activeheaders below are superseded; never rerun completed steps blindly.

# ACTIVE: owner71 weekly latency alpha17 —24October2026

Owner71 wants label/slider for7days. Candidatealpha17/dashboard93/ui65: true1–7day retention per operator setting,1–168h window,7daypan/datedaxes, schema1checkpoint compatibility, MAX10081minute rows/2MiBfile. Legacydaily tail plus completeweek rows_json reduces RPC array overhead; frontend validates850kchar/10081row/count bounds; graphmarkers<=720perchannel, lines/stats keep observedminute data, gaps/no backfill. Existing7Python+3new week/storage/size tests PASS10; extendedLatencyUI weekly/control/codec/marker tests PASS. Production16 remainsAutoONreserve,4speedrows.

New actualx86VM e48ea670f9fc7f2039adeaafda10b3675cde8c44f2574fbbc3e8b4c94d710f16 is running,networknone/no mounts/ports/privileges. In private/latency-alpha17-20261024:01raw10081arrayRPCfixture failedexit7timeout;02compact test exited4unregisteredobject (not format acceptance);03freshregistrationcompact retest running. Fixture only VM status restored/monitor restarted, nativeOFF/noGLidentityspoof. Need finish/retain failures, install canonical17inVM, actualweekfile/RPC/restore checks, controlledVMshutdown. Never fabricate week data on physicalMT3000.

Next canonicalGitarchiveLinuxbuild, recordSHA/kit, finalexactCI (first build needs no preliminaryfullCI), realVMacceptance, backup/normalStop/install/Start/reserve/legacydata+7dAPIreadback on dedicatedMT3000, combinedGitHub/Gitea delivery. Source not delivered. Oldalreadypruned days cannot return. Source handoff has earlier16complete below; privateACTIVE is owner71. Keep loopbackusergateway alive; no hostroutes/mainMT6000 changes.

# COMPLETE: owner70 saved-history layout alpha16 delivered —24October2026

[GitHub alpha16](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha16) · [Gitea alpha16](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha16). Actualnon-draft prereleases,fourassets/server downloaded/hashverified. Canonicaltag/sourceea9685bbf22b98c43380d9c928d9467ac5aacd66 andpublictag/source7161e9f2180ba291ab2fd325eca09d0d1bfc076b,identicaltree98f5d61ee2ebf2aa6849e696ceca7d99229e5992. Main/stable0.9.0/oldtags unchanged. Exacte7609c981cb108a4fc79439d2b11368c1161e795 dualCI771app/112QA each/47UI PASS; canonical831904bytes SHA913acd14de698b1898d7333cc20a788c14b75e2abdebc9354054f0d0807989d9.01207a3 cache-dependent testfixturefailure retained; test-onlyisolationfixed,5focusedcasesandfullCI passed, product/guardsunchanged.

CSSonlyfeature: saved-historyDate15%,State27%,Event58%,min880px/existinghorizontal scroll. M/R diagramblockbeforeunbrokenstatecode; eventdata/search/sort/disclosure/livejournalunchanged. Nativebrowserinventoryexposednoapps/browsers, no visualclaim; sourceCSS/actualservedbytes verified.

MT3000/4.11.0 alpha16/dashboard92/ui64,AutoON/confirmedreserve/bothVPNDNS+2HTTPS.87immutablefiles/modes,RPC,HTTP8080/pinnedHTTPS,CSSreadback,settings/terms1preserved.4successfulspeedrows,manualspeedON/auto-newOFF retained. NormalfirstStart64.672s,reserve41.281s; independentlydecrypted/read193before/193afterencryptedbackups. No new speedtest/fault/Windowsnetwork/mainMT6000changes. LeaveAutoONreserve/usergateway127.0.0.2:8080alive.

Read docs/VERIFICATION-ALPHA16-2026-10-24.md,qa/EVENTS-ALPHA16-2026-10-24.json,qa/MT3000-ALPHA16-2026-10-24.json. Privateevidence private/events-alpha16-20261024,private/alpha16-install-20261024. Docs-onlyclosure follows. Do not rerun non-idempotentprepare/rewrite/install/publication scripts; preserve immutable receipts. UserrefreshCtrlF5/#events loadsnewmodule/style. No pendingappwriter. Record newdictationimmediately inownerTODO; newproductchangesrequire nextversion/CI. Earlier activeheadersbelow are history.

# READY FOR PUBLICATION: alpha16 event layout verified on MT3000 —24October2026

Exacte7609c9 CI771app/112QA each/47UI PASS. Canonical831904bytes SHA913acd14de698b1898d7333cc20a788c14b75e2abdebc9354054f0d0807989d9; initial01207a3 cache-dependent fixturefailure retained/fixedtestonly. CSSfeature15/27/58widths, codeunderM/R/unbroken,min880/horizontal scroll. Existinghistory/terminal tests passed; nativebrowserinventoryempty, no visualclaim.

MT3000alpha16/dashboard92/ui64 installed87files/modes,RPC,actualHTTP8080+pinnedHTTPS,CSSrulesreadback;AutoONreserve/bothVPNDNS+2HTTPS. NormalStart64.672s,reserve41.281s. Four speedrows/manualspeedON/auto-newOFF/terms1/settingspreserved.193before/193afterencryptedbackups independentlydecrypted/read. No new speedtest/fault/hostnetwork/mainMT6000change. Read docs/VERIFICATION-ALPHA16-2026-10-24.md,qa/EVENTS-ALPHA16-2026-10-24.json,qa/MT3000-ALPHA16-2026-10-24.json. Next owner-authorized combinedGitHub/Gitea actualprerelease/featurebranch and source-onlyclosure; stablemain0.9.0 unchanged. Keep usergateway127.0.0.2:8080alive. Earlier active headings below are superseded.

# INSTALLING: alpha16 full CI PASS, MT3000 update in progress —24October2026

Exacte7609c981cb108a4fc79439d2b11368c1161e795 full dual-runtimeCI PASS,771app/112QA each/47UI. Same canonical831904byteIPK SHA913acd14de698b1898d7333cc20a788c14b75e2abdebc9354054f0d0807989d9.01207a3 TTL-dependent fixture failure retained; test-onlyrepair passedfocused5andfullmatrix; product/guardsunchanged. Owner70 CSS15/27/58widths,codeunderM/R,nointernalbreaks.

DedicatedMT3000 update started via private/alpha16-install-20261024/run.py:193entryfreshencryptedbackup independentlydecrypted/read. Stop/install/RPC/HTTP/HTTPS/Start/reserve sequence in progress. Read immutable per-step receipts/transport logs before resuming; never repeat completed steps or bypass failed guards. Required finalAutoONreserve,4speedrows,manualspeedON/auto-newOFF/settings/terms1preserved. No new speedtest/fault/hostnetwork changes. Publication still pending, feature/main/stable15baseline tracked in priorheaders. Usergatewaykeepalive127.0.0.2:8080.

# VALIDATING: alpha16 test isolation corrected —24October2026

Initialcf165e fullCI passed, package913acd14de698b1898d7333cc20a788c14b75e2abdebc9354054f0d0807989d9/831904bytes. Metadata-source01207a3 failed4manual-native-boundary cases: global Popen fake intercepted retention UCI read only after5s cache expiry. Test-onlye7609c9 fixes fixtureconfigured_days=7; productionpayload unchanged, no guards weakened. Focused5case/fullCI rerun in progress; new fullPASS required before install. Physicalstillalpha15AutoONreserve/manualspeedON/auto-newOFF,4speedrows. Source16notdelivered. Keep previousfailure private/events-alpha16-20261024/retained-ci-failure.json; never label01207a3PASS.

# ACTIVE: owner70 saved-history column layout alpha16 —24October2026

Owner70 asks widerState/narrowerEvent and code belowM/R diagram without splitting. CSS-only feature:15/27/58percent columns, min880px/horizontal scrolling, diagram block before unbroken code, Event normal wrapping. No event data/rendering/controller changes. Existing event_history/journal_terminal regressions PASS. Candidate0.9.1-alpha16/dashboard92/ui64; fullCI/canonical artifact/install/publication pending. Last verified device/publicbaselinealpha15 AutoONreserve with4successful speed samples, manualspeedON/auto-newOFF. Do not lose these settings/history.

Nativebrowser inventory via cua_repl reports no available apps/browsers; priorWindowsComputerUse URL-policy stop remains historical. No visualacceptance claim or UI fallback. Keep userloopbackgateway alive. Scope delivery standingownerpermission: new version/canonicalCI, dedicatedMT3000 backup→Stop/install/Start→reserve, GitHub/Giteafeature/prerelease. Main/stable0.9.0 unchanged. Store evidence under private/events-alpha16-20261024 and fresh private/alpha16-install-20261024. Newdictation goes immediately to ownerTODO.

# COMPLETE: owner69 speed launch/chart alpha15 delivered —24October2026

[GitHub alpha15](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha15) · [Gitea alpha15](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha15). Actualnon-draft prereleases,fourassets/server downloaded/SHA256verified. Canonicaltag/source7591d37f26a10d60df38c77e3f041fca8e54e012 andpublictag/source292eb5000933a17de9d0ed75ba9b8dd293ad529e,identicaltreebd3c50c139433fbf6e2cdb0e9b3aeebdb71429a2. Stable0.9.0/main/oldtags unchanged. Exactproducta60971e61cecb5a870aa2dc500c96d260f203f5f CI771app/112QA each/47UI PASS. Canonical831752bytes SHA98e8ff51ab77e895a693ef08f519d51062e3d6fab41afa78ba7c10ed6c78dab0. Docs-only closure follows without product changes.

MT3000/4.11.0 installedalpha15/dashboard91/ui63,AutoON/confirmedreserve/bothVPNDNS+2HTTPS.87immutablefiles/modes,actualHTTP8080+pinnedHTTPS,freshRPC,userconfig/terms1preserved,192before/193afterencryptedbackups independentlydecrypted/read. NormalStart67.125s,reserve41.203s. Manualspeedenabled,auto-newOFF. Realengine2profiles testedbefore14andafter15,32MiBtotalpayloadreserved,4successfulsamples retained; latestWG30.463/17.930Mbps,OVPN14.570/10.378Mbps. Noquotaguardreset/hostnetwork/mainMT6000/faultchange.

UI: Testspeed alwaysopensreview whenidle; explicitenable/run confirms manualsettings/currentlimits withauto-newOFF beforequeue,unconfirmedsaveneverstarts; connectedpreselection, running-jobdisable, localrefusalfeedback. BackendCPU/traffic/quota/cooldown/routesunchanged. Graphbelowtable: measured download/uploadperselectedserver/period, firstsamplepoint andlaterlines, failuresbreaklines. NewUIregressions EN/RU passed. NativeComputerUse stoppedbeforecapture becausebrowserURLnotconfidentlyidentified; nofurtherUIinput, nativevisualNOTVERIFIED. HTTP/syntheticDOM proof is notnativevisual. No newVMclaim;14VMresults remainversioned.

Read docs/VERIFICATION-ALPHA15-2026-10-24.md,qa/SPEED-ALPHA15-2026-10-24.json,qa/MT3000-ALPHA15-2026-10-24.json. Privateevidence private/speed-alpha15-20261024,private/alpha15-install-20261024. Do not rerun non-idempotentprivateprepare/rewrites blindly. LeaveAutoONreserve/userfixedgateway127.0.0.2:8080alive; actualMT3000192.168.11.1viaif3/.228,Wi-Fi14sameIPcollisionunchanged. User shouldreloadCtrlF5/new#testspage fordashboard91. No pendingappwriter. Newownerrequests must be recorded immediately; newproductchanges require nextcandidate/CI/delivery.

# READY FOR PUBLICATION: owner69 speed fix alpha15 installed —24October2026

Exacta60971e CI771app/112QA each/47UI PASS; canonical831752bytes SHA98e8ff51ab77e895a693ef08f519d51062e3d6fab41afa78ba7c10ed6c78dab0. Source fixes disabled-test review/save/start, preserves limits/auto-newOFF, preselectsconnectedVPNs, displays refusals/busy and realdownload/uploadchart belowtable with server/period/errorgaps. Backendguards unchanged. NativeComputerUse stopped before capture due unknownbrowserURL; no furtherUIinput, visualNOTVERIFIED.

MT3000alpha15/dashboard91/ui63 physicallyverified87files/modes,RPC,HTTP8080/pinnedHTTPS,settings/terms1,encrypted192before/193after independentlydecrypted/read. FirstnormalStart67.125s, reserve41.203s. AutoON/confirmedreserve/bothVPNDNS+2HTTPS.2prior speedrows preserved+2actualnew rows:WireGuard30.463/17.930,OpenVPN14.570/10.378Mbps. Manualspeedenabled,auto-newOFF,32MiBtotalreservedacrossbothbatches,noquotareset. No hostnetwork/mainMT6000/fault changes.

Read docs/VERIFICATION-ALPHA15-2026-10-24.md,qa/SPEED-ALPHA15-2026-10-24.json,qa/MT3000-ALPHA15-2026-10-24.json. Private evidence private/speed-alpha15-20261024 and private/alpha15-install-20261024. Next: owner-authorized combinedGitHub/Giteafeature/tag/actualprerelease and source-onlyclosure; stable0.9.0/main untouched. LeaveAutoONreserve/usergateway127.0.0.2:8080 alive. Earlier active/alpha14 headings below are history.

# ACTIVE: owner69 speed launch/chart alpha15 —24October2026

Owner asks working Test speed and graph below server descriptions. Source0.9.1-alpha15/dashboard91/ui63: disabled manual testing can be explicitly enabled/launched in review without bypassing backend guards; preserve limits, auto-newOFF, connected profiles preselected, failure feedback/busy states; real stored download/upload chart with server/period selection and error gaps. New launch/chart UI regression plus existing speed-collapse test PASS. FullCI/canonical build/deployment pending; source not yet delivered.

ActualMT3000 alpha14 backend tested through existing normalsetup_speed→speed_start: manual enabled/auto-newOFF,2already-connected profiles,16MiB reserved. Bothsuccess: WireGuard28.845/17.455Mbps,OpenVPN17.409/9.039Mbps,AutoRUNNING/confirmedreserve. No route/hostnetwork/VPN changes. These are engine measurements onalpha14, not yet newUI acceptance. Evidence private/speed-alpha15-20261024/actual-speed-start.json and actual-speed-results.json. New code does not weaken disabled/quota/CPU/traffic/route guards; first explicit action saves enabled settings. Last physical full delivery remainsalpha14, published on both services.

Next: full exact-source CI and package; install dedicatedMT3000, restoreAutoONreserve, verify servedchart and retained actualsamples, then combined GitHub/Gitea delivery within standing owner authorization. Keep userloopbackgateway127.0.0.2:8080 alive. Do not rerun previous rewrite scripts blindly.

# COMPLETE: alpha14 documentation/helper audit delivered —24October2026

Owner68 complete within recorded test scopes. [GitHub alpha14](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha14) · [Gitea alpha14](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha14). Actual non-draft prereleases, four assets each downloaded/hash-verified. Gitea canonical tag/source388879bd1ef28a7bb0eb385cf10754bc97c84437 / GitHub tag/source17740c6e83cfd89a45b0f7947b81ace6f9eaa83a, identical treeb61b99e60c9eda6d0034d8ddf589f43749b594ed. Both feature histories retained, main/stable0.9.0 unchanged. Product exactfe3b492 CI771app/112QA each,46UI; canonical829928byteIPK SHA49ffb3e57b288f899c84e77546e7b1a0e26243300765bf5927ef8270ae214342. Failed intermediate8984120 install-kit mismatch retained and corrected. Publication-only documentation closure follows without product changes.

MT3000/4.11.0 installedalpha14/dashboard90/ui62, AutoON/confirmedreserve/bothVPNDNS+2HTTPS.87files/modes, HTTP8080/pinnedHTTPS, preserved settings/terms1, independently decrypted/read190entry encrypted before/after backups. NormalfirstStart64.719s, reserve41.922s; no guards bypassed. Fault-readiness currentreserve PASS read-only, no actualphysicalfault. MainMT6000/Windowsnetwork untouched. ActualWindowsCheckOnly safely refused CLIENT-CABLE-PROBE-ROUTE-MISMATCH; no credentials/HTTP. Native physical-browser/externalLAN/IPv6/KillSwitch acceptance unverified.

199prose/notice files incl OFL and60runtime/helper sources inventoried. CurrentRU/EN docs/help/prompts/wizards aligned;31Help topics perlocale,458codes andfourfullprompts source-generated.82prompt recipe matrix PARTIAL for external models/LAN, not autonomy certification. Real new isolatedx86VM stableinstall/reinstall→14upgrade, fullENRUsetup/retention/components/diagnosis/emergency pending edit PASS; VM741cfb8427fd80691404b47ff363d232d4de5f3d8ad3168e6862954ddad484c0 poweredoff exit0. No observer to resume. Normative legal/licence text and terms1 unchanged.

Read docs/VERIFICATION-ALPHA14-2026-10-24.md, docs/DOCUMENTATION-AUDIT-2026-10-24.md, qa/OWNER-DOCS-ALPHA14-2026-10-24.json and qa/MT3000-ALPHA14-2026-10-24.json. Private receipts/scripts under private/full-doc-audit-20261024 and private/alpha14-install-20261024. Do not rerun non-idempotent private rewrite/publication scripts. New product work requires a new candidate/source/CI; old active headings below are history.

User management address: actualMT3000192.168.11.1 via cableif3/.228; Wi-Fiif14/.100 reaches a different same-IP device. Keep fixed localgatewayPID25196 alive, user URL http://127.0.0.2:8080/cgi-bin/luci/admin/services/homensai-vpn?lang=ru#overview. No hostroute changes. Stock80alias403 remains unaccepted;8080login verified. Gateway address is localcomputer lifetime, never a LAN-witness target. LeaveAutoONreserve; no pending device writer.

# READY FOR PUBLICATION: alpha14 physically verified —24October2026

Owner68 documentation/help/wizard/helper audit implemented and validated. Exact fe3b4927559e426f5741e7a677bccaedeec3590f dual-runtimeCI PASS771app/112QA each,46UI, canonical829928byteIPK SHA49ffb3e57b288f899c84e77546e7b1a0e26243300765bf5927ef8270ae214342. Intermediate8984120 VERSION-INSTALL-KIT failure retained/corrected. New actualx86VM stableinstall/reinstall→14upgrade87files/modes/RPC/HTTP/fullENRUsetup/retention/componentcommands/emergency-pending PASS; VM poweredoff exit0.82prompt recipes are PARTIAL external-model/LAN scope, not autonomy certification.199prose/notice files incl unchangedOFL+60runtime/helper sources inventoried. Normative terms/licences preserved.

ActualMT3000 nowalpha14/dashboard90/ui62. NormalStop→install→firstStart64.719s→reserve41.922s; finalAutoON/confirmedreserve/bothVPNDNS+2HTTPS;87immutablefiles/modes+servedHTTP8080/pinnedHTTPS; only own lease fields changed; terms1/settings retained; independently decrypted/read190-entry encrypted backups before/after. Actualfault readiness currentreserve PASS read-only; no physical fault. ActualWindowsCheckOnly safely refused CLIENT-CABLE-PROBE-ROUTE-MISMATCH, no credentials/HTTP/hostnetwork changes. Native browser/externalLAN/IPv6/KillSwitch unverified. LeaveAutoONreserve.

Read docs/VERIFICATION-ALPHA14-2026-10-24.md, qa/OWNER-DOCS-ALPHA14-2026-10-24.json, qa/MT3000-ALPHA14-2026-10-24.json. Next is owner-authorized combined GitHub/Gitea featurebranch and realalpha14prerelease, preserving separate histories/main/stable0.9.0. Product unchanged after finalCI; docs/evidence only closure. Private publication scripts prepared under private/full-doc-audit-20261024, not run yet. Keep loopbackusergateway127.0.0.2:8080 alive; fixedcable3/.228, no hostroute edits.

# ACTIVE: alpha14 documentation/helper candidate —24October2026

Owner68 full audit continues. Candidate0.9.1-alpha14/dashboard90/ui62 is source work, NOT installed/published. Baseline alpha13 remains last verified AutoON/reserve. Read docs/DOCUMENTATION-AUDIT-2026-10-24.md. Current7generated refs cover31Help topics per locale/458codes/four prompts.195+ public prose/legal files structurally reviewed; current index enumerates191Markdown+5legal notices. NormativeLICENSE/LICENSING/DISCLAIMER bodies match priorHEAD; terms1 unchanged.46UI suites, native helper SelfTest,2PowerShell regressions and3Linux emergency cases PASS. Public source privacy1049files PASS. Full committed-source CI, canonical artifact, VM/install/publication still pending. Do not issue product acceptance from focused tests.

Helper fixes: refuse wrong management interface before login/RPC; not a pinned HTTP socket/no claim that every route race is eliminated. Emergency Stop refuses own UCI commit for pending edits or failed service Stop. Setup step2 exposes1–2000/1–7validated fields. Source-driven7reference generation/hash manifest catches drift; archive banners no longer call0.9.0 current. Do not rerun private rewrite scripts blindly; their earlier text predates later refinements.

Keep user fixed local gateway alive at http://127.0.0.2:8080/cgi-bin/luci/admin/services/homensai-vpn?lang=ru#overview (PID25196; reverify identity before managing). It pins cable interface3/.228 to actual MT3000192.168.11.1. Wi-Fi14/.100 reaches different same-IP device; no host routing changes authorized/needed. Stock80alias403 remains a known limitation;8080login verified.

Next: exact source CI; retain failures, fix without guard bypass, rebuild/canonical hash, actual isolated VM and current-source prompt cases, then owner-authorized GitHub/Gitea prerelease and dedicatedMT3000 upgrade/AutoONreserve restore. Stable0.9.0/main unchanged; no physical fault/Telegram send implied.

# ACTIVE: comprehensive documentation/helper audit —24October2026

Owner68 explicitly requested all docs/help/wizards/helpers, then said continue. Physical/public baseline remains alpha13 AutoON reserve; no app/device update during this review. Source WIP is intentionally version-stale until all corrections are ready. Do not install it as alpha13 or call it delivered.

Audit work: private/full-doc-audit-20261024 inventory/catalog/flags; initial246human-facing files plus discovered LAN/legals. Current Help rewritten with31runtime topics incl3new areas; generated full Help EN/RU and458-code reference via scripts/sync-documentation.py + qa/export_documentation.js. Canonical guides/aliases rewritten; further archive/current classification and full QA pending. LICENSE/LICENSING/DISCLAIMER normative bodies preserved; terms version1 unchanged, UI full reference generated from originals with separate current-scope note. Found/fixed a lost Windows backslash in LAN prompt; installation and LAN prompts now consistent and release-scoped. Runtime navigation/legacy promises corrected. Wizard step2 now exposes existing backend retention fields. Helpers: control-route mismatch refuses before login/RPC; emergency stop no longer commits pending app edits after warning. New regression tests and full checks still pending.

User also requested MT3000 address: cable interface3/.228 reaches GL-MT3000 at192.168.11.1, Wi-Fi interface14/.100 reaches a different same-IP device. Default browser8080 refused. User-requested fixed loopback gateway PID25196 at127.0.0.2:8080 forwards through cable only, login form verified GL-MT3000; keep it alive for user. No host/router network settings changed. Raw80/443 are forwarded too; stock80 with alias Host currently403, so do not claim full stock-panel alias acceptance. This private gateway is not a LAN-witness address.

Next: finish current guides/technical refs, classify/read/archive all public human-facing files, add meaningful helper/contract regressions and sync/audit checks. After review/test, new package version needed for runtime/helper changes; prose-only changes alone would not require reinstall. Never accept terms or alter host network to bypass controls.

# COMPLETE: alpha13 deployed and published —24October2026

All owner items51–67 delivered. Latest read-only MT3000 check: AutoON, confirmed reserve, both VPN DNS/HTTPS healthy; installed0.9.1-alpha13-1/dashboard89/ui61, settings/terms retained,190-entry encrypted pre/post backups independently verified. No physical fault injected; host network/main MT6000 unchanged. Own VM powered off exit0; no test browser/observer job to resume.

Published actual non-draft prereleases, four assets each downloaded and SHA256-verified:

- [GitHub alpha13](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha13)
- [Gitea alpha13](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha13)

Both feature branches saved with equal trees and preserved separate histories; main/stable0.9.0 unchanged. Release canonical sourcea2c39ac / public8cf690f; tested product2e8f549 (full dual-runtime CI768app/108QA,46UI). Package815967bytes SHA256f570634022381f8520b3214786bab207228497eda6589fb81cb5ab5f4fd786a8. Documentation-only closure follows publication; no product changes after CI.

[Full report](../VERIFICATION-ALPHA13-2026-10-24.md) · [Batch matrix](../../qa/OWNER-BATCH-ALPHA13-2026-10-24.json) · [Physical receipt](../../qa/MT3000-ALPHA13-2026-10-24.json). Fifty synthetic personas combine49pre-crash+1rerun with matching frozen assets. First60s VM cold-boot timeout retained; bounded longer observation confirmed reboot/config preservation/fresh monitor. Native physical-browser visual and independent externalLAN/IPv6/KillSwitch remain outside acceptance.

Private receipts: `private/owner-batch-validation-20261024/publication.json`, `private/alpha13-install-20261024/`, exact CI receipt in `.git/handoff/`. Older ACTIVE/batch-only/alpha12OFF text below is historical and superseded by this completion. Do not restart Auto or old observers merely to resume reading this handoff.

# Alpha13 verified on MT3000 —24October2026

Product source2e8f5499e4245321c3611e95981d68f539e14e86 passed full dual-runtime CI:768app/108QA,46UI; canonical IPK815967bytes SHAf570634022381f8520b3214786bab207228497eda6589fb81cb5ab5f4fd786a8. On actual MT3000/4.11.0:87immutable files/modes, HTTP8080+pinnedHTTPS, freshRPC, first Start54.8s (transport58.8s), normal reserve restoration37.2s (transport38.4s), AutoON/reserve/bothVPN DNS+HTTPS confirmed, settings/terms preserved, encrypted190entry pre/post backups independently decrypted/read. New fault readiness on current reserve PASS read-only, no physical fault injected. Native browser/externalLAN/IPv6 remain unverified.

Read [verification](../VERIFICATION-ALPHA13-2026-10-24.md), [batch matrix](../../qa/OWNER-BATCH-ALPHA13-2026-10-24.json), [physical receipt](../../qa/MT3000-ALPHA13-2026-10-24.json). VM actual upgrade/settings/kernel expiry/restart/reboot passed with documented initial60s cold-boot timeout and longer bounded retry; VM powered off exit0. 50distinct synthetic personas recovered49old+1rerun; canonical UI normalized-text equality verified. Older failures/partialalpha12 remain historical.

Latest owner authorized GitHub/Gitea/MT3000 delivery after all checks, superseding old batch-only text below. Publication uses feature branch and alpha13 prerelease, leaves main/stable0.9.0 unchanged. Publication receipts under private/owner-batch-validation-20261024 and .git/handoff; final remote links are verified during delivery.

# ACTIVE: final delivery authorized after reboot —24October2026

Latest owner: «проверь всё, что не закончено, закончи и продолжи, если необходимо, залей на GitHub, Git и в роутер и дай мне отчет». This renews item67 and supersedes the older local-only batch rule. Current executor: resumed-owner67-auto-vpn-20261024. No publication/device writes completed yet in this resumed block.

# Resumed after crash: alpha13 software/UI checks recovered —24October2026

Read [UI crash recovery](UI-CRASH-RECOVERY-2026-10-24.md) first. Exact ca7bf7e canonical CI PASS768app/108QA per runtime/46UI; interrupted synthetic matrix recovered as49historical PASS + separately rerun persona49 PASS,50unique same-frozen-source scenarios total. Own browser/listener cleanup independently verified. This is loopback synthetic acceptance, NOT physical alpha13 installation. Preview recorded draft package hash; canonical IPK asset equality still needs verification. No router/Windows changes or Git publication this block. Historical alpha12 AutoOFF is not a new live read. Next: canonical artifact-to-preview checks, fresh cable/device/recovery preflight, then owner67-authorized combined delivery and actual acceptance without bypassing guards. Earlier batch-only/current headings below are history until reconciled with latest owner instruction.

## Пункт58 готов локально — сбой только текущего канала и проверка перехода

В простое одна кнопка «Имитировать сбой трафика» и длительность; выбор основной/области убран. Кнопка доступна для открытия проверки даже при отсутствии условий: показывает подготовку/конкретные причины и обновление данных без разрушительного RPC. При подтверждённой готовности — обзор точного туннеля/ID/длительности и запуск. Во время активного/неподтверждённого сбоя доступна «Остановить тест и снять сбой»; в простое её нет. Сам запуск не выдаётся за завершённый переход.

Backend поддерживает действующий continuous-pair router-probed режим без старого LAN-сертификата: проверяет private pair intent/revision/RUNNING, отсутствие pending manual request, штатные network/config fingerprints, текущий порядок policy, подтверждённый journal для резерва, точные обе текущие identity/generation/kernel bindings и свежие DNS+2HTTPS. Основной/резерв выбирает из реального private policy/journal, запрос другого ID отклоняется. nft затрагивает только фактическое выбранное устройство, таймаут/nonce/watchdog/Stop fence/проверки перед dispatch сохранены. Старый bounded LAN-certified режим сохраняет прежние сертификат/окно.

Проверка резерв→основной во время явного активного теста может преодолеть только предпочтение hold_reserve; по-прежнему нужны серия отрицательных проб резерва и recovery_ready основного. Настройки не меняются. После отмены/таймаута тестовое исключение не действует. Автоматический переход, вызванный таким сбоем, маркируется test. Worker снимает блокировку досрочно при свежем подтверждённом другом маршруте; таймаут без доказательства — FAULT-TRANSITION-NOT-CONFIRMED, не PASS. UI даёт понятные состояния, новые RU/EN коды внесены в source error tables. Обычные failure thresholds/cooldown/rate budget сохраняются; при слишком коротком выбранном времени переход может не подтвердиться, это честный результат.

PASS:117 Python3.9 unit/platform-model tests в readonly/no-network Linux container (fault_control, committed_recovery, pair_auto, pair_manual, native_switch, native_history). Проверены оба selected устройства, wrong ID, stale/generation/policy/Stop/health, pre-test samples не доказывают переход, bounded active marker/expiry/cancel, hold override без обхода failure/health. Node legacy_actions/recovery/monitor и source syntax PASS; diff --check PASS. Первоначальный native Windows запуск не поддержал fcntl; Linux прогон обнаружил shadowed role в новом eligibility, исправлено и все тесты повторены. Реальные kernel nft/fault переходы на VM/MT3000, browser visual и полная CI новой пачки НЕ выполнены. Generated assets/VERSION/сборка/commit/push/роутер не менялись. Last physical state alpha12 AutoOFF прежнее; issue51 открыт.
# ВАЖНО: новая политика пачки; MT3000 alpha12, Auto OFF —24October2026

Владелец дважды подтвердил: выполнять все текущие/новые правки и проверки локально; общую версию/сборку/роутер/Gitea/GitHub делать только после конца списка. Сохранять каждую диктовку сразу. Никаких новых доставок/перезапусков на роутере до разрешённого общего этапа.

Установка alpha12 уже выполнялась при поступлении правила: opkg/86files+modes/RPC/HTTP8080/pinnedHTTPS PASS. Две попытки восстановить прежний AutoONreserve остановились на штатных vendor worker quiet/busy gates, обе выполнили cleanup. Последнее строго read-only подтверждение: установлен0.9.1-alpha12, pair STOPPED, intentoff, оба owned-интерфейса отсутствуют, собственная guard-таблица отсутствует. НЕ считать Auto восстановленным. Прежняя полностью рабочая база —alpha11 AutoONreserve. Дальнейшие попытки/откат/установка остановлены по правилу владельца, защиты не обходились. [Частичный физический отчёт](../../qa/MT3000-ALPHA12-PARTIAL-2026-10-24.json).

Пункт50 локально готов: две серииblue primary/orange reserve с легендой; текущие роли из одинаковых до/после inventory, legacy без роли только в архиве. Исправлен native-state overwrite состояния отказа и строго восстанавливаемая старая сигнатура checkpoint;36focused Python и полная dual-runtime CI PASS на07040b7. Физическая проверка роли на работающей паре NOT RUN: Auto не восстановлен. Новый график доставлен по байтам, но полный device acceptance остаётся PARTIAL. Никаких push после обновлённого правила, новые отчёты/передача — local WIP.

Следующая локальная задача: исследовать повторяемый VENDOR-WORKER-QUIET-UNVERIFIED/BUSY после первого ifup при Start. Не превращать её в новый deployment до конца пачки. Перечитать private/ACTIVE-EXECUTOR.local.json и живое состояние перед любым будущим разрешённым действием.

# Item50 alpha12 failure-chart correction candidate —24October2026

Only primary blue/reserve orange series; explicit colour legend. Old records without event-time role remain archived/excluded, never assigned from today’s pair. Roles for new episodes use two matching configured snapshots around the actual probe, including controller startup/error states. Fixed accidental native-state overwrite of probe state and strictly repair only the provable legacy failure-row signature. Focused36Python3.9 statistics tests and UI regression PASS; complete CI and dedicated MT3000 update follow within standing owner scope. Installed baseline stillalpha11 AutoONreserve until update. No fault injection or host/MT6000 changes.

# Alpha11 installed on dedicated MT3000 — 24 October2026

Owner49 «Роутер обнови» completed. Actual model glinet,mt3000-snand/firmware4.11.0 verified before write; previousalpha9 AutoONreserve. Fresh190-entry encrypted pre-backup independently decrypted/read. Normal Stop→opkg alpha11→86immutable files/modes+own/protected settings/terms→freshRPC→actualHTTP8080 and pinnedHTTPS dashboard87/ui59 allPASS. First Auto Start hit VENDOR-WORKER-QUIET-UNVERIFIED and safely cleaned up; failure retained. After independently observed workers busy0, one normal retry reached RUNNING. Programmatic reserve restoration confirmed; final fresh RPC: AutoONreserve, manual_hold target, both VPN DNS+2HTTPS healthy,2fresh bound endpoints. Only expected lease nonce/deadline changed; unrelated settings/terms preserved. Final190-entry encrypted backup independently decrypted/read. [Receipt](../../qa/MT3000-ALPHA11-2026-10-24.json). No host/MT6000/fault changes; no native-browser visual or external-LAN claim. No active device job remains; leave Auto on reserve. Product/Git branch alpha11 already published before this device task; new physical receipt/docs are local, no new release or Git push performed here.

# Owner48 completed: alpha11 training/docs published — 24 October2026

Published feature/owner-ui-20261023 to both GitHub and Gitea. Canonical tested99eab5956c3f0af63e380d1ff336750a2d6e8549 and public497649b1d0100cf5b644b5e7450ee5c5b9c449f8 have identical tree13b11b0d51d97575a53831bcd63b2d139ced4fe9. Exact final source passed dual-runtime750app/108QA each and45UI primary; package806313bytes SHA8671e8096ff75cab54b2855589123d8ab85ee0bdc28008dacd40dd4856d846f6. A documentation-only closure records publication and will be saved to these same branches; no product files change.8interactive vector lessons and full quiz EN/RU checked;179Markdown files inventoried/classified/local targets PASS. Current guides/changes RU→EN refreshed; legal/dates/pinned stable assets preserved. Alpha10 VM report included with explicit PARTIAL GL/LAN/model scopes. No new release/tag/main merge or physical install. Native browser visual acceptance and physicalalpha11 remain pending. Last verified physicalbaselinealpha9. No active device writer; no further upload/install is implicit. Final remote proof: private/docs-training-20261024/publication.json.

# Alpha11 training/docs ready for authorized branch upload — 24 October2026

8interactive lessons and complete EN/RU quiz PASS; playback/pause/back/next/reset/hidden/dispose tested, no RPC. Product sourcee5451728e43b2f649aaf1e3f8a9538949ac488a5 passed full dual-runtime CI:750app/108QA each,45UI primary; canonical806313byte package SHA8671e8096ff75cab54b2855589123d8ab85ee0bdc28008dacd40dd4856d846f6.179Markdown documents inventoried/classified, local targets/version scopes PASS. Main current guides rewritten RU/EN; pinned stable instructions and historical/legal evidence preserved. Further documentation-only closure corrects VERSIONING/PUBLICATION/recovery pointers and records evidence, then is checked before upload. No source/product differences in that closure. Target feature/owner-ui-20261023 on both Git services; no main/tag/release/device mutation. Native browser visuals and physical alpha11 remain unverified. Read docs/TRAINING-AND-DOCS-AUDIT-2026-10-24.md and qa/OWNER-TRAINING-DOCS-2026-10-24.json.

# Alpha11 training/documentation candidate — 24 October2026

Owner48: eight interactive native-vector lesson scenes, Play/Pause/Back/Next/Reset, hidden/dispose cleanup and no router RPC. Complete8lesson/quiz flow EN/RU passed; stale helper/return/client-start/step-number/monitoring statements corrected. Current RU→EN guides/changes and179-file Markdown index reviewed; all local link targets and version scopes checked. Alpha10 VM audit is included with PARTIAL external platform/model coverage. Candidate alpha11/dashboard87/ui59 has not been installed on hardware or accepted in a native browser. Exact-source CI/canonical package and authorized GitHub/Gitea branch publication follow. Stable0.9.0 and last verified installedalpha9 stay distinct.

# Item47 VM audit completed within explicit scope — 24 October2026

Read VM-AUDIT-2026-10-24.md and qa/OWNER-PROMPT-VM-ALPHA10-2026-10-24.json. Actual double build/install/idempotence/dependency repair/setup/upgrade/files/HTTP/history/negativeRPC/restart/rollback/reupgrade/reboot PASS.76 prompts inventoried with PARTIAL platform/model scopes. Four lab/harness failures retained and resolved; no new confirmed application defect. Owned disposable VM powered off (exit0). No product changes, publication or physical-router writes. Real GL/LAN/external models/visual/full-fault combinations remain NOT RUN. New audit files are local WIP.

# Alpha10 uploaded to GitHub and Gitea — 24 October 2026

Owner request «залей все на гитхаб и гит» fulfilled: branch feature/owner-ui-20261023 exists on both services. Tested canonical source b1630a79532f0285e7d3a2bf1636e395d138bef5 was saved to Gitea; GitHub reviewed snapshot196a1ca640bf004ffcd0fd35753ee5609b678a7d has the identical complete tree093581b70ce081a83adeaff0ca4764a4164d551c. Final exact-source dual-runtime CI passed again:750 application +107QA per runtime,44UI on the primary runtime; canonical IPK SHA2569a40e7ce48170bc76d2aada215764691edd60dd61d1f1f660e88afcad1b1896b. Source, generated dashboard86/ui58, package/checksum, tests and all handoffs are included. Evidence qa/ALPHA10-BRANCH-PUBLICATION-2026-10-24.json. A following documentation-only closure records this result and will be saved to both same branches. No product files change in that closure. No main merge, new release/tag or alpha10 physical-router installation; stablev0.9.0 and last installedalpha9 unchanged. Browser visual acceptance and prior prompt/VM limitations remain open. Next step: await further owner direction; do not silently install or publish main from this Git-only request.

# Alpha10 batch checked for GitHub/Gitea publication — 24 October 2026

Items32–46 and the onboarding Stop actor marker are included in0.9.1-alpha10/dashboard86/ui58. Product source03fe2c9470683310d0571f6af5dd20063c197157 passed exact-commit dual-runtime CI:750 application +107QA tests per runtime,44UI suites on the primary runtime, complementary runtime skips. Canonical Linux IPK801579bytes, SHA2569a40e7ce48170bc76d2aada215764691edd60dd61d1f1f660e88afcad1b1896b. Windows draft package replaced with canonical artifact; no product source change. Receipt qa/OWNER-UI-ALPHA10-2026-10-24.json. Publication is authorized for both Git services; installation was not requested by this message. Device alpha9 and stable publicv0.9.0 remain unchanged. Native-browser acceptance and previous prompt/VM limits remain open.

# Batch publication candidate 0.9.1-alpha10 — 24 October 2026

Owner ended the local-only batch for GitHub/Gitea publication. Items32–46 source and generated UI are included in alpha10/dashboard86/ui58. Local source snapshot will undergo exact-commit dual-runtime offline CI before branch push. Includes grouped live observations, actor/direction/latency metadata, compact statistics/failure chart, no null child text, readable channel/server/outcome statistics and layout/copy corrections. Onboarding emergency Stop also explicitly records operator provenance. No physical router installation is part of this publication; installed alpha9 remains the last verified device baseline. Native-browser visual acceptance and older VM/prompt limitations remain open. Existing v0.9.0 release is unchanged. See NEXT-AI-2026-10-24.md and OWNER-UI-TODO-2026-10-23.md.

# Item31 installed; item30 latency recommendation/statistics delivered

0.9.1-alpha9/dashboard85/ui57 installed on dedicated MT3000. Auto works/power group raised to match right Step1 content with common12px top inset; old20px margin/22px padding removed. Literal null removed from page header. Previously saved item30 work completed: current lower-delay recommendation with rationale/bound endpoint/actual selected role before manual controls, weighted mean/minute min/max/success count table follows graph window. RPC errors and route-helper refusal fenced; no automatic route/pair change. Focused existing suites and new meaningful aggregation/refusal regressions PASS; exact-source dual-runtime full CI and86files/modes/actualHTTP8080/HTTPS verified. Final AutoONreserve, both VPN DNS+twoHTTPS healthy; encrypted final backup independently verified. [Evidence](../../qa/MT3000-ALPHA9-2026-10-24.json). Item30 broader audit remains open for item15 VM coverage limits/item19 native browser review. No new native visual proof: browser automation was stopped by URL-confidence policy.

# Актуальная передача следующему ИИ — 24 октября 2026

Читать [NEXT-AI-2026-10-24.md](NEXT-AI-2026-10-24.md) первым. Установлена alpha8; пункт30 (аудит старых диктовок, более заметная рекомендация минимальной задержки и таблица статистики) — незакоммиченный WIP в исходниках, НЕ установлен. Активных операций записи на роутер нет; последнее подтверждённое состояние AutoONreserve.

# Item29 installed — short reserve label

0.9.1-alpha8/dashboard84 installed on dedicated MT3000. Manual channel-switch card uses "Интернет: задействован резерв" (English "Internet: reserve in use"). Copy-only change; existing switching/status logic unchanged. Existing manual UI check and exact-source dual-runtime full CI PASS.86files/modes and actual HTTP8080/HTTPS bytes verified; final AutoONreserve, both VPN DNS+twoHTTPS healthy; encrypted backup independently verified. [Evidence](../../qa/MT3000-ALPHA8-2026-10-24.json). No native browser visual acceptance claim, host-network/primary-router changes or public release.

# Item28 installed — Auto first, monitoring and VPN check inside

0.9.1-alpha7/dashboard83/ui56 installed on dedicated MT3000. Automatic VPN failover is first in all three Overview designs. Its header holds monitoring at upper right; its controls place the existing VPN check action at right. Former duplicate tools removed from page header. Narrow screens stack controls without changing actions or status freshness. Existing generated-tree regression covers first placement, real monitor lamp, real connectivity button, and retained graphs/manual controls; existing action tests PASS. Exact-source dual-runtime full CI and86files/modes/actualHTTP8080/HTTPS verified. Final AutoONreserve, both VPN DNS+twoHTTPS healthy; encrypted final backup independently verified. [Evidence](../../qa/MT3000-ALPHA7-2026-10-24.json). Native browser visual acceptance remains unavailable. No host-network/primary-router/fault changes or new release.

# Item27 installed — compact current checks and VPN peer addresses

0.9.1-alpha6/dashboard82 installed on dedicated MT3000. Generated current-checks renderer verified with 11 rows: five visible initially, remaining rows behind expandable triangle; full-list search and reordering preserve the limit. Primary and reserve precede other profiles; channel column shows their roles rather than default group. Each server cell includes a fresh, identity-bound live VPN peer IP/port when available; unavailable/stale endpoints remain explicitly unknown. Owner screenshot referenced alpha3, while pre-update live router was alpha5. New immutable module refreshes the page asset. Exact-source full CI and86files/modes/actualHTTP8080/HTTPS verified. Final AutoONreserve, both VPN DNS+twoHTTPS healthy and both bound peer addresses confirmed; encrypted final backup independently verified. [Evidence](../../qa/MT3000-ALPHA6-2026-10-24.json). No native browser visual claim, host-network/primary-router/fault changes or new release.

# Item26 installed — newest-first live terminal

0.9.1-alpha5/dashboard81 installed on dedicated MT3000. Newest records appear at the top under pinned status. Timestamp-ordered insertion keeps delayed historical rows below fresher observations; oldest entries expire at the tail of the2000line buffer. Following live and return button use the top edge/up arrow. Reader anchoring preserves the same visible older record when rows arrive. One-second screen heartbeat and actual network probe cadence remain separate. Existing pair and settings preserved. Exact-source full CI and86files/modes/actualHTTP8080/HTTPS verified. Final AutoONreserve, both VPN DNS+twoHTTPS healthy; encrypted final backup independently verified. [Evidence](../../qa/MT3000-ALPHA5-2026-10-24.json). No native browser visual claim, host-network/primary-router/fault changes or new release. No further device mutation required.

# Item25 installed — configured client pair chooser

0.9.1-alpha4/dashboard80 installed on dedicated MT3000. Only configured client tunnels are offered, reserve excludes the same client. Explains role vs protocol vs assigned profile and the exact Auto/stock-VPN responsibilities. Saved profiles without a client binding are excluded; stopped configured clients remain selectable. Existing primary/reserve assignments preserved; WireGuard and OpenVPN UCI configuration bytes independently compared equal across encrypted pre/post exports. Standing owner authorization permits these application updates without repeated questions. Exact-source full CI and86files/modes/actualHTTP8080/HTTPS verified. Final AutoONreserve, both VPN DNS+twoHTTPS healthy; encrypted final backup independently verified. [Evidence](../../qa/MT3000-ALPHA4-2026-10-24.json). No native browser visual claim, host-network/primary-router/fault changes or new release. No further device mutation required.

# Item24 installed — five visible current server probes

Standing owner authorization: future HomenS.AI Auto VPN updates on this dedicated MT3000 may be installed without repeated questions, using the existing tested recovery/lifecycle flow and restoring reserve. Owner explicitly said “ставь сразу без вопросов на роутер - я разрашею всегда”. Earlier alpha3 scope rejection was resolved by explicit approval; no such approval remains pending.

0.9.1-alpha3/dashboard79 installed on dedicated MT3000. Five initial table rows; triangle expands all others; full search/sort and expansion state retained. Default order primary then reserve, roles replace default grouping. Exact-source full CI and86files/modes/actualHTTP8080/HTTPS verified. Final AutoONreserve, both VPN DNS+twoHTTPS healthy; encrypted final backup independently verified. [Evidence](../../qa/MT3000-ALPHA3-2026-10-24.json). No native browser visual claim, host-network/primary-router/fault changes or new release. No further device mutation required.

# Item24 alpha3 candidate ready — device update awaits explicit scope

Five visible current-server probe rows, triangle expand/collapse of all remaining rows, persistent disclosure/full-list search and sort; default primary then reserve with role labels. Exact source ebc0df0 /790185bytes /SHAdab1c30348925c75eb44f07ce020622a32d69e5e338f5ac539181605c2e234ad passed dual-runtime full CI. [Candidate evidence](../../qa/OWNER-UI-ALPHA3-2026-10-24.json). Automatic review rejected the combined device preparation/Stop command because the earlier explicit installation approval named alpha2. The command was not executed; no alpha3 backup, Stop or installation occurred. Current physical baseline remains alpha2 AutoONreserve. Await explicit owner approval before any alpha3 device mutation; do not bypass the rejection.

# Item24: compact current server probes — alpha3 candidate

Owner requested five visible rows and triangle expansion for all remaining rows. Source uses the existing persistent disclosure helper, retaining full-list search/sort. New0.9.1-alpha3/dashboard79 candidate is being validated for the same dedicated MT3000; installed alpha2 remains AutoONreserve until the normal update stages. No host/primary-router/fault changes.

# Alpha2 installed on dedicated MT3000 — 24 October 2026

Owner-approved alpha2/source bc8a298 /790193bytes/SHA2b4276fd79c0abfe25b745783920af63f5e33050f9d3f2da2cc4f158f45b1857 installed.86immutable files/modes, freshRPC, actualHTTP8080/HTTPS assets PASS; unrelated settings and accepted terms preserved. Normal Stop20.06s, Start60.84s, explicit reserve selection39.91s. Final AutoONreserve/manual hold target, both selected VPNs DNS+twoHTTPS healthy, monitor4.29s old, current kernel peer data for both profiles and8live latency rows. Actual encrypted190entry final export independently decrypted/read; saved latency-history file validated from that export. [Machine evidence](../../qa/MT3000-ALPHA2-2026-10-24.json).

Initial install harness returned nonzero on uci get of valid empty native_trial(exit1). Package was already installed; no opkg repeat. Independent exact file/mode/settings/RPC/HTTP checks passed, failed evidence retained. No Windows-network, primaryMT6000, unrelated router-network or fault-test changes. Real browser layout/clipboard and independentLAN/24h/IPv6/power-cut acceptance remain unverified. VM prompt evidence remains PARTIAL in its stated scope; published0.9.0 is unchanged. No further device mutation needed.

# Alpha2 final offline/virtual candidate verified

Sourcebc8a298e89d61b63bb27915c5f3135281ca190db; package790193bytes SHA2b4276fd79c0abfe25b745783920af63f5e33050f9d3f2da2cc4f158f45b1857. Exact737app/107QA per runtime/44UI PASS. Actual VM install,86files/modes/HTTP assets and disk history tests PASS. [Candidate receipt](../../qa/OWNER-UI-ALPHA2-2026-10-23.json). Physical alpha1 remains AutoONreserve; no new release or physical alpha2 installation. Native browser unavailable; full LAN/GL/AI-model execution acceptance is not claimed. All23dictated items remain in the saved checklist with delivery gates.

# Alpha2 offline candidate — weekly events and owner follow-up

All23owner requests are saved. New0.9.1-alpha2 sources/package include items9–14and16–23;44UI suites pass, full exact-source CI is next. [Behavior and storage budgets](../OWNER-UI-ALPHA2.md), [executed prompt recipes and limits](../PROMPT-VALIDATION-2026-10-23.md). VM install/components/real missing-dependency repair/setup/diagnostics passed; complete prompt acceptance remains PARTIAL because physical LAN/GL/native Auto and browser tooling are unavailable. Browser layout/clipboard are not accepted. Installed physical alpha1 remains AutoONreserve; no additional installation or release is claimed.

# Owner UI alpha1 installed — Auto ON reserve; new dictation active

Source9daab2b/0.9.1-alpha1/dashboard77/ui54 installed on dedicated MT3000. Exact dual-runtime CI724application/107QA per runtime/40UI PASS. Canonical769169byte IPK SHA91d641ec3beacbef5ffa59e49daa492c26bc0b6d183073c55c69db8fe6de9e5d;84installed files/modes and actually servedHTTP8080/HTTPS bytes PASS. Start63.89s, owner reserve restored35.97s, final AutoONreserve/bothDNS+twoHTTPS healthy/no test faults/full-block.189entry encrypted final export independently decrypt/read verified. Terms retained. Installation harness initially refused byte-identical own config; only documented lifecycle resets of native_until/native_trial changed, all unrelated UCI options preserved; no opkg retry. [Machine evidence](../../qa/MT3000-OWNER-UI-2026-10-23.json).

**Continue the latest saved owner requests(items9–23) in [OWNER-UI-TODO](OWNER-UI-TODO-2026-10-23.md).** New requests include live endpoint addresses, fixed role order, compact cards/tables, day latency graph/recommendation, diagnostic prompts for every Help section and full virtual prompt execution, native dropdown readability, Linux-style one-second terminal, and removing package/page/style noise. These are not yet delivered in alpha1. Save every new dictation immediately. Keep current Auto/reserve undisturbed during offline work; a later install requires its own tested package/checkpoint. Public0.9.0 tags/assets remain immutable.

# Release0.9.0 published and verified —23October2026

**New owner UI work is active:** immediately read [the saved dictation/TODO](OWNER-UI-TODO-2026-10-23.md). Save every additional owner request there by default before implementation. The release is published; new UI requests are not yet implemented/installed and require a new package identity. Do not confuse release completion with completion of this new work.

Owner explicitly confirmed a real release. [GitHub v0.9.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0) and [Gitea v0.9.0](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0) published: no Draft/Pre-release; GitHub Latest. Main contains the release in both histories. GitHub tagf0678decee7e932edb313efecc9e4697cb0569c1; canonical Gitea tag5f7ea5089d82ad1544792c0dac9ee9be3027101f; identical tree14fdf2aac62bea80cf3deb3caf3057afc3825a4c. Both exact commits passed724application/107QA per runtime/39UI, with complementary skips retained. Canonical769849byte IPK SHA7cf93df74cbf72271c93235cdeece7e1e4eaa70fac249bfddeef647af29f287a and checksum/final-source verification JSON independently downloaded from both hosts; hashes match.170Markdown files audited, local links resolve, About updated in both, historical notices added to40GitHub/4Gitea releases without replacing old assets/tags. [Release evidence](../RELEASE-0.9.0.md), [publication receipt](../../qa/RELEASE-0.9.0-PUBLICATION.json).

Private source bundle restore and full fsck PASS. Crash repair affected only the zero-filled index of stale temporary worktree base00; original index retained, worktree files untouched. No router or Windows-network operations in this publication continuation; physical results remain alpha45 baseline. No independentLAN/24h/power-cut/IPv6/currentMT6000-continuous-mode acceptance. Do not reinstall for this documentation-only closure or restart old observers. Final verification-note synchronization/recovery checkpoint follows without moving release tags or changing package bytes. Remaining product acceptance is in [ROADMAP](../ROADMAP.md).

Older chronological entries follow.

# Current: alpha45 first-run flow installed, Auto ON reserve

Read [first-run flow report](FIRST-RUN-FLOW-2026-10-23.md) and [machine evidence](../../qa/MT3000-FIRST-RUN45-2026-10-23.json). Owner additions complete: existing experimental/MIT/own-risk agreement stays first until accepted; then read-only2paragraph/3schematic intro, OK→8step wizard. Green skip below Cancel/Next, clear unchanged-current-settings/no-reset/no-save/no-Auto copy and later Settings route; focused8step EN/RU help with examples in separate tab. Existing accepted terms remain version1; no consent fabricated/reset. Canonical8ce0fb2 product769863bytes SHA10857c90e28e9f8fec01ecec9d059a577f3c22e49e7f090e9996e4fa5974b0f2; exact CI724app/107QA per runtime/39UI PASS.84installed files/modes/protected configs and actual HTTPS/HTTP8080 dashboard75/ui52 PASS. Canonical UI interactions and local browser screenshots PASS. Actual Start57.61s, owner reserve restored, final18:17Berlin AutoON reserve/both DNS+twoHTTPS healthy/no test faults/full block;189entry encrypted final backup verified. Final source/report GitHub+Gitea publication/recovery closure follows privately; no further router action needed. No primary MT6000/Windows network changes; no independentLAN/24h/power-cut or unattended boot claim. Older pending entries are historical.

# Alpha45 installed — actual Start in progress

Exact8ce0fb2 full CI PASS724app/107QA per runtime/39UI. Final769863byte SHA10857c90e28e9f8fec01ecec9d059a577f3c22e49e7f090e9996e4fa5974b0f2 installed;84files/modes/protected configs and actual HTTPS/HTTP8080 dashboard75/ui52 PASS. Canonical UI EN/RU flow checks and local screenshots PASS: agreement first when unaccepted, two-paragraph/three-diagram intro, OK to wizard, bottom green skip and focused8step help. Existing terms acceptance retained, version1 unchanged. Actual Start45 observer is RUNNING; do not send a competing Start/Stop. Wait for start-alpha45 receipt, then restore pre45owner reserve, final snapshot/backup/report and both Git remotes. No test faults or primary-router/Windows changes.

# Alpha45 final wording CI — Auto temporarily OFF

Stop44 PASS,16:10:48UTC; pre45 encrypted backup verified. Visual review of intro/wizard/agreement PASS. User added illustrated intro after initial45 build; final wording now explicitly says agreement→illustrated explanation→eight-step setup. Earlier2ae94dd package dbdd... is superseded and must not be installed. Final candidate769863bytes SHA10857c90e28e9f8fec01ecec9d059a577f3c22e49e7f090e9996e4fa5974b0f2. Repeat exact CI pending; then install/RPC/assets/Start45 and restore owner reserve (reconnect pause runs concurrently with CI). Do not hand over while Auto OFF. No test faults or primary-router/Windows changes.

# Alpha45 first-run flow — final CI RUNNING, not installed

Owner additions: existing typed MIT/experimental/own-risk agreement stays first for unaccepted users; next a read-only two-paragraph/three-schematic operating intro, OK then eight-step wizard. Bottom green skip after navigation, accurate unchanged-existing-config copy, same-origin help tab with all8EN/RU steps/examples. No fake acceptance reset or Auto start. Terms Help registration order corrected. Targeted tests PASS. Canonical product2ae94dd,769811bytes SHAdbddf7c6c9e0959a257a17d7662c2aab1d121d9f851cb3272d8a2484a65e536d. Exact full CI RUNNING. Installed44 remains AutoON reserve, fresh pre45snapshot PASS. Need backup, exactCI PASS, oneStop44/install45/RPC/assets, reconnect pause/Start45, restore owner reserve, final snapshot/backup/QA/report/both Git remotes. Dedicated MT3000 only; no Windows/primary-router changes or test faults.

Older entries:

# Publication completed: GitHub and Gitea feature branch

Owner explicitly approved full-history publication after the earlier review refusal. Source/report checkpoint5fb6ea8 was pushed and independently verified in BOTH GitHub HomenSAI/homensai-gl-mt6000-auto-vpn and Gitea localadmin/homensai-gl-mt6000-auto-vpn, branch feature/recovery-auto-20261023. Complete reachable history audit PASS111commits/2409blobs/80,843,335bytes, no secret-pattern or private-path findings. This closure note is synchronized next. Prior paragraphs saying GitHub is blocked/pending approval are historical and superseded. Main/tags/releases were not changed. Installed44 device state is unchanged by publication.

# Current handover: alpha44 appearance fixes installed, Auto ON reserve

Owner appearance corrections complete. See [alpha44 report](APPEARANCE-2026-10-23.md) and [machine evidence](../../qa/MT3000-APPEARANCE44-2026-10-23.json). No Emergency Stop/note on Language and appearance; other steps unchanged. Soft-green dashboard/recovery link; RU/EN preview immediately rerenders first-step labels/navigation/attribution/link language, preserves other draft fields and performs no save/RPC/reload. Stale MT3000 unsupported copy removed. Product5189933 full724app/107QA per runtime/39UI PASS; canonical765127bytes SHAaabd1cf1839fe1f30538ba9896dddbed3852583e945b3d9ea31f820ffa052d1c.84installed files/modes/protected configs and actual HTTPS/HTTP8080 dashboard74/ui51 PASS. Actual Start57.66s, adaptive10→2→10 PASS, owner reserve restored35.78s. Final17:53Berlin AutoON reserve, both DNS/twoHTTPS healthy, no test faults/full-block.189entry encrypted final backup verified. Final report/source Gitea save and recovery closure follow privately; no further device changes needed. GitHub full-history push remains blocked pending explicit105commit/78MB publication approval. Do not retry it for this UI task. No primary MT6000 or Windows network changes.

Older chronological entries:

# Alpha44 installed — reconnect pause before final Start

Final5189933 CI PASS724app/107QA per runtime/39UI. Installed44:84immutable files/modes/protected configs PASS; actual HTTPS/HTTP8080 dashboard74/ui51 PASS. Canonical44 generated UI interaction check PASS: no Stop on appearance, soft-green recovery link, immediateRU/EN, other draft fields retained, no save/RPC/reload, dashboard link follows locale. Stop43 PASS20.18s at15:47:22UTC; Auto temporarily OFF, waiting reconnect pause before Start44. MUST complete Start44, restore pre-upgrade owner reserve, final snapshot/backup and report/Gitea closure before handing over. Earlier38edc52 package superseded; only765127byte SHAaabd1cf1839fe1f30538ba9896dddbed3852583e945b3d9ea31f820ffa052d1c is final. No test faults introduced; primary router/Windows networking unchanged.

Older entries follow.

# Active alpha44 appearance correction — final CI in progress

Owner requested no Emergency Stop in Language and appearance, soft-green dashboard/recovery escape, immediate EN/RU preview on the first step. Implemented/tested locally in44, fresh assets dashboard74/ui51. Corrected stale MT3000 unsupported/help copy. Exact final source5189933 full CI RUNNING;765127byte canonical SHAaabd1cf1839fe1f30538ba9896dddbed3852583e945b3d9ea31f820ffa052d1c. Earlier38edc52 CI passed but its package is superseded and must not be installed. Installed43 remains AutoON reserve, pre44snapshot and189entry encrypted backup verified. After final CI: one Stop43/install44/RPC/assets, reconnect pause/Start44, restore pre-upgrade owner reserve selection and final snapshot/backup/report/Gitea. No new faults or main-router/Windows network changes. GitHub push remains blocked pending explicit historical payload approval; do not retry for this UI task.

Historical entries follow.

# Current handover: installed alpha43 verified ON, owner reserve restored

Latest status supersedes chronological entries below. Read [owner status](OWNER-STATUS-2026-10-23.md) and [complete saved plan](OWNER-IDEAS-2026-10-23.md). All owner UI refinements and selected animation1 are installed in43, plus bounded adaptive2s startup polling with normal10s after readiness. Product85211db, exact CI724app/107QA per runtime/39UI PASS, canonical764983bytes SHA7b4ea2dee269a68d1fb2517f21ceef30c478d0fc4460480c267554d66d44a023.84files/modes/protected configs and actual served HTTPS/HTTP8080 PASS. Start59.81s and actual10→2→10 cadence PASS; no substantial overall startup speedup claimed. Actual manual reserve/90s/primary144.52s PASS with AutoON; owner reserve restored34.67s. Final17:29Berlin AutoON reserve, both DNS/twoHTTPS healthy, no test faults/full-block. Actual43 UI-frame replay passes red/static DNS error and green/moving healthy selections.189entry encrypted recovery export verified.

Source and final report saved/remote-verified in authorized Gitea feature branch at2fe3532. Source bundle restore passed; final documentation recovery receipt follows privately. No further device changes needed. Do not resume old observers/faults. Primary MT6000/Windows networking unchanged. Router-only IPv4 acceptance; no independentLAN/24hsoak/powercut or unattended bootAuto claim.

Historical chronological entries:

# Active alpha43 adaptive polling completion

Owner additionally requested faster startup polling. Alpha42 UI installed/served but Auto remains deliberately OFF during the upgrade. New43source85211db targets2s only during matching startup<=180s, restores configured10s after readiness, never overlaps monitor rounds or weakens proof/worker deadlines. Canonical43package764983bytes SHA7b4ea2dee269a68d1fb2517f21ceef30c478d0fc4460480c267554d66d44a023. Full43CI RUNNING. Do not Start/install unaccepted43. After CI: install43/RPC/assets, Start with cadence evidence, manual roundtrip and restore pre-upgrade owner reserve preference, final snapshot/backup/report/Gitea. No active test faults.

Older history follows.

# Active alpha42 installation — chosen running dots

Owner chose variant1 and requested completion of all saved UI items. Alpha42 canonical source bf2d081, full dual-runtime CI PASS723app/107QA and39UI; package764669bytes SHA12444dccb45dc943ecd630ccc62861e40a97a1848b941e2437c1e1cceb49eee5. Installed84files/modes/protected configs PASS; actual HTTPS/HTTP8080 assets PASS. Auto temporarily OFF after verified Stop41 (20.19s), during reconnect pause before Start42. Must finish Start, actual manual roundtrip, restore pre-upgrade owner reserve preference, final snapshot/backup/report/Gitea save. Do not call hardware acceptance complete yet. No test faults introduced. No primary MT6000/Windows network changes.

Older history follows.

# Current handover: verified alpha41 ON; alpha42 awaits animation choice

Read [the full owner idea/resume plan](OWNER-IDEAS-2026-10-23.md) and [operator acceptance](UI-OPERATOR-2026-10-23.md). Installed41 product source8239552, exact CI PASS723app/107QA per runtime/39UI,84file/mode/protected-config checks and actual HTTPS/HTTP8080 assets PASS. Start60.36s, actual operator reserve/90s hold/primary cycle151.65s PASS without disabling Auto or using Resume. Actual installed UI frame replay PASS. Final14:39UTC snapshot: Auto ON, reserve selected by later operator action, both VPN DNS/twoHTTPS healthy, monitor age5.15s, no test faults/full block. Preserve the operator's choice. Raw failures remain retained.

Current source42 is UNINSTALLED WIP:1–24h slider, equal cards/eligible-only action, shorter copy/destination-only pending text, targeted checks PASS. Owner explicitly requested four animation variants before choosing; previews prepared and interaction-tested, none chosen or integrated. Finish42 only after that input, then canonical/full CI/build/install. Do not call42 hardware-accepted or replace41 with a placeholder-hash build. No active fault/observer; no Windows/primary MT6000 changes. Source41 is saved in the approved Gitea feature branch; latest42 recovery checkpoint follows. Older headings below are chronological history.

# Active alpha41 operator/visibility completion — 23 October 2026

Read [the complete owner idea/resume plan](OWNER-IDEAS-2026-10-23.md). Installed alpha40 Auto is ON/OBSERVING on primary. Start40 PASS62.34s. First manual40 reserve refused VENDOR-WORKER-QUIET-UNVERIFIED and rolled back; second actual forced reserve/primary test PASS58.31s without disabling Auto,90verified concurrent worker samples/no errors. New alpha41 WIP source implements all later operator text/color/monitor/footer/advanced-Stop requirements and router-clock-based UI ages, with bounded retry of unverified quiet samples. It is not installed or fully CI accepted yet. Freeze/version metadata/build/CI/install and actual final cycle remain. Last Gitea saved a050116; newer commits currently local. No active fault/observer; dedicated MT3000 only. Keep provider AUTH_FAILED failures and the refused manual attempt in the report. Exact evidence/next steps are in the plan.

# Active alpha40 final button correction — 23 October 2026

Read [owner feedback / exact resume plan](OWNER-IDEAS-2026-10-23.md). Alpha39 is installed and served on both pinned HTTPS and user HTTP8080; new dashboard70/ui47 include all requested UI changes. First Start39 received OpenVPN AUTH_FAILED and safely stopped. Its observer completed with cleanup244.48s; owned links absent. Auto is currently OFF, not running. No active fault/observer remains. Alpha40 local source corrects the public Stop timestamp regression found on this refusal; canonical package762017bytes/SHA8cc1a3812ea08c41dc8b9c01523c4c04a4da7e768b3b92c45477a77b9f144f54. Exact-source CI, install/RPC registration, successful Start and actual manual pair cycle are pending. Last Gitea checkpoint a050116; all later source/plan checkpoints are local. Do not claim these pending checks complete. Keep actual authentication failures; do not change credentials or primary MT6000/Windows networking. Current owner executor claim remains active.

# Active alpha39 owner UI batch — local checkpoint, not installed

Read [owner feedback and resume plan](OWNER-IDEAS-2026-10-23.md). Installed alpha38 Auto remains ON/OBSERVING. All current/new owner UI requirements have local source implementations with targeted Node checks: ready-state toggle locking; three-level graphs; rounded manual card-buttons and explicit selected policy separate from Internet health; primary/reserve health-bar labels; actual Overview daily graph in all designs; corrected GL.iNet/OpenWrt version fields and removed stale warning. New assets dashboard70/ui47 avoid reusing old cached assets after reload. Alpha39 is uninstalled WIP: canonical package/hash pins, exact CI, one Stop38, install/RPC registration, Start39 and actual manual-cycle acceptance still pending. Preserve these distinctions after a crash. Exact code/evidence and next actions are in the plan. Dedicated MT3000 only; never resume old observers or change Windows/primary MT6000.

# Active owner feedback / durable crash-resume point — 23 October 2026

Read [OWNER-IDEAS-2026-10-23.md](OWNER-IDEAS-2026-10-23.md) first. Owner explicitly requested recording later ideas without interrupting current Auto button/graph fixes, preserving the exact crash-resume state, then installing completed fixes on MT3000. Alpha38 is installed and Auto ON after62.73s verified Start; RPC registration required a second normal reload after upgrade. New source is uninstalled: three plotted graph levels and lock through RUNNING/PAIR-WAITING-PROBES. Bump alpha39 before next installation. Manual card-buttons, rounded whole-panel border, explicit selected route vs Internet health, labelled Step1 bars and missing Overview daily graph are queued, not completed. Last Gitea checkpoint a050116; later local commits/WIP need save after testing. Full resume order and evidence pointers are in the plan. Do not confuse older alpha37/38 success with these new UI requirements being accepted.

# Active Auto power-button transition lock — 23 October 2026

Owner reported repeat clicks during startup/Stop and requested locking the normal toggle for the entire operation. Alpha38 candidate adds correlated queued/STARTING/STOPPING backend display phases and retains a UI command lock beyond RPC ACK until a fresh completed controller observation. Redraw/reload keeps transition locking; Emergency Stop remains available during startup, repeated pending Stop is disabled. Focused JS duplicate-click/ACK/redraw/reload/completion checks PASS. Exact-source full CI, installation and fresh hardware Start/Stop confirmation are still pending; installed alpha37 Auto remains ON. Owner said another UI observation would follow; incorporate it into this active task. Dedicated MT3000 only.

# MT3000 alpha37 installed acceptance — 23 October 2026

The owner authorized complete tracked source plus current-task fixes to the existing Gitea repository and `feature/recovery-auto-20261023` only. Source c477c5d is already saved there; no GitHub/main/tag publication is claimed. Alpha37 is installed: 84 file/mode checks, protected configurations and actual served assets PASS. Exact-source dual-runtime CI PASS717app/107QA and37UI suites. Actual post-upgrade automatic cycle PASS133.01s with exact one automatic commit/one return; manual override/90s hold/primary/resume/bad-reserve refusal PASS181.84s. Weekly export and graceful service-restart persistence PASS8.43s. Known false pre-Start alpha36 records were corrected after daemon quiescence and verified after startup; the first overwritten correction is retained as a failed durability check.

Final retry Start PASS58.07s after one retained upstream AUTH_FAILED refusal; final37.42s/7sample acceptance PASS. Auto LEFT ON, primary selected, manual hold absent, both profiles DNS/twoHTTPS PASS, test fault tables removed, normal VPN-only guard valid. Final189entry encrypted/decrypt-read-verified export retained privately. Read [the consolidated report](../MT3000-AUTO-TEST-REPORT-2026-10-23.md) and [machine evidence](../../qa/MT3000-AUTO-MATRIX-2026-10-23.json). Dedicated MT3000 only; no Windows/primary MT6000 changes. Owner chose router-only evidence. External LAN, actual browser interaction, 24h soak, physical power-cut and unattended boot Auto resume remain unverified/unimplemented. Older entries below are chronological history.

# Active expanded MT3000 acceptance and UI/statistics work — 23 October 2026

Owner explicitly continued testing and added statistics/UI/manual requirements. Read [the current matrix and WIP checkpoint](AUTO-MATRIX-2026-10-23.md). Actual alpha35 nine-scenario/19m23s matrix PASS, 3 reserve commits/3 returns, test cleanup confirmed. Installed alpha35 Auto stays active. Unreleased alpha36 sources now contain statistics and UI fixes; full verification, manual Auto override, canonical build/installation and post-upgrade tests are still pending. Never install the earlier stale alpha36 artifact or call the WIP hardware accepted. Dedicated MT3000 only; no Windows or primary MT6000 changes.

# Owner-resumed crash recovery — 23 October 2026

Owner resumed and requested final automatic switching acceptance. Fresh results are in [the recovery report](RECOVERY-2026-10-23.md) and [machine-readable evidence](../../qa/AUTO-RECOVERY-2026-10-23.json). **Auto LEFT RUNNING on the dedicated MT3000**, alpha35, continuous-pair OBSERVING; final 66.64-second/7-sample read-only acceptance PASS. Two actual failover/return cycles (131.51/131.70 seconds), native crash recovery (20.18 seconds), Stop during startup and 80 installed file/mode checks passed. Exact original-source dual-runtime CI PASS681app/107QA per runtime/34UI; no product change/reinstall. One rapid startup received OpenVPN AUTH_FAILED and safely stopped; unchanged-config final retry after a pause PASS62.08seconds. This failure is retained. Automatic switching works in router-probed IPv4 scope; unattended production remains PARTIAL: external LAN, intermittent upstream rejection, boot auto-resume and long soak remain open. The application services/Auto remain active; old observers were not resumed. Primary MT6000 and Windows networking unchanged. Older entries below are historical.

# Active router-only completion — 22 October 2026

## Immediate Auto + chart handover completed

Alpha35 is installed and hardware-accepted on the dedicated MT3000 in router-probed IPv4 scope. Three complete actual cycles, ordinary/startup Stop, native crash recovery, settled reboot and postboot Start60.09s/final Stop14.07s passed. Last23state checks passed: Auto/clients off, services running, original policy/bridge/preparation retained, no fault/guard/fixture. Final189entry encrypted/decrypt-read-verified export is private/completion-20261022b/handover35-config.enc. No further hardware mutations are needed for this handover.

Immutable v0.9.0-alpha35 is published in GitHub and Gitea, with independently downloaded IPK/checksum verified SHA220261bbf1e876c2ca0429b491ab79b7a4f0d1e7ef3bfb34185370d484e07465,740585bytes. Canonical/local tagaa7eb85884a9da1b48f5544586e738f0a5944a13 and public tagea8d8e2668ca1220fce833f5e99ab5d7e6d8ad52 have identical trees. Both main histories contain the release; canonical protected mainb9ff460026cd275943b3a18ccfcb4c5732e70b9d passed all original checks after correcting only test fixture isolation. Exact b9ff dual-runtime CI PASS681app/107QA per runtime/34UI, package unchanged. Temporary Gitea authorization removed and absence verified. Publication facts: qa/ALPHA35-PUBLICATION.json. Final documentation-only synchronization follows without retagging/reinstalling.

Owner test: follow docs/AUTO-QUICKSTART.ru.md, refresh Ctrl+F5, then Start once and allow about one minute. Green/blue chart shows primary/reserve; Stop remains available. Independent external-LAN/MT6000 acceptance, full multireserve hierarchy, captive interception, broader stress/Telegram lab/server CI and long traffic soak remain explicitly unfinished in the eleven-item matrix. The later owner priority was working Auto today, not unrestricted scope growth. Older paragraphs below are chronological evidence, not the latest state.

20:41 UTC: alpha35 published in GitHub main/release publicea8d8e2668ca1220fce833f5e99ab5d7e6d8ad52 and Gitea release canonicalaa7eb85884a9da1b48f5544586e738f0a5944a13, exact identical release trees/package downloads verified; local canonical tag imported. Own temporary Gitea token removed and absence verified (UID1000 required with cap-drop; initial UID0 lacked DAC write permission). Postboot Start PASS60.09s and final Stop PASS14.07s; final23state checks and189entry encrypted export PASS, all hardware changes ended. Final aa7 full CI PASS;897 Git archive blobs/modes and complete20MB bundle verified. Protected Gitea main merge REFUSED on26 legacy test fixture errors: new pair helpers used unpatched agent.RUNTIME/PERSIST and touched container /var/run instead of each native fixture. Five test fixtures now share the same temporary paths across native/agent; no product/package/guard change. Repeat exact CI/protected merge pending. Public releases/tags remain immutable.

20:29 UTC release verification correction: final exact-HEAD CI refused stale install-kit SHA/size after the manifest hash was filled; fixed kit to canonical alpha35 SHA/740585bytes. Product/package bytes are unchanged. Complete Git bundle verification passed; first source-export blob comparison exposed Windows text=auto CRLF export despite core.autocrlf=false, not lost source. Exact LF archive correction/reverification and new final-HEAD CI follow. These failed checks are retained; publication has not started.

20:24 UTC: alpha35 physical acceptance complete within the defined router-probed IPv4 scope. Complete cycle PASS124.94s (plus two alpha34 cycles126.98/131.47s), Start64.08s; actual native SIGKILL recovery PASS20.21s, monitor unchanged/profiles off/guard absent/budget+certificate unchanged/revision revoked. Actual Stop during STARTING PASS: ACK1.33s, cleanup10.35s, stale Start rejected. Actual30sample auto_live RPC run PASS. Actual pinned HTTPS dashboard/styles equal canonical IPK. Reboot final23checks PASS at121s uptime; initial45s check failed only missing services, both services observed running by92s. Auto and clients remain off, original policy/preparation retained. Final backup/recovery and exact release-HEAD CI/publication in progress. See release notes and Russian quick start; deferred eleven-item backlog remains explicitly open.

20:15 UTC: second alpha34 cycle PASS131.47seconds in the same continuous session; ordinary Stop PASS16.1seconds, original owned profiles off and guard absent. Alpha35 exact sourcebeabca86d7a7106102284338a3d5a170e9b21709 complete CI PASS681 app/107QA per runtime/34UI; reproducible740585bytes SHA220261bbf1e876c2ca0429b491ab79b7a4f0d1e7ef3bfb34185370d484e07465. Fresh189-entry encrypted/decrypt-verified backup; actual install80files/modes/protected configurations PASS. Actual alpha35 Start PASS64.1seconds; its full fault/return test is RUNNING. Desktop and actual390px iframe synthetic graph layouts visually checked, readable/no cropped graph. Live read-only RPC captured reserve and primary at roughly2-3sec; collector exceeded its200sec transport budget before80iterations finished, so its overall run is PARTIAL, not PASS. Native crash recovery, Stop during startup, final receipts/publication remain pending.

20:08 UTC: first complete alpha34 continuous Auto hardware cycle PASS126.98seconds. Actual120sec bounded WG packet-drop -> SOURCE-FAILED/APPLYING -> COMMITTED on OpenVPN -> fault removal -> automatic original WG return/ROLLED-BACK -> OBSERVING. Both paths passed DNS/two HTTPS and matched their distinct pre-recorded exit hashes; actual rule order checked at reserve and restored primary. Proof scope router-probed-ipv4, external LAN false. Second cycle in the same session RUNNING; alpha35 full CI RUNNING. No broad completion or final release claim yet. Private pair34-failover-01.jsonl and receipt bind exact script/output/device.

20:05 UTC: alpha34 source86bd49beddaa1a1174e2b36a1b8af53fe0df4708 full CI PASS681 app/107QA per runtime,34UI; reproducible740412-byte IPK SHA0743c1312fd7d53b0de19dddf3aa4ff8aba60a2ab8520f5adf8eabce506fa00e installed80files/modes/protected configurations PASS. Exact derived-process via/mark synchronization passed actual isolated vendor Lua/UCI. Cold Start failed twice: the second run captured seven server AUTH_FAILED replies and repeated OpenVPN teardown/retry, while shared locks/queues were free. Owner confirms unchanged credentials. A later unchanged-config Start passed56.1s; transient authentication cause remains UNKNOWN. Actual failover/return with the atomic fix is RUNNING, not yet PASS. Source alpha35 also suppresses unrelated Wi-Fi setup via stock ifup -w (not a wait option), records RESTORING before automatic return, and adapts graph labels/width for small screens. Full CI/install of alpha35 pending. Public alpha27 remains the released baseline.

Latest actual state: alpha32 installed,80 files/modes and protected configs verified; new678 app/107QA per runtime/34UI matrix PASS. Actual Start58.1seconds PASS and Stop14.1seconds PASS, both owned profiles restored off/guard absent. Actual fault switching is NOT accepted: precise refusal POLICY-IDENTITY-CHANGED, rolled back; new module identity handling kept the session alive to observe/retry instead of the prior daemon crash. Synthetic isolated UCI reorder on actual vendor libuci PASS. Alpha33 source33df1ca1bedf792591331b011dc50a58ce243a7d adds sanitized apply failure location/derived-rule context; full CI/actual diagnosis pending. Graph is installed but actual visual/live acceptance remains pending. Do not report Auto ready yet.

18:11 UTC checkpoint: alpha31 source8282011dd2e1d88db696eb4e14f7e4b31fef35f9 full CI PASS (675 app+107QA per runtime/33UI), exact736330-byte IPK SHA4e624cb7938d0f6413274d0819cc03a8b332be87dd1308df42e468fed2d3a848 installed on actual MT3000;79 files/modes and protected configs verified. Fresh187-entry encrypted recovery export verified. Thirty-minute read-only resource baseline60samples/0failures completed; I/O counters unavailable in vendor kernel. Auto remains off pending physical Start/fault/return/Stop acceptance. See [pair operations](../PAIR-AUTO-OPERATIONS-2026-10-22.md). Older WIP state below is chronological history.

Immediate owner priority: usable two-channel Auto today, target 23:00 Europe/Berlin. The broader eleven-item list is retained but secondary. New source adds explicit continuous-pair control with automatic existing-profile startup, bounded per-transition native leases, a persistent rolling attempt budget, Stop/restart ownership recovery and router-probed-ipv4 scope. It never creates an external-LAN certificate. Twelve focused Linux tests and Auto/readiness Node tests pass; complete matrix, installation and physical acceptance are pending. Alpha27 remains installed and Auto off. Do not report the new mode working before actual acceptance.

Owner explicitly approved all eleven router-only completion items after alpha27 publication. Follow [the active completion matrix](ROUTER-ONLY-COMPLETION-2026-10-22.md). Fresh work starts at 1ec7bc5574c828a10d17d0b6c15536219605243f; alpha27 remains the immutable released baseline. Refresh identity/recovery before device writes. Preserve Windows networking and primary MT6000. External-LAN certification is excluded. Old completion/pause entries below describe earlier windows.

# Dual release publication — 22 October 2026

Owner requested release publication in both GitHub and primary Gitea. v0.9.0-alpha27 is now a published prerelease in both services, with the 728294-byte IPK independently downloaded and verified against SHA256 5357b80acb21ac7ee0bc5e9a36082318adf59004d15184c6ce3e2a936e4acad6. Each release includes its SHA256 text attachment. GitHub's checksum file uses CRLF and Gitea's uses LF; both name the same package and hash. No existing release or tag was overwritten.

Gitea and local Git canonical tag point to de9ab00a007816f5b723e112c3c75c2d393a71af; immutable GitHub tag points to a05018bee9c61379a140f2a59aaa2c8a03dbe686. Their complete source trees are identical. Main already contains the release in both histories; later documentation commits preserve the released package. See [publication receipt](../../qa/ALPHA27-PUBLICATION.json) and [release notes](../../releases/v0.9.0-alpha27.md). The temporary local release token was removed and its absence verified after Gitea refused API self-revocation; no secret was persisted. Only documentation bookkeeping follows; product, router and acceptance scope are unchanged.

# COMPLETE — alpha27 release and main verification, 22 October 2026

Released v0.9.0-alpha27: GitHub release/tag/source snapshot a05018bee9c61379a140f2a59aaa2c8a03dbe686; canonical Gitea main de9ab00a007816f5b723e112c3c75c2d393a71af verified through protected Gitflow checks and normal FF save. Public main/local main verified. Release IPK and checksum independently downloaded and checked; package SHA5357b80acb21ac7ee0bc5e9a36082318adf59004d15184c6ce3e2a936e4acad6,728294bytes. Later documentation-only main snapshots may descend from the release object without changing this package.

Actual MT3000 alpha27 acceptance completed:655 app+107 QA per runtime/33 Node UI,40 lab checks; actual calibration/Auto fault/reserve/recovery/Stop/manual operations, active native SIGKILL recovery, monitor off/on, final persistent reboot19 checks. Installed77 payload files and served HTTPS assets match canonical IPK. Auto and both clients off after tests, monitor/native supervisor running, default external-lan scope, no fault/guard/fixture. Native packet decisions were verified with ordinary router-hosted IPv4 client; external Windows forwarding remains unverified by the owner's no-host-changes instruction. No external certificate, MT6000 hardware requalification, six-hour traffic soak or power-cut acceptance is claimed.

Final187-entry encrypted/DPAPI-decrypt-read-verified configuration backup includes own state/preserved SFE autoload. Complete-history18MB Git bundle verification PASS. All882 source export files match canonical Git blobs after the configured Windows CRLF export normalization (405 text files); executable modes verified. The earlier tar assertion was a normalization mismatch, not lost files. Recovery receipts are private/acceptance-20261022/final-recovery-receipt.json and final-alpha27-config.receipt.json.

Physical work ended within the six-hour window; only Git publication bookkeeping followed. No automatic router/VM/fixture tests should resume. Old entries below are history. The owner can start a fresh task explicitly.

# Published release checkpoint — 22 October, 15:57 UTC

GitHub main and immutable v0.9.0-alpha27 are published at a05018bee9c61379a140f2a59aaa2c8a03dbe686. Exact canonical source de9ab00a007816f5b723e112c3c75c2d393a71af, final CI PASS, downloaded IPK/checksum verified SHA5357b80acb21ac7ee0bc5e9a36082318adf59004d15184c6ce3e2a936e4acad6. Local main fast-forward verified to the same public commit. Canonical source and publication branches saved to primary Gitea. Protected Gitea default-main synchronization is still finalizing after a local clone/working-system error; no force/protection bypass.

Physical six-hour window is CLOSED as completed testing, not an owner pause. No automated tests/fixtures/router changes should resume. MT3000 alpha27 installed; native happy path/fault/manual and active supervisor crash recovery passed in hosted IPv4 scope; monitor off/on and corrected reboot19 checks passed. Final Auto off, selected clients disabled/auto0, stock arbitration boot disabled, SFE autoload preserved/masked, HNAT disabled, services monitoring. Windows and primary MT6000 unchanged. External LAN remains unverified and hosted certificate cannot satisfy external scope.

Final supported backup187 entries encrypted and DPAPI-decrypt/read verified; own state and preserved autoload explicitly included. Complete-history source bundle verification PASS. Source tar export normalization verification is being reconciled; do not claim exact blob restoration from that tar yet. Git-only final bookkeeping remains; old entries below are history.

# Latest status — 22 October 2026, 15:33 UTC

Final product:0.9.0-alpha27-1, dashboard69/ui46. Exact CI655 app+107 QA per runtime/33 UI PASS; canonical728294-byte IPK SHA5357b80acb21ac7ee0bc5e9a36082318adf59004d15184c6ce3e2a936e4acad6 installed and77 payload files/modes plus actual HTTPS assets verified. Native calibration/Auto source fault/reserve/automatic return/Stop/manual reserve and return PASS in hosted IPv4 scope. Actual alpha27 SIGKILL during WAIT-CLIENT recovered without lease/quota reset or false certificate; original DNS/HTTPS passed. Monitor off/on5 checks PASS. Final main publication/ref/download verification is the remaining release step.

After reboot, stock clients came up and SFE core reloaded while app Auto stayed disabled. Authoritative SFE cause: /etc/modules.d/09-shortcut-fe, not shortcut-fe init (which skips when HNAT0). Under the explicit dedicated-router repair authority, preserved that exact file outside autoload, disabled competing stock VPN/SFE boot entries, set only selected clients disabled1/auto0 and used normal non-force accelerator stop/unload. Second reboot: all19 final checks PASS, both clients/Auto off, no guard/fault/fixture, source policy preserved, monitor/native supervisor running, HNAT disabled/SFE absent. See operations log for exact hashes/undo.

External Windows forwarding remains UNVERIFIED: owner refused host route/NIC changes. Hosted evidence is never an external certificate; default scope is external-lan, Auto off after tests. Primary MT6000/host Wi-Fi unchanged. No six-hour traffic soak or physical power-cut claim. Earlier entries below are chronological history, not current blockers.

# Current work — 22 October 2026

Owner resumed completion, full testing and the dedicated GL-MT3000 hardware window. Later instructions require saving critical/long operations to local Git and this current state, publishing the completed release on main, and offering MT6000/MT3000 model selection in setup/settings. This is active work, not a pause. Primary MT6000/host Wi-Fi and Windows network settings remain excluded from changes.

## Verified in this session

- Exact committed source a502a0a59ef1179ff78e1e72d2a5f9dcfe0775b2 passed canonical offline CI on Python 3.9/Lua and Python 3.11/Node. Each runtime ran 631 application and 106 QA tests; 33 Node suites ran on 3.11. Fifteen application Lua skips in 3.11 are covered on 3.9; fifteen QA environment skips in 3.9 are covered on 3.11. Reproducible IPK: 717313 bytes, SHA256 4d26c4a64611908f552d325e1b0712a50d57b1f7349218fa4ff15a3a89154700. Receipt: .git/handoff/ci-a502a0a59ef1179ff78e1e72d2a5f9dcfe0775b2-dcfea2eaef334883900bca2f66687a96.receipt.json.
- Initial cable attempt failed while Ethernet reported Disconnected; after owner confirmation, fresh Ethernet 1Gbps, ping 2/2 and pinned cable-only SSH succeeded. Actual board glinet,mt3000-snand. This supersedes the transient connection failure.
- Actual installed alpha19: all 73 program files/modes match the canonical package. Nine health checks pass: monitor-only, sole monitor instance, native/optional functions off, terms1, CalmB, no transaction/owned guard. Onboarding is still incomplete; no owner wizard choices were fabricated.
- Actual RPC 19/19 pass, including unsupported Auto/manual refusal, Stop/revision/replay/deduplication and no false path confirmation. No real channel transition occurred. Network/wireless/firewall/DHCP/route-policy/app config, kernel route/rule hashes and boot link unchanged.
- Actual monitor SIGTERM/procd recovery 8/8 pass in 7.5s, with fresh status from the replacement process. This is graceful monitor loss, not native transaction recovery/power-loss acceptance.
- Private readiness model now rejects malformed boolean/binding evidence and negative constructor time; 12 tests pass on Python3.9. Runtime witness9 tests pass. Diagnostic queue30 tests pass with root-owned isolated fixtures. The first non-root fixture run failed honestly because ownership validation returned UNVERIFIED. Extended consumer/lab batch stopped at missing /vendor fixture mount; it is incomplete, not PASS.

Private receipts and scripts: private/acceptance-20261022/. No credentials or raw profile configuration belong in Git. Earlier runtime-witness work and history remain in LIMIT-CHECKPOINT-2026-10-21.md.

## Active work and not done

### Checkpoint 09:47 UTC — model selection implemented, release not yet published

- Implemented Automatic/MT6000/MT3000 choice in first-run and Settings aggregate editor, actual hardware display, correct device attribution, reload persistence, backwards-compatible old callers and rejection of a mismatched model in both Python and the final Lua writer. Model preference does not grant controller capability. Native diagnostics also refuse mismatched preferences.
- Versioned WIP is alpha20/dashboard69/ui46. Focused Python3.9/Lua checks38/38 PASS; all33 Node UI suites PASS. Initial UI run stopped at the old diagnostic count39 after adding two explained codes; expected count41 and new request shape were corrected and full run repeated. Exact-commit full CI and canonical alpha20 package are NOT yet done.
- Additional offline checks completed: exact-source vendor consumer3/3, transaction engine9/9 (including200 fault combinations), isolated child process crash20/20, synthetic cascade256series/2048steps with0invariant failures. These are model/container tests, not physical switching.
- Owner now explicitly authorizes all necessary changes and real manual/automatic switches on the dedicated MT3000, and requires documentation plus the existing launch prompt to record prerequisites discovered. Work window is3–4hours; single executor claim until13:45UTC. Other heartbeat threads must defer. No successful physical switching claim is added by this checkpoint.
- Next: fresh encrypted recovery export; complete justified bounded OpenVPN settling/rollback path, physical channel tests with real traffic and application integration; update launch prompt and documentation. Final release/main publication follows final-source validation. Old failed/STOPPED results remain preserved.

### Recovery checkpoint 09:48 UTC

- New pre-switch supported configuration export completed on the actual MT3000:175 archive entries; required configuration/shadow entries and full archive reads verified. AES-GCM encrypt and independently DPAPI-decrypt/read comparison succeeded in memory; no plaintext backup persisted. Encrypted artifact SHA25612f35324594e417f9be08b10368845dac5514636125f9e4578feea0eed3f9938. Private receipt: private/acceptance-20261022/pre-switch-config.receipt.json. This is configuration recovery, not a full-flash/bootloader recovery proof.
- Owner explicitly grants full necessary control/remediation of the dedicated MT3000, including settings changes, switching and persona/error scenarios. Record each obstacle, why it mattered, exact fix and verification in documentation and the existing launch prompt. This supersedes earlier router-only mutation/unsaved-wizard restrictions within this active test window. It does not authorize changes to the primary MT6000/host Wi-Fi/network routes, secret publication or invented acceptance.
- No VPN activation or physical channel switch has occurred in the new session yet; preparation is complete and active trials follow.

### Acceleration checkpoint 09:52 UTC

- Actual MT3000 HNAT was enabled and shortcut_fe loaded. Inspected/pinned stock controls, then ran the exact installed preparation function under the owner's explicit remediation authority. HNAT config0/runtime disabled, SFE core absent;7/7 checks PASS. Protected/app config hashes, monitor-only and disabled clients preserved; management remains accessible. No forced removal or firewall restart. Persistent acceleration setting is intentionally retained for failover tests.
- Observations, mechanism, exact change and verification: [MT3000 operations log](../MT3000-OPERATIONS-2026-10-22.md). Reboot persistence and actual switching still open. Existing launch prompt will be updated with these prerequisites in the next code batch.
- Owner expanded the absence/work window to six hours. Single active interactive executor claim extends to15:55UTC; scheduler threads must defer while it is live. Work is active, not paused.

### Physical WG checkpoint 10:05 UTC

- Two real WG cycles completed: actual interface/fresh handshake,17 samples each, unchanged safety limits, independent cleanup/stock boot restoration PASS at about42s.19 isolated updated hash/version-pin regressions PASS. New4check parser/socket binding suite PASS. Acceleration remains disabled; fresh post-trial kernel/queue readback is clean.
- Physical Windows cable DNS/HTTPS did NOT pass. Synchronized second trial repeatedly returned TCP10051 and DNS timeout while router handshake was fresh. Preserve this as a real datapath failure, distinct from successful interface lifecycle/cleanup. Host Ethernet gateway exists and no Windows routes/NIC settings were changed.
- Next actual diagnostic must capture active marked route tables/DNS ports/counters; post-stop blackhole/2153 redirect alone cannot explain an active failure. Detailed evidence and interpretation are in the operations log. No real app manual/Auto acceptance yet. Product remains committed alpha20 WIP; installed device remains alpha19 monitor-only.

### Active-path / client prerequisite checkpoint 10:26 UTC

- Third real WG cycle: active route-get confirms marked LAN traffic chooses wgclient1/table1001; per-policy DNS listeners exist. Independent cleanup PASS; Windows client data still FAIL. Ethernet IgnoreDefaultRoutes is enabled; bound public Find-NetRoute returns1231. Owner explicitly REFUSED temporary host routes. The prepared route plan was Plan-only and never executed. Keep Windows network unchanged.
- Fixed the public LAN helper's hidden route writes (including former CheckOnly mutation): sockets now bind interface/source, HTTPS uses validated TLS and total deadlines, no New/Remove-NetRoute. Added read-only ProbeOnly and clearer route refusal. Native PowerShell self-tests, replay/DNS parsing and compiled HTTPS scope rejection PASS. External data acceptance is still not established.
- Updated the existing installation prompt, continuation prompt and helper documentation with both models, encrypted recovery, actual acceleration/FW3/queue requirements and host/hosted-witness boundaries. Code is alpha21 WIP; all33 Node UI suites and native PowerShell helper self-tests PASS. Final exact-commit CI/package/release remain pending; installed alpha19 is unchanged.
- Next: owned MT3000 namespace/veth forwarding client and cleanup, bounded OpenVPN lifecycle, reviewed real manual/Auto adapter. Hosted evidence must never be relabelled as an external-LAN certificate.

### Namespace lifecycle checkpoint 10:38 UTC

- Implemented lab/mt3000_lan_fixture.py;10 isolated scope/identity/cleanup regressions PASS. Exact physical board/subnet plus DHCP/reservation/lease/ARP checks passed. No host changes or existing VPN/profile edits.
- Actual45s MT3000 fixture: namespace/veth created, isolated client pinged LAN gateway, guardian cleanup PASS. Independent post-cleanup6/6 readback PASS: namespace/veth/active pointer absent, original bridge MAC/ifindex preserved. Live inspection arrived after expiry and remains INCOMPLETE. This proves fixture lifecycle/management preservation only, not forwarded DNS/HTTPS, process-loss recovery or external-LAN safety.
- Next: parent/guardian process-loss cleanup, then real VPN data through the hosted ordinary-LAN client and MT3000 adapter integration. No app Auto/manual transition has passed yet.

### Fixture owner-loss checkpoint 10:41 UTC

- Actual exact-owner SIGKILL test PASS: fresh live source/PID/start/namespace/MAC checks preceded the single owned-process kill. Expected foreground/controller exit=-1 retained. Independent guardian cleanup then independently verified7/7 PASS, including resource absence and unchanged bridge MAC/index. During active fixture memory208604KiB remained available.
- Added bounded reciprocal parent recovery for guardian death/stall; physical guardian-loss/stall validation is pending next. Native/Auto remains off and neither VPN was started in these fixture-only faults. Do not turn this result into native transaction or external-LAN acceptance.

### Fixture guardian-loss checkpoint 10:42 UTC

- Actual exact-guardian SIGKILL PASS: fresh PID/start/cmdline/source/namespace checks, then only that owned process killed. Live parent performed reciprocal cleanup; independent8/8 verification PASS including parent_recovery=true and unchanged bridge MAC/index. Evidence namespace-guardian-loss*. Foreground controller returned0 only for confirmed fixture cleanup; no data/switch PASS is implied.
- Next: hosted client DNS/HTTPS during real VPN startup, then OpenVPN lifecycle/actual app adapter. Both current VPN clients remain disabled outside bounded trials; native/Auto is still off.

### Combined data / startup-model checkpoint 11:03 UTC

- First combined hosted-client/WG run PARTIAL: old aggregate guard aborted7.724s after1→3→4 worker counts, disabled confirmed8.030s. Hosted probes ran later with no live tunnel, so they are NOT active-path failure/success proof. WG and fixture cleanup PASS plus independent6/6 cleanup/bridge verification PASS. Source/raw results and assessment retained in wg-namespace-d34d6998.
- Added ordinary unmarked namespace DNS/HTTPS client with fresh namespace/route/MAC/source and root epoch checks. It always states external_lan_verified=false/native_certificate=false. Collector explicitly reports absent tunnel; host driver now returns PARTIAL on missing data/forward acceptance.
- Added separate bounded startup-work model: known fresh worker identities/roles, reload queues, strict budgets/progress/quiet generation, unchanged hard fault cutoffs. All36 lab unit tests PASS (13 startup reducer scenarios). Model is NOT installed or physically integrated yet; ceilings are diagnostic engineering choices, no calibrated/production claim.
- Next: wire this reviewed-in-code model into a separately frozen bounded WG/OV test without changing independent25/30s actor/cleanup leases, then obtain actual in-window data and fix observed router faults. Native app/manual/Auto and final release remain incomplete.

### Progress-observer integration checkpoint 11:12 UTC

- New frozen hardware observer refused an unmatched startup worker at2.297s; this is PARTIAL, not successful forward/data operation. Both cleanup actors PASS and independent6/6 cleanup/bridge verification PASS. Hosted probes correctly report inactive tunnel. Raw evidence retained in wg-namespace-ea909701.
- Added allowlisted classification diagnosis (PID/start/kind/known-path booleans; no raw argv/env/profile).37 lab unit checks +6 integrated observer checks PASS. Guardian/cleanup/parent/dispatch/config-guard AST identity is verified against the prior harness;25s actor/30s cleanup/15s quiet unchanged.
- Next: identify the precise legitimate/unsafe unmatched worker, then correct only a source-supported classifier contract. Do not silently whitelist arbitrary work. Installed app is still alpha19 monitor-only, source alpha21 WIP; no native/manual/Auto or data acceptance yet.

### Actual hosted HTTPS checkpoint 11:22 UTC

- Narrow classifier correction now verifies relative netifd invocation CWD, live process identity and19 current vendor source hashes; arbitrary inline work still refuses.38 lab +6 integrated observer checks PASS.
- Actual wg-namespace-726e30d8 reached LINK-SETTLED with unchanged independent timer/cleanup. Hosted ordinary-LAN client twice passed2/2HTTPS while tunnel present and root epoch unchanged. DNS to LAN gateway still timed out twice: overall PARTIAL, not full data acceptance/certification. Independent6/6 cleanup/bridge verification PASS; both fixture and WG cleanup actors PASS.
- Next concrete blocker: stock DNS dispatcher/leak filter, with HTTPS forwarding now independently distinguished. Read-only source/config-key/service-schema inspection is underway. No Windows changes. App native/manual/Auto is still unimplemented for this target, installed19 monitor-only; final release remains pending.

### DNS-owner repair checkpoint 11:45 UTC

- Confirmed stale dnsmasq upstream127.0.0.1#3053 for all instances with no listener. Kernel rule resync was unchanged and did not fix it. Stock DNS API explicitly refused DNS_BUSY because AdGuardHome was configured enabled while DNS/process were inactive.
- Verified/pinned controls; disabled only inactive adguardhome owner, removed only its nonrunning procd record and saved auto DNS with override_vpn=false via stock API, parameters only in memory. Intended flag readback PASS; network/wireless/firewall/route-policy/app config bytes unchanged. Expected changed files: adguardhome,gl-dns-v2,dhcp. Actual data retest PENDING; do not mark DNS PASS yet.
- Evidence dns-owner-repair.json; prior failed/unchanged requests retained. Next: repeat hosted WG data under the now corrected stock DNS configuration, then proceed to OV and actual app switching. No Windows changes or external-LAN certificate.

### Verified DNS recovery checkpoint 11:56 UTC

- Actual wg-namespace-b7dc19b5 PASS within router-hosted forwarding scope: LINK-SETTLED, two real DNS+2/2HTTPS measurements, same exit hash, live tunnel and stable expanded DNS/network epoch. WG and fixture cleanup PASS; independent6/6 cleanup/bridge verification PASS. This closes the observed WG DNS-owner fault; no external-LAN/native certificate or actual app switch is implied.
- Existing UI installation prompt and continuation prompt updated with actual DNS_BUSY/inactive-owner diagnosis, correct remediation and preservation of working DNS owners.33 Node UI suites PASS. New source checkpoint is alpha22 WIP, device remains alpha19 monitor-only. Full final CI/canonical package/release still pending.
- Next: current PID-safe OpenVPN cold start/data/cleanup, then warm pair and application manual/Auto transitions. Windows remains unchanged; prior failures retained.

### OV preparation checkpoint 12:01 UTC

- Fresh exact dead OV PID residue quarantined without process kill: inode4450366/numeric7646 absent process;4/4 preservation checks PASS,8 config hashes unchanged and both VPNs disabled. Source script is single-inode/single-use. Evidence ov-current-pid-quarantine.json.
- Frozen OV progress wrapper6/6 unit checks PASS; guardian/cleanup/owned-probe cutoff/dispatch functions are AST-identical to reviewed old harness,25s actor/30s cleanup unchanged. Next real cold trial proves only marked router-originated OV lifecycle/data. Ordinary LAN fallback remains blocked by WG-first Kill Switch until an actual guarded policy transition is implemented/tested.

### OV first progress / next prep checkpoint 12:14 UTC

- Actual OV LINK-SETTLED and cleanup/boot restoration PASS45.2s; independent both-links-absent/queues0 readback PASS. Early-TLS marked probe hadHTTPS2 but DNSfalse while configuration work still ran, so channel data remains PARTIAL.
- Probe timing now requires quiet LINK-SETTLED, retaining25/30s guardian/cleanup;7 wrapper regressions PASS. Fresh new residue inode4869998/PID26992 was verified dead and quarantined without process kill/config changes. Next bounded trial verifies this timing fix; no app policy transition claimed yet.

1. Add validated model preference (automatic/MT6000/MT3000) to first-run setup and settings, reporting actual hardware separately. Preserve strict platform/native guards, existing installation choices and optional functions off.
2. Complete required focused/full/generated-UI/package checks on the final source; version/bundle exact code identity. Publish reviewed release to main with exact-source CI and downloaded artifact/ref verification. Owner explicitly authorized this publication; it has not happened yet.
3. MT3000 real manual/Auto adapter remains incomplete. Actual refusal includes unsupported board, monitor-only, unconfigured source/reserve, unverified accelerators and missing bounded LAN trial. Unit/RPC refusal passes do not close these blockers.
4. OpenVPN cold-start queue abort remains unresolved. Empty queues/connected flags do not prove reload success. Do not relax growth guard or repeat identical trials solely to obtain PASS. Current read-only witness is not installed or an apply permit.
5. Finish extended isolated consumer/lab tests with correct exact-source mount, and investigate a cable-bound LAN data witness without Windows route/NIC changes. Do not issue a native certificate from router-originated traffic.
6. After each critical/long result update this file and save a local Git checkpoint. Preserve failed runs, no private histories/secrets in publication. Final physical state/readback and restore-verified current archive remain required.

### OV second progress checkpoint 12:25 UTC

- Settled-only probe correctly did not run: actual trial refused STARTUP-WORK-UNVERIFIED after7 samples/9.266s. Both cleanup actors PASS33.8s; independent links-absent/queues0 readback PASS. This is PARTIAL, not OV data or app acceptance.
- Fresh dead residue inode4900341/PID7599 quarantined without process kill/config changes;4 preservation checks PASS. Added allowlisted service-action diagnosis without raw argv; next run will distinguish the exact rejected stock firewall action. Independent25/30s leases and guard remain unchanged.

### OV measured / pair preparation checkpoint 12:33 UTC

- Third bounded cold OV trial reached LINK-SETTLED and measured DNS=true/HTTPS2 with the same independent25/30s lease/cleanup. Both cleanup actors PASS44.9s; independent current readback confirms links absent and queues0. Evidence ov-physical-progress-03.jsonl, pre-pair-readiness.json. This closes marked router-originated OV data only; no ordinary LAN/app/Auto claim.
- Prepared separate two-warm-channel engineering qualification with independent180s cleanup actor, typed/owned command GO gate, stable normalized configuration identity, two-state policy order guard, bounded nft guard and exact original boot/client restoration. Source is private/uninstalled; new physical pair run is pending. Existing unsupported native guard is unchanged.

### Pair refusal / exact recovery checkpoint 12:38 UTC

- First pair probe refused CONFIG-IDENTITY during WG start; independent actor also correctly HOLD on unexpected config. No OV or policy swap occurred. Immediate encrypted-before/after comparison in memory identified only network.WG.disabled and four firewall WG-zone metadata fields.
- Separate exact-current-network-hash recovery restored original network bytes, stopped only owned WG, verified15s quiet/both links absent and restored stock boot link: PASS. Evidence pair01-recovered.json; no Windows changes.
- Pinned stock gl_block_wan_access_exit and its already-pinned RTP/route-policy callers prove exact automatic metadata declaration/removal (wan_like1/managed1/exit_id=interface/bridge_reject0, no device/before rule). Pair observer now normalizes only that complete exact record on the two selected zones; malformed/partial/other-zone changes still refuse. No global firewall restart or metadata deletion was used. Next pair rerun is pending.

### Pair02 checkpoint 12:42 UTC

- Narrow metadata identity regressions6/6 PASS; pair reached actual WG settling and began OV. Unknown FW3 work at26.05s again caused refusal; no policy exchange or data success claimed. Independent pair cleanup PASS51.94s, original policy/both links/boot/nft state restored. Separate readback confirms links absent/queues0 and dead PID residue.
- Added allowlisted FW3 argument-shape diagnosis (unknown tokens expose length only), not a classifier exception. Next run will identify the exact stock child shape; no safety threshold relaxed.

### Pair03 / provider refusal checkpoint 12:46 UTC

- Pair03 did not settle within its25s startup observation; independent cleanup PASS63.35s, exact policy/both links/boot/nft restoration. Separate readback confirms links absent/queues0/no stale PID. No manual/Auto switch occurred.
- Safe coded logread inspection found3 AUTH_FAILED server replies and corresponding retries during this pair run; prior isolated OV succeeded. The reason (rate/session/credentials/other) is UNKNOWN; no claim of provider limit or network fault. Stop repeated authentication retries while diagnosing and running offline checks. Pair02 intermittent FW3 unknown shape remains unresolved and preserved.
- Pre-pair supported backup175 entries encrypted and DPAPI-decrypt/read verified, plaintext never persisted; SHA5b672c001df127e5e4c6097fb83ce0fbc147d702ed2fab1621b9a01fa0226f6a.

### Pair04 / recovery / CI diagnostic checkpoint 12:55 UTC

- OV-first pair startup reached both channels settled and actual root DNS/2HTTPS on both; ordinary hosted client twice passed DNS/2HTTPS through WG with stable exit/epoch. No claim that startup order caused recovery: prior AUTH_FAILED reason remains UNKNOWN.
- Engineering callback then rejected its own staged UCI reorder before commit, leaving only cfg0692bd .type=4 in libuci delta; cleanup HOLD. Exact delta and unchanged policy file SHA verified independently. Reverted only this one verified own order marker, then guarded recovery restored original policy, both links absent, boot link and nft absence: PASS. Evidence pair04-pending-index.json / pair04-recovered.jsonl.
- Pair observer now accepts only staged order markers4/5 on the exact two selected rule sections with unchanged semantic policy and a two-state effective order; actor reverts only these verified own staged markers before cleanup. Forward reorder commands now also use the shared lease/typed command deadline. No foreign option delta is allowed.
- Full alpha22 exact-commit CI failed in QA before a receipt, so NOT PASS. Added exact failing command/exit diagnostics; found and corrected a separate import side effect: protocol lab installed a global20s faulthandler timer on import. New import regression pending full run; no test timeout/memory/safety threshold was relaxed.

### Full CI / exact query / Pair05 recovery checkpoint 13:02 UTC

- Exact source905c1b73a7cd80148824e6fb7e0b576de82dfef5 full CI PASS:636 application+107 QA per runtime,33 Node UI suites on3.11;3.11 Lua skips covered by3.9 (app0 skips),3.9 QA15 environment skips covered by3.11. Identical722340-byte alpha22 IPK SHA5ced27af123dbcbd0145408074122495c9a611dff960952b6c94fb517ee2b896. Receipt .git/handoff/ci-905c1b73a7cd80148824e6fb7e0b576de82dfef5-4ec246ef62ef4278a95b88debe89548d.receipt.json. No release/publication yet.
- Actual unknown FW3 child identified as exact /bin/sh /etc/rc.common /etc/init.d/firewall enabled. Source-pinned rc.common SHAebeeedc132a75942ce876465e4636a75f745e468c573fdf9ad058e57e58a0341 proves this checks a startup symlink only. Classifier now omits only this exact read-only tuple; enable/disable/extra args still refuse.39 lab tests PASS.
- Pair05 stopped on that query before WG start; actor HOLD on down of never-registered WG. Separate corrected cleanup stops only active OV and explicitly handles proven absent runtime+kernel for WG. Recovery PASS, both links/policy/boot/nft restored. Previous failed results retained; pair policy exchange is still pending.8 private order/identity guards PASS.

### Derived process binding / Pair06 recovery checkpoint 13:27 UTC

- Pair06 reached actual guarded policy application, then correctly stopped on unmodelled stock gl_process_vpn via/mark updates. No post-switch client data success claimed. Pinned RTP handle_always_vpn_policy sets this rule from the first enabled VPN rule and set_mark_from_via commits its mark. Encrypted comparison in memory verified only two client flags, exact BWA metadata, generic order and that derived process binding.
- Separate pinned/exact-file recovery restored the full original semantic policy hash/order; both clients then disabled and links removed. Earlier recovery stages/strict assertions were incomplete and are retained. Final independent15s quiet cleanup PASS at13:22UTC: original policy semantics/order, both clients disabled/links absent, stock boot restored, own nft absent and fixture absent (pair06-cleanup-finished.jsonl). Do not claim original raw network bytes until semantic export comparison; UCI serialization can change.
- Product WIP now binds the exact two selected interface/mark pairs into policy hash and journal. Only the known gl_process_vpn via/mark pair is derived; all other fields and foreign interfaces/marks remain identity guarded. Recovery reloads this exact journal context; post-apply requires the deterministic first enabled VPN rule binding.7 targeted Python3.9 tests PASS. Full new-source CI and physical policy data/recovery remain pending.

### Alpha23 CI / Pair07 checkpoint 13:40 UTC

- Full exact-source e234461103bcab83ba1697afbe77097eabe727ae CI PASS:643 app tests per runtime plus107 QA,33 Node UI suites; reproducible alpha23 IPK SHA57e95428d14c93269bc81a01da5de88f7e30cb8293be833c3fc9a8ad83ca1838 (723757bytes). Receipt .git/handoff/ci-e234461103bcab83ba1697afbe77097eabe727ae-3e500c186ae644efbb0219bb8445c4be.receipt.json. Initial direct app-only invocation had one missing /lab bind-mount import error; exact immutable full CI includes the lab and passed.
- Pair07 used frozen new policy methods in RAM, installed app remains19 monitor-only. Own config/hash guards survived policy application; post-policy observer refused stock DNSMASQ restart, not a data/Auto PASS. Independent automatic cleanup PASS95.18s; separate links absent/queues0 readback PASS.
- Source-pinned RTP line836 directly starts dnsmasq restart in background even with not_reload_network. Added explicit post-policy-only DNS restart contract, exact argv and DNS-init source pin; cold defaults/network/firewall restarts remain refused and all original timing/memory/process budgets unchanged.40 lab tests PASS. Next physical rerun must match actual hosted target exit to a fresh marked OV measurement and prove WG return, not merely distinct IP.

### Physical policy round trip PASS / new native integration WIP, 14:07 UTC

- Pair08 PASS: frozen alpha23 policy methods executed actual WG→OV→WG exchange. Six ordinary unmarked hosted-client measurements passed DNS+2HTTPS (two each phase); reserve exit exactly matched fresh marked OV root measurement and was distinct from source, return matched original WG. Original policy, both clients disabled/links absent, boot and own nft removal PASS111.9s. Separate fixture/bridge6 checks PASS. This is router-hosted forwarding, not external LAN certification or an installed native daemon test.
- New strict MT3000 live platform profile readback PASS with no blockers: glinet,mt3000-snand / GL.iNet GL-MT3000 / mediatek/mt7981 /5.4.211/aarch64 /4.11.0, exact stock hashes/FW3/include and quiet workers. It grants no rights by itself. Actual controller still installed alpha19 monitor-only.
- Source now adds MT3000 native service eligibility plus live source/FW3/worker guards (selected WG1/OV1 only), post-RTP quiet waiting, separate external-lan vs router-hosted-ipv4 confirmation/certificate/history/status, explicit test-only UI label, and nonce/revision-bound native_trial_start. A fresh private calibration can supersede an old Stop without erasing it or claiming a certificate; normal Auto Start still requires one. Public helper stays native_enabled0 and requests only RAM intent after TEST.
- Focused platform/proof/control/deployment tests and Windows helper SelfTest PASS; full new-source CI, package/install/served UI, real native calibration/manual/Auto/fault tests and main release remain pending. Existing AI prompt updated with exact prerequisites, derived process rule, asynchronous DNS and scoped proof limits.

### Native integration CI correction 14:16 UTC

- Alpha24 exact CI failed at Node auto blocker explanation coverage for newly exposed EXISTING-TUNNEL-BINDING-UNVERIFIED; no PASS receipt issued. Added plain EN/RU explanations for every additional MT3000 platform refusal. Fault-injection eligibility now also requires matching native/certificate proof scope, preventing hosted proof reuse in external mode. New final CI follows this checkpoint. Router remains19 monitor-only, both VPNs/fixture/guards restored after Pair08.

### UI coverage correction / canonical build preparation 14:26 UTC

- Alpha25 exact CI stopped at readable-name coverage after blocker explanations passed. Added bilingual short names for the same verified platform codes; all33 Node UI suites then PASS together. No alpha25 PASS receipt is claimed. Explicit fresh private calibration also now distinguishes an exhausted older bounded window from the current one; nonce replay and current-window quota still refuse. Next exact CI/canonical artifact covers the complete source.

### Installed native controller acceptance PASS, 14:49 UTC

- Alpha26 full exact CI PASS:655 app+107 QA per runtime,33 Node UI suites, complementary environment skips covered. Canonical Linux IPK727939bytes/SHA8ad6eda5287135b3b3b60e292d80b120da3cd03c984319a0a1d51c70e59bd624 matched both matrices.
- Actual install PASS opkg0,77 payload files/modes exact,7 protected config files byte-unchanged. Fresh175-entry supported backup encrypted and DPAPI-decrypt/read verified. Actual HTTPS dashboard69.js/ui46.css through pinned cable/certificate match canonical package exactly.
- Actual installed native_pilot01 PASS (458.1s): real native calibration with fresh scoped confirmation, actual bounded WG packet-drop fault, Auto reserve COMMITTED plus ordinary hosted DNS/2HTTPS, automatic primary recovery plus data, Stop, manual reserve held/confirmed plus data, manual primary return plus original WG exit. Wrong revision and manual-while-Auto refused. Shared quota used3 attempts; no external-LAN certificate claimed.
- Independent outer cleanup reports original policy restored, both links absent, stock boot restored, own nft removed, Auto stopped, default external scope restored and monitor restarted. Hosted certificate cannot satisfy default external mode. Separate final kernel/service readback and boot test follow.
- Observed minor status issue: after transient VENDOR-WORKER-BUSY clears, COMMITTED reused the prior warning list. Fixed only that stale list when current diagnostics are clear. Kit now accepts both actual boards and does not log private trial/preparation nonces or duplicate a token-bearing conffile in plaintext. Existing launch prompt records PID ownership repair. Final source CI/artifact/version/install and main publication pending after this checkpoint.

### Final installed/crash/boot checkpoint 15:33 UTC

- Alpha27 exact cde035f5727a482e670682696a083cdd71c904e0 CI PASS; installed77 payload files/modes and HTTPS assets match canonical SHA5357b80...acad6. New supported backup encrypted and DPAPI-decrypt/read verified.
- native-crash-27 PASS: own source/PID identity verified before SIGKILL in WAIT-CLIENT; procd respawned1770→9153, journal rolled back with SUPERVISOR-RECOVERY, ordinary hosted DNS/2HTTPS restored, monotonic lease unchanged, quota1 preserved, certificate bytes unchanged, duplicate nonce refused. Cleanup PASS.
- Actual monitor off/on5 checks PASS, protected config hashes unchanged and Auto not started.
- First reboot is PARTIAL for original all-off/acceleration state: app Auto stayed off, but stock profiles came up and SFE core loaded. SFE source identified exactly as /etc/modules.d/09-shortcut-fe SHA8aad0842bbf4de46c61719fba3237d3127cee632f4312807ff3b591d388b2f49. The init shortcut-fe source itself exits with HNAT0. Do not attribute the module load to that init action.
- Persistent dedicated-router fix: mask exact autoload file at /etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe; disable vpn-client/shortcut-fe boot entries, only WG1/OV1 disabled1/auto0, normal non-force accelerator preparation. Combined fix verified by second actual reboot:19 final checks PASS. HNAT remains0/runtime disabled, SFE absent; no owner PC/primary router changes. Current readback post-reboot27-persistent-state.json.
