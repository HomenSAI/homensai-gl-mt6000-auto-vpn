#!/bin/sh
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
# canon_c.so (router/native/canon_c.c), run in router/native inside the build image homensai-vpn-sdk:20261020:
#   sh build.sh router <toolchain-dir> <out-dir>   the package file: aarch64_cortex-a53, musl, the Lua of OpenWrt 21.02
#   sh build.sh host-stock <out-dir>               x86_64 for PC tests with stock Lua 5.1.5 (Debian lua5.1)
#   sh build.sh host-lnum <out-dir>                x86_64 for PC tests with the OpenWrt Lua (LNUM) built for the PC
# <toolchain-dir>: staging_dir/toolchain-aarch64_cortex-a53_gcc-8.4.0_musl of
#   openwrt-sdk-21.02.7-mediatek-mt7622_gcc-8.4.0_musl.Linux-x86_64.tar.xz (downloads.openwrt.org, sha256
#   723b08a90778779cbc20da03a36fa0e213b22dd63ce601803f0eae44f303681d); staging_dir/host/lib next to it.
# Headers: lua-5.1.5-openwrt-21.02/ = lua-5.1.5.tar.gz (sha256 2640fc56a795f29d28ef15e13c34a47e223960b0240e8cb0a82d9b0738695333)
#   with package/utils/lua/patches of OpenWrt v21.02.7 (LNUM: LNUM_DOUBLE + LNUM_INT32, lua_Integer = int);
#   lua-5.1.5/ = the same tarball unpatched (lua_Integer = ptrdiff_t). The module never links liblua: /usr/bin/lua
#   (dynamic liblua.so.5.1.5) provides the symbols, as for every OpenWrt Lua C module.
# The build is reproducible: fixed flags, no build id, -ffile-prefix-map, stripped; the same inputs give the same bytes
# (canon_c.so.sha256 records the package file).
set -eu
mode=$1
here=$(cd "$(dirname "$0")" && pwd)
WARN="-std=gnu99 -Wall -Wextra -Werror -fvisibility=hidden -ffile-prefix-map=$here=router/native"
case "$mode" in
router)
  tc=$2; out=$3
  export STAGING_DIR=$(dirname "$tc")
  CC=$tc/bin/aarch64-openwrt-linux-musl-gcc
  STRIP=$tc/bin/aarch64-openwrt-linux-musl-strip
  mkdir -p "$out"
  "$CC" -Os -pipe -mcpu=cortex-a53 -fno-caller-saves -fstack-protector -fPIC $WARN -I"$here/lua-5.1.5-openwrt-21.02" \
    -shared -static-libgcc -Wl,-z,now -Wl,-z,relro -Wl,--build-id=none -o "$out/canon_c.so.debug" "$here/canon_c.c"
  "$STRIP" --strip-all -R .comment -o "$out/canon_c.so" "$out/canon_c.so.debug"
  "$tc/bin/aarch64-openwrt-linux-musl-readelf" -d "$out/canon_c.so" > "$out/canon_c.so.readelf-d.txt"
  "$tc/bin/aarch64-openwrt-linux-musl-readelf" -h "$out/canon_c.so" | grep -E 'Class|Machine|Type' > "$out/canon_c.so.readelf-h.txt"
  (cd "$out" && sha256sum canon_c.so)
  ;;
host-stock|host-lnum)
  out=$2
  inc=$here/lua-5.1.5; [ "$mode" = host-lnum ] && inc=$here/lua-5.1.5-openwrt-21.02
  mkdir -p "$out"
  ${CC:-gcc} -O2 -fPIC $WARN ${EXTRA_CFLAGS:-} -I"$inc" -shared -Wl,--build-id=none -o "$out/canon_c.so" "$here/canon_c.c"
  ;;
*)
  echo "usage: build.sh router <toolchain-dir> <out> | host-stock <out> | host-lnum <out>" >&2; exit 2;;
esac
