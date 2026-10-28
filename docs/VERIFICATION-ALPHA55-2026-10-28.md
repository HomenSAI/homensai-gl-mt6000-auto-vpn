<!-- doc-role: versioned-evidence -->
# Alpha55 installed, manual acceptance failed / Alpha55: ручная приёмка не пройдена

Dedicated GL-MT3000, GL.iNet 4.11.0, 28 October 2026. Code `b80376d0fc1b6eb7b0c8c43f63868eb67ba88fcb`, record `e930d1add16dd7786b784f9962cb6f0492100fe4`. Package **0.9.1-alpha55-1**, 971879 bytes, SHA256 `fe466cacfd043ff92a4305920ce76eda383f6cee8a0bb62e9bae3731a4eb0d18`.

Both immutable runtimes passed 1100 application tests without skips, 150 QA with 2/37 explicit skips, 60 offline lab cases and 13 Lua tests. Full 3.11 also passed 20 tools tests, **81 UI suites** and two Node lab suites. The earlier local count of 80 understated the actual UI glob; CI records 81. The isolated Python 3.9 build matched and strict five-file record verification passed without a second record-only CI.

Installation and HTTP/RPC verification passed for **99 files**, dashboard130/ui96/help130. Main module 872094 LF bytes, 30.16% below alpha51. Protected settings, terms, interfaces and main routes were preserved. Encrypted before/after backups passed independent decrypt/archive checks; plaintext was not persisted.

Normal Start passed in **29 seconds**: ON, RUNNING, OBSERVING, fresh kernel-confirmed reserve path and both VPNs healthy. The epoch correction worked. Auto subsequently completed a return to the primary: repeated fresh observations showed primary marking, OBSERVING and a COMMITTED journal.

Actual 3/3 website checks passed on both VPNs. One snapshot measured primary **323.7 ms**, reserve **2220.8 ms**, independently recomputed from the three site values. A separate sequential read-only diagnostic measured reserve requests at 1677.9/1791.6/1681.8 ms, mean **1717.1 ms**. The Google request included DNS 373.1, TCP 316.4, TLS 483.1 and HTTP-header waiting 504.2 ms. This is fresh web-response time, not an ICMP round trip or a fabricated timeout zero; it does not measure browser rendering or prove a separate LAN client's path.

**Manual acceptance failed; alpha55 was not issued as a GitHub release.** The first same-channel action was refused before dispatch with TRANSACTION-IN-PROGRESS. An inspection during the automatic transition could not confirm the path. Later stable RUNNING/OBSERVING, primary kernel marking and COMMITTED journal observations still showed both manual choices blocked.

Exact comparison proved that pair_manual.controls constructed Linux backends without current process_bindings. Unbound live order/hash differed and state_order_matches was false. Binding the same backend with the current state made it true: the bound hash equalled state and journal, current journal order matched, and session-order/role metadata matched. This was missing observation context, not an external policy change. No guard was bypassed or manual route mutation made. The next correction must bind context at status/request/dispatch/recovery boundaries, retaining foreign-hash, generation, Stop, quota and cooldown checks. Actual manual switching, final native browser/performance acceptance and publication remain required. Code, package, backups and failed evidence remain preserved.

Intermediate source failures were also retained: premature footer anchor, a 22-byte miss of the strict size target, old fixtures and saved-event normalization, rounded bucket statistics, Windows-worktree Git access in Linux and a private CRLF size-check mistake. Their corrected checks passed; the hardware manual failure remains separate.

---

Alpha55 установлена: 99 файлов, HTTP/RPC, настройки и условия сохранены; копии до и после проверены. Auto запустился за 29 секунд и затем действительно вернулся на основной канал. Полные ответы трёх сайтов через оба VPN прошли, среднее пересчитано независимо. Большой отклик OpenVPN подтверждён отдельным разбором DNS/TCP/TLS/HTTP.

Ручная приёмка не прошла: API сохранял TRANSACTION-IN-PROGRESS после завершённого возврата. Без контекста пары правила выглядели иначе; с контекстом те же правила точно совпали с состоянием и журналом. Настройки вслепую не восстанавливались, проверки не отключались, ручная смена пути не выполнялась. Alpha55 не выпущена как GitHub-релиз. Следующему кандидату нужны настоящие ручные переключения, окончательный браузер и публикация.

External LAN-client, full-day, controlled physical-fault, power-cut, IPv6 and MT6000 continuous-mode acceptance remain separate.
