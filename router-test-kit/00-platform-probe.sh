#!/bin/sh
# Read-only, stdout-only inventory. No network, flash access, installs or config writes.
# Run deliberately on the TEST device: sh 00-platform-probe.sh > platform.tsv
# Keep the report private. No hostname, MAC, serial, VPN settings or credentials.
LC_ALL=C
export LC_ALL
field() { printf '%s\t%s\n' "$1" "$(printf '%s' "$2" | tr '\t\r\n' '   ' | cut -c1-180)"; }
board=''
if command -v ubus >/dev/null 2>&1 && command -v jsonfilter >/dev/null 2>&1; then
    board=$(ubus call system board 2>/dev/null)
    for key in board_name model; do
        field "$key" "$(printf '%s' "$board" | jsonfilter -e "@.$key" 2>/dev/null)"
    done
    field openwrt_target "$(printf '%s' "$board" | jsonfilter -e '@.release.target' 2>/dev/null)"
    field openwrt_version "$(printf '%s' "$board" | jsonfilter -e '@.release.version' 2>/dev/null)"
else
    field board_name UNKNOWN
    field model UNKNOWN
    field openwrt_target UNKNOWN
    field openwrt_version UNKNOWN
fi
field schema 1
field kernel "$(uname -r)"
field architecture "$(uname -m)"
field gl_firmware "$(head -c 180 /etc/glversion 2>/dev/null)"
for tool in opkg apk python3 lua nft ubus rpcd jsonfilter sha256sum; do
    if command -v "$tool" >/dev/null 2>&1; then field "tool_$tool" PRESENT; else field "tool_$tool" MISSING; fi
done
field python_version "$(python3 --version 2>/dev/null)"
field lua_version "$(lua -v 2>&1 | head -n 1)"
field nft_version "$(nft --version 2>/dev/null)"
if command -v opkg >/dev/null 2>&1; then
    field package_architectures "$(opkg print-architecture 2>/dev/null | tr '\n' ';')"
    for pkg in python3 lua lua-cjson libuci-lua ip-full ubus rpcd luci-base ca-bundle; do
        if opkg status "$pkg" 2>/dev/null | grep -q '^Status: [^ ]* ok installed$'; then field "package_$pkg" INSTALLED; else field "package_$pkg" MISSING; fi
    done
fi
field overlay_free_kib "$(df -k /overlay 2>/dev/null | awk 'NR==2 {print $4}')"
field memory_available_kib "$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
# Partition labels establish only layout, never a bootloader version or recoverability.
if grep -qi 'u-boot\|uboot' /proc/mtd 2>/dev/null; then field bootloader_partition PRESENT; else field bootloader_partition UNKNOWN; fi
field bootloader_version UNKNOWN
field recovery_backup NOT_OBTAINED
for path in /usr/bin/rtp2.sh /usr/bin/setup_instance_via.lua /lib/functions/vpn_func/route_policy_func.sh /lib/functions/vpn_func/global_leak_drop.sh; do
    if [ -f "$path" ] && command -v sha256sum >/dev/null 2>&1; then
        field "sha256:$path" "$(sha256sum "$path" | cut -d' ' -f1)"
    else field "sha256:$path" UNKNOWN; fi
done
field native_switch REFUSED_UNCERTIFIED_TARGET
field installation NOT_AUTHORIZED_BY_PROBE
