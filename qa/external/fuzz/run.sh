#!/bin/sh
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
# Build canon_c.c + stock Lua 5.1.5 with clang ASan/UBSan/libFuzzer and fuzz decode/decode_keys against canon.lua.
#   docker run --rm -v <worktree>:/src:ro -v <out>:/out homensai-vpn-qa-external:20261101 sh /src/qa/external/fuzz/run.sh [seconds] [workers]
# Replay one input: /out/build/canon_fuzz <file> (with the two CANON_* variables below exported).
set -eu
secs=${1:-480}; workers=${2:-4}
src=/src; out=/out; b=$out/build; mkdir -p "$b" "$out/corpus" "$out/artifacts"
LUA=/opt/lua-5.1.5/src
SAN="-g -O1 -fno-omit-frame-pointer -fsanitize=address,fuzzer-no-link"
for f in "$LUA"/*.c; do
  case $(basename "$f") in lua.c|luac.c|print.c) continue;; esac
  clang $SAN -DLUA_USE_POSIX -c "$f" -o "$b/$(basename "$f" .c).o"
done
clang $SAN -fsanitize=undefined -fno-sanitize-recover=undefined -std=gnu99 -Wall -Wextra -I"$LUA" -c \
  "$src/router/native/canon_c.c" -o "$b/canon_c.o"
clang -g -fsanitize=address,undefined,fuzzer -I"$LUA" "$src/qa/external/fuzz/canon_fuzz.c" "$b"/*.o -lm -o "$b/canon_fuzz"
cp "$src"/qa/external/fuzz/seeds/* "$out/corpus/"
export CANON_FUZZ_LUA="$src/qa/external/fuzz/canon_fuzz.lua" CANON_LUA_DIR="$src/router/files/usr/lib/homensai-vpn/lua"
export ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1
cd "$out"
"$b/canon_fuzz" -dict="$src/qa/external/fuzz/json.dict" -max_len=4096 -timeout=10 -rss_limit_mb=2048 \
  -max_total_time="$secs" -fork="$workers" -ignore_crashes=1 -artifact_prefix="$out/artifacts/" "$out/corpus" \
  > "$out/fuzz.log" 2>&1 || true
tail -25 "$out/fuzz.log"
echo "artifacts: $(ls "$out/artifacts" | wc -l)"; echo "corpus: $(ls "$out/corpus" | wc -l)"
