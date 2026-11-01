#!/bin/sh
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
# PC differential check of canon_c against canon.lua (Git Bash or Linux with Docker; nothing touches a router):
#   sh router/native/test.sh <work-dir> [cases]
# <work-dir> (outside the repository) must hold, built by the commands at the end of this comment:
#   lua-x86/{lua,liblua.so.5.1.5}   OpenWrt 21.02 Lua (LNUM) for x86_64
#   lua-a64/{lua,liblua.so.5.1.5,ld-musl-aarch64.so.1}   the same Lua for aarch64 musl (SDK toolchain) + its loader
# Stages: stock Lua 5.1.5 (Debian lua5.1 of homensai-vpn-python311:local) with the host-stock module; the x86_64
# OpenWrt Lua with the host-lnum module; the aarch64 OpenWrt Lua with the package file router/files/usr/lib/lua/
# canon_c.so under qemu (docker --platform linux/arm64); then the module refused across number models, the Lua-only
# switch, and the router/tests/lua suites + test_lua_*.py with the module in use (stock Lua).
# OpenWrt Lua: lua-5.1.5.tar.gz + package/utils/lua/patches of v21.02.7 (hashes in build.sh), in src/:
#   make CC=<cc> CFLAGS="<-O2|-Os -mcpu=cortex-a53> -DLUA_USE_LINUX -fPIC -std=gnu99" PKG_VERSION=5.1.5 V=5.1 liblua.so lua.o
#   <cc> -o lua5.1 lua.o -L. -l:liblua.so.5.1.5 -Wl,-E [-lm -ldl]
set -eu
work=$1
cases=${2:-20000}
winpath() { (cd "$1" && { pwd -W 2>/dev/null || pwd; }); }
repo=$(winpath "$(dirname "$0")/../..")
w=$(winpath "$work")
run() { MSYS_NO_PATHCONV=1 docker run --rm -v "$repo:/s" -v "$w:/cm" "$@"; }
run -w /s/router/native --entrypoint sh homensai-vpn-sdk:20261020 -c 'sh build.sh host-stock /cm/stock && sh build.sh host-lnum /cm/lnum'
echo '== stock Lua 5.1.5 (Debian), host-stock module'
run -w /s/router/tests/lua --entrypoint sh homensai-vpn-python311:local -c "export LUA_CPATH='/cm/stock/?.so'
  lua5.1 canon_c_differential.lua fuzz $cases 1 && lua5.1 canon_c_differential.lua floats 200000 && lua5.1 canon_c_differential.lua bench 5
  HOMENSAI_CANON_C=0 lua5.1 canon_c_differential.lua off
  LUA_CPATH='/cm/lnum/?.so' lua5.1 -e \"package.path='../../files/usr/lib/homensai-vpn/lua/?.lua;'..package.path
    assert(require('canon').c_module==nil) print('lnum module refused by stock Lua: ok')\""
echo '== OpenWrt Lua (LNUM) x86_64, host-lnum module'
run -w /s/router/tests/lua -e LD_LIBRARY_PATH=/cm/lua-x86 --entrypoint sh homensai-vpn-sdk:20261020 -c "export LUA_CPATH='/cm/lnum/?.so'
  /cm/lua-x86/lua canon_c_differential.lua fuzz $cases 2 && /cm/lua-x86/lua canon_c_differential.lua floats 200000 && /cm/lua-x86/lua canon_c_differential.lua bench 5
  LUA_CPATH='/cm/stock/?.so' /cm/lua-x86/lua -e \"package.path='../../files/usr/lib/homensai-vpn/lua/?.lua;'..package.path
    assert(require('canon').c_module==nil) print('stock module refused by LNUM Lua: ok')\""
echo '== OpenWrt Lua (LNUM) aarch64 musl under qemu, package file'
run -w /s/router/tests/lua --platform linux/arm64 alpine:3.20 sh -c "L=/cm/lua-a64; export LUA_CPATH='/s/router/files/usr/lib/lua/?.so'
  \$L/ld-musl-aarch64.so.1 --library-path \$L \$L/lua canon_c_differential.lua fuzz $((cases / 4)) 3 &&
  \$L/ld-musl-aarch64.so.1 --library-path \$L \$L/lua canon_c_differential.lua floats 50000 &&
  \$L/ld-musl-aarch64.so.1 --library-path \$L \$L/lua canon_c_differential.lua bench 2"
echo '== router/tests with the module in use (stock Lua)'
run -w /s -e PYTHONDONTWRITEBYTECODE=1 --entrypoint sh homensai-vpn-python311:local -c "export LUA_CPATH='/cm/stock/?.so'
  cd router/tests/lua && for t in test_*.lua; do lua5.1 \$t >/tmp/out 2>&1 || { echo FAIL \$t; tail -5 /tmp/out; }; done; echo lua suites done
  cd /s && python3 -m unittest discover -s router/tests -p 'test_lua_*.py' 2>&1 | tail -4"
