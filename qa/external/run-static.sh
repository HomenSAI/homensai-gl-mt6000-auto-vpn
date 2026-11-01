#!/bin/sh
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
# Static analysers over the product sources (read-only mount), results in /out/*.txt|json:
#   docker run --rm -v <worktree>:/src:ro -v <out>:/out homensai-vpn-qa-external:20261101 sh /src/qa/external/run-static.sh
# (Git Bash on Windows: export MSYS_NO_PATHCONV=1 first.) gitleaks runs with --redact: values never reach the report.
# semgrep runs from its own image (see the end of this file).
set -u
cd /src
R=router/files/usr/lib/homensai-vpn
out=/out; mkdir -p "$out"
luacheck --std lua51 --codes --no-color --formatter plain $R/lua router/tests/lua > "$out/luacheck.txt" 2>&1
# A Windows checkout (core.autocrlf=true) has CRLF in the extensionless scripts: lint LF copies (git blobs are LF).
sc=/tmp/sc; mkdir -p $sc
for f in router/files/etc/init.d/homensai-vpn router-test-kit/*.sh router/files/usr/sbin/*; do
  mkdir -p "$sc/$(dirname "$f")"; tr -d '\r' < "$f" > "$sc/$f"
done
(cd $sc && shellcheck -f gcc -s sh router/files/etc/init.d/homensai-vpn router-test-kit/*.sh router/files/usr/sbin/*) \
  > "$out/shellcheck.txt" 2>&1
bandit -q -r $R -f txt > "$out/bandit.txt" 2>&1
bandit -q -r $R -f json -o "$out/bandit.json" >/dev/null 2>&1
ruff check --no-cache --target-version py39 --output-format concise --select E9,F,B,S,PL,UP $R > "$out/ruff.txt" 2>&1
ruff check --no-cache --target-version py39 --output-format concise --select E9,F $R > "$out/ruff-correctness.txt" 2>&1
pyflakes $R > "$out/pyflakes.txt" 2>&1
cppcheck --enable=warning,portability,performance --inconclusive --std=c99 --inline-suppr --quiet \
  -I router/native/lua-5.1.5 -ULUA_USER_H --suppress=missingIncludeSystem router/native/canon_c.c \
  > "$out/cppcheck.txt" 2>&1
clang --analyze -Xanalyzer -analyzer-output=text -I router/native/lua-5.1.5 router/native/canon_c.c -o /dev/null \
  > "$out/clang-analyzer.txt" 2>&1
# eslint resolves the config's imports next to the config: lint a copy beside /opt/eslint/node_modules
js=/tmp/js; mkdir -p $js/router
cp router/*.inc.js router/files/www/luci-static/resources/view/homensai-vpn/dashboard.js $js/router/
cp qa/external/eslint.config.mjs $js/ && ln -s /opt/eslint/node_modules $js/node_modules
(cd $js && eslint router > "$out/eslint.txt" 2>&1)
gitleaks dir /src --redact --no-banner --report-format json --report-path "$out/gitleaks.json" > "$out/gitleaks.log" 2>&1
echo done
# semgrep (official image):
#   docker run --rm -v <worktree>:/src:ro -v <out>:/out semgrep/semgrep:1.142.0 semgrep scan --config p/default \
#     --metrics=off --json -o /out/semgrep.json /src/router/files /src/router/native /src/router-test-kit
