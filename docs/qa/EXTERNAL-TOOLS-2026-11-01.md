# External test and analysis tools — 2026-11-01 (2.0.0-beta1 source)

## Кратко (RU)

1. Подобраны открытые инструменты с GitHub под наш стек (Lua 5.1, C-модуль, Python 3.9, busybox sh, JS LuCI, nftables).
2. На ПК (в Docker, без роутера) запущены: luacheck, shellcheck, bandit, ruff, pyflakes, cppcheck, clang analyzer, eslint, semgrep, gitleaks, hypothesis и libFuzzer+ASan/UBSan для `canon_c.c`.
3. Падений и утечек памяти в `canon_c.c` фаззинг не нашёл; C и `canon.lua` совпали на всех входах (итог — раздел «Fuzzing»).
4. Реальная находка 1: `native_history.History._read()` пропускает `RecursionError` на повреждённом файле с глубокой вложенностью (≥1000) — нет перехода на резервную копию.
5. Находка 2: `decode_keys` (Lua и C одинаково) не проверяет пропускаемые поля: `{"x":[garbage},"a":1}` принимается, `decode()` — отвергает.
6. Находка 3: тест `test_canon_keys.lua:24` содержит `'"é"'` — в Lua 5.1 это `"u00e9"`, экранирование \u в тесте фактически не проверяется.
7. Находка 4: рабочее дерево на Windows (autocrlf) получает CRLF в init.d/sbin/*.lua: `.gitattributes` не закрепляет LF для файлов без расширения и `.lua`.
8. Мелкое: теоретический UB `memcpy(NULL,…,0)` в `canon_c.c:62`; защита от `__proto__` в `ui_logic.inc.js:29`; 20 неиспользуемых импортов Python.
9. Секретов не найдено: 5 срабатываний gitleaks — все ложные (sha256-суммы, текст, имена переменных).
10. Код продукта и тесты не менялись; добавлены только `qa/external/*` и этот отчёт. Роутер не трогали.

## Tools

"Ran" means run on this PC against this worktree (Docker image `homensai-vpn-qa-external:20261101`, built from
`qa/external/Dockerfile`, Ubuntu 24.04). Router-only tools were not run.

| Area | Tool | GitHub | Version | Applies | Ran | Result |
|---|---|---|---|---|---|---|
| Lua lint | luacheck | github.com/lunarmodules/luacheck | 1.2.0 | yes | yes | product Lua: 0 undefined globals, 0 syntax errors; 1174 warnings (1111 line length, 34 unused args/vars, 6 shadowing). Tests: E011, see F3 |
| Lua lint | selene | github.com/Kampfkarren/selene | — | partly (Lua 5.1 std, Roblox-oriented) | no | luacheck covers the same checks |
| Shell | shellcheck | github.com/koalaman/shellcheck | 0.11.0 | yes | yes | 0 errors on LF copies; 3 SC2034 (procd vars), 3 SC3043 (`local`, fine in busybox ash), 15 notes |
| Python security | bandit | github.com/PyCQA/bandit | 1.8.6 | yes | yes | 0 HIGH; 12 MEDIUM (9×/tmp paths on OpenWrt tmpfs, 1×urlopen fixed https, 2×B610 false positive); 94 LOW (subprocess argv lists) |
| Python lint | ruff | github.com/astral-sh/ruff | 0.14.3 | yes | yes | correctness set (E9,F): 0 syntax errors, 0 undefined names, 20 unused imports, 1 unused local |
| Python lint | pyflakes | github.com/PyCQA/pyflakes | 3.4.0 | yes | yes | same as ruff + 1 `global STOP` false positive |
| C lint | cppcheck | github.com/danmar/cppcheck | 2.13.0 | yes | yes | 0 findings |
| C lint | clang static analyzer | github.com/llvm/llvm-project | 18.1.3 | yes | yes | 1: F5 |
| C lint | clang-tidy | github.com/llvm/llvm-project | — | yes | no | analyzer run covers clang-analyzer-* checks |
| C sanitizers + fuzz | libFuzzer + ASan + UBSan | github.com/llvm/llvm-project | 18.1.3 | yes | yes | see "Fuzzing" |
| C fuzz | AFL++ | github.com/AFLplusplus/AFLplusplus | — | yes | no | libFuzzer harness chosen; same harness builds with afl-clang-fast |
| JS lint | eslint (+@eslint/js recommended) | github.com/eslint/eslint | 9.39.0 | yes | yes | 0 undefined names in built `dashboard.js` (1 unused `self`); 41 hits in fragments: 29 empty blocks, 4 control-char regex (intended), 5 constant conditions (2 dead `false&&`/`null&&` UI blocks), 2 redeclared `var`, 1 intended func reassign |
| Multi-language | semgrep (p/default, 449 rules) | github.com/semgrep/semgrep | 1.142.0 | yes (no Lua support) | yes | 3: prototype-pollution `ui_logic.inc.js:29` (F6); 2 false positives (`status_client.py:81` argv list, `telegram_report.py:112` fixed https URL) |
| Secrets | gitleaks | github.com/gitleaks/gitleaks | 8.28.0 | yes | yes | 5 generic-api-key hits, all false positives (2 sha256 file pins, prose, 2 identifiers); run with `--redact` |
| Secrets | trufflehog | github.com/trufflesecurity/trufflehog | — | yes | no | gitleaks covers the worktree; trufflehog adds history + live verification (needs network calls to providers — not wanted) |
| Python property tests | hypothesis | github.com/HypothesisWorks/hypothesis | 6.113.0 (py3.9) | yes | yes | 4 properties, 1 failing: F1 |
| Python fuzz | atheris | github.com/google/atheris | — | yes | no | hypothesis found the same class; atheris adds coverage guidance (follow-up) |
| Mutation | mutmut | github.com/boxed/mutmut | 3.3.1 (installed) | yes | no | needs per-module runs of the 1–2 h suite; too heavy for a shared PC today |
| Mutation (Lua) | — | none maintained | — | no | no | — |
| nft syntax | `nft -c -f` (nftables) | git.netfilter.org/nftables | — | yes | no | already used by the product before every ruleset load (`backend.lua:787`, `fault_control.py:80`); offline check would need the generator extracted |
| nft lint | nff | git.frzn.dev/NotAShelf/nff | — | maybe | no | young project; style rules only |
| Network chaos | tc netem / pumba / toxiproxy | github.com/alexei-led/pumba, github.com/Shopify/toxiproxy | — | lab only | no | useful for the OpenWrt-VM lab (packet loss/latency on WAN), not for unit code |
| VPN leak | go-dnsleaktest, ovpns (DNS/IPv6) | github.com/rany2/go-dnsleaktest, github.com/M3ro20j1/ovpns | — | router-only (LAN client behind router) | no | headless; run from a LAN client during a router acceptance window |
| WebRTC leak | browser test pages | — | — | no (router does not proxy browsers; IPv4 policy routing) | no | — |
| WireGuard/OpenVPN | wireguard-tools netns tests, openvpn t_client | git.zx2c4.com/wireguard-tools, github.com/OpenVPN/openvpn | — | router-only (GL firmware owns the tunnels) | no | — |
| OpenWrt | SDK `make package/…/check` + `opkg` metadata, `ucode`/uci tests | github.com/openwrt/openwrt, github.com/openwrt/actions-shared-workflows | — | yes (SDK image exists: `homensai-vpn-sdk:20261020`) | no | already part of the release build; not rerun (CI is busy) |
| Dependencies/CVE | osv-scanner, pip-audit | github.com/google/osv-scanner, github.com/pypa/pip-audit | — | low | no | no third-party Python/npm runtime deps in the package; firmware packages are GL.iNet's |

## Findings (real or likely)

F1 — `router/files/usr/lib/homensai-vpn/native_history.py:338` (`History._read`). `json.loads` of a corrupt
`native-history.json` nested ≥ ~1000 deep raises `RecursionError` (a `RuntimeError`), which the `except
(OSError,ValueError,KeyError,TypeError,AttributeError)` does not catch: the backup file is not tried and callers
(`load`, `load_state`, `statistics_export`, `stats_reset`) get an unexpected exception instead of `HistoryError`.
`encoded(data)` would hit the same for deep valid JSON. Reproduced on Python 3.9 (`homensai-vpn-python39:local`) by
`qa/external/hypothesis/test_props.py::test_history_read_fails_only_with_history_error`. Severity low (file is
root-owned and self-written), but it defeats the main→backup fallback. `agent.read_json` and `rpc_input` already
catch `RecursionError`. Fix idea: add `RecursionError` to that `except`.

F2 — `canon.lua:415-427` and `canon_c.c:785-805` (`skip_value`, used by `decode_keys`). Skipped fields are scanned
only for brackets and quotes, so `{"x":[garbage},"a":1}` and `{"x":"\q","a":3}` are accepted by `decode_keys` while
`decode` (and Python `json.loads`) reject them; `[`…`}` mismatches are counted as balanced. C and Lua agree, so it is a
documented-speed trade-off, not a divergence. Risk: a torn/corrupt `status.json` can be partly accepted. Severity low.

F3 — `router/tests/lua/test_canon_keys.lua:24`: the piece `'"é"'` is `"u00e9"` in Lua 5.1 (unknown escape drops
the backslash; luacheck E011). The random-document test therefore never feeds a `\u` escape. Intended: `'"\\u00e9"'`.

F4 — Line endings. `.gitattributes` pins `eol=lf` for `*.py`, `*.sh`, `router/native/**`, but not for `*.lua`,
`*.js`, `router/files/etc/init.d/*`, `router/files/usr/sbin/*`, `router/files/etc/config/*` (`text=auto`). With
`core.autocrlf=true` this Windows worktree has 386 CRLF files under `router/files`, including the procd init script.
Git blobs are LF and the SDK export uses `git archive`, so shipped packages are fine today; but any build or copy from
a Windows checkout would put `#!/bin/sh /etc/rc.common\r` on the router. Fix idea: `router/files/** text eol=lf`
(keeping the existing `-text` style rule).

F5 — `router/native/canon_c.c:62` (`buf_add`): clang analyzer path where `b->p == NULL` and `n == 0` reaches
`memcpy(NULL+0, s, 0)` — undefined behaviour by the C standard although harmless with glibc/musl. Fix idea:
`if (!n) return;` first.

F6 — `router/ui_logic.inc.js:29` (`uiMergeHistory`): walks dotted paths from the router's `history_split` into
`status`; a path through `__proto__` would write to `Object.prototype`. Data comes from the router's own RPC, so not
exploitable from outside today; cheap hardening is to skip `__proto__`/`constructor`/`prototype` keys.

### Fix status (2026-11-02)

- F1, F3, F4, F6 — fixed in `e61dc351` (01.11.2026).
- F2 — fixed. `skip_value` in `canon.lua` and `canon_c.c` now validates exactly as `parse_value` does, without building
  the value: string escapes, `\uXXXX`, control characters, number grammar, `nonfinite number`, `integer beyond 2^53`,
  literals, `,`/`:` separators, duplicate fields in nested objects and the nesting limit (skipped fields start at depth
  1, like kept ones). `decode_keys` therefore accepts exactly what `decode` (and Python `json.loads` with the canon hooks)
  accepts and, for an object document, raises the same error at the same byte. Tests: `router/tests/lua/test_canon_keys.lua`
  (26 malformed values × 3 positions, same error as `decode`, both with and without the C module) and
  `router/tests/lua/canon_c_differential.lua` (fixed cases plus, for every fuzzed object text, `decode_keys` vs `decode`
  acceptance and error text, besides Lua vs C).
- F5 — fixed: `buf_add` returns at once when `n == 0`, before `buf_need`/`memcpy`.
- `router/files/usr/lib/lua/canon_c.so` rebuilt with `router/native/build.sh router` (OpenWrt 21.02.7 SDK toolchain,
  same flags); the HEAD source rebuilt in the same container reproduced the previous record `503c2b9a…` byte for byte,
  the new record is in `router/native/canon_c.so.sha256`. `router/native/test.sh` (stock Lua, LNUM x86_64, aarch64 package
  file under qemu, router/tests with the module) was run on the PC.
- Found on the way: the F4 line `router/files/** text eol=lf` came after `*.so binary` and the style `-text` rule and
  overrode them (`canon_c.so` and the `.woff2` fonts were marked text with LF conversion, so a CR LF pair inside a new
  binary would have been changed on `git add`). `.gitattributes` repeats the binary and style rules after it.

Style-only (counts): luacheck 1111 long lines, 20 unused args, 13 unused vars, 10 empty `if` branches, 6 shadowed
upvalues; ruff 609 local imports, 388 magic numbers, 203 complexity, 47 `%` formatting; bandit 94 LOW; eslint 29
empty blocks, 2 disabled-by-`false&&`/`null&&` UI blocks (`auto_panel.inc.js:515`, `manual_panel.inc.js:226`), duplicate
`var monitorKind` (`live_log.inc.js:21,24`) and `interval` (`setup_wizard.inc.js:71,101`); unused
`profiles` (`agent.py:932`).

## Fuzzing (canon_c.c vs canon.lua)

Harness: `qa/external/fuzz/` — `canon_c.c` and stock Lua 5.1.5 built with clang 18 `-fsanitize=address` (+`undefined`
on `canon_c.c`, no recover) and libFuzzer. Every input goes to `canon.lua`'s own `lua_decode`/`lua_decode_keys` and to
the C `decode`/`decode_keys`; the run aborts on any difference in accept/reject, error text, decoded value (markers,
-0.0), or on any difference between `lua_encode` and C `encode` of the result. Seeds: the module's own probe document,
a history-like document, nesting, escapes, numbers; JSON dictionary `json.dict`. Not covered: the router's LNUM Lua
(integer subtype) — `router/tests/lua/canon_c_differential.lua` already covers it on the PC.

Result (2026-11-01 16:16-16:25, `-fork=2`, 498 s, `--cpus 2`): 2,043,755 executions, 0 crashes, 0 timeouts,
0 OOM, 0 sanitizer reports, 0 Lua/C mismatches; coverage 3698 edges / 7535 features, corpus grew from 5 to 879 inputs
(all of `l_decode`, `l_decode_keys`, `l_encode`, `parse_*`, `skip_value`, `repr_float`, `round_trip` reached). The
corpus is not committed (rebuilt in a few minutes).

## Rerun

```sh
cd <worktree>; export MSYS_NO_PATHCONV=1        # Git Bash on Windows
docker build -t homensai-vpn-qa-external:20261101 qa/external
docker run --rm -v "$PWD:/src:ro" -v "$PWD/../qa-out:/out" homensai-vpn-qa-external:20261101 sh /src/qa/external/run-static.sh
docker run --rm -v "$PWD:/src:ro" -v "$PWD/../qa-out:/out" semgrep/semgrep:1.142.0 sh -c 'mkdir -p /tmp/s && cp /src/router/files/usr/lib/homensai-vpn/*.py /src/router/*.inc.js /src/router/native/canon_c.c /tmp/s/ && cd /tmp/s && semgrep scan --config p/default --metrics=off --no-git-ignore --json -o /out/semgrep.json .'
docker run --rm -v "$PWD:/src:ro" -v "$PWD/../fuzz-out:/out" homensai-vpn-qa-external:20261101 sh /src/qa/external/fuzz/run.sh 300 2
docker run --rm -v "$PWD:/src:ro" homensai-vpn-python39:local sh -c 'pip install -q --target /tmp/hy hypothesis==6.113.0 && PYTHONPATH=/tmp/hy python3 /src/qa/external/hypothesis/test_props.py'
```

Notes: gitleaks runs with `--redact`; no tool contacts the router; F1 makes `test_props.py` exit 1 until fixed.
