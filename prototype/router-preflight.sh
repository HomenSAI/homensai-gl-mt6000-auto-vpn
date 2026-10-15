#!/bin/sh
# Read-only inventory. Does not run probes, show credentials, or change routes.
# To run later on the router: sh router-preflight.sh
set -u
printf '%s\n' 'VPN failover preflight: read-only; no settings changed'
printf '%s\n' '--- Model and firmware ---'
for path in /proc/gl-hw-info/model /etc/glversion /etc/openwrt_version; do
    if [ -r "$path" ]; then
        printf '%s: ' "$path"
        head -n 1 "$path"
    fi
done
printf '%s\n' '--- Available commands ---'
for tool in ubus jsonfilter uci ip curl lua python3 lock flock procd; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '%s: available\n' "$tool"
    else
        printf '%s: absent\n' "$tool"
    fi
done
printf '%s\n' '--- Interfaces (selected nonsecret fields only) ---'
if command -v ubus >/dev/null 2>&1 && command -v jsonfilter >/dev/null 2>&1; then
    for iface in wan lan ovpnclient2 ovpnclient3 wgclient1; do
        printf 'interface=%s\n' "$iface"
        status=$(ubus call "network.interface.$iface" status 2>/dev/null) || {
            printf '%s\n' 'status=unavailable'
            continue
        }
        printf '%s\n' "$status" | jsonfilter -e 'up=@.up' -e 'pending=@.pending' -e 'device=@.l3_device'
    done
fi
printf '%s\n' '--- IPv4 policy rules ---'
ip -4 rule show 2>/dev/null || :
printf '%s\n' '--- IPv6 policy rules ---'
ip -6 rule show 2>/dev/null || :
printf '%s\n' '--- Routing tables observed in earlier audit (may have changed) ---'
for table in main 1001 1012 1013; do
    printf 'table=%s\n' "$table"
    ip -4 route show table "$table" 2>/dev/null || :
done
printf '%s\n' '--- Space and memory ---'
df -k /overlay /tmp 2>/dev/null || :
if [ -r /proc/meminfo ]; then
    sed -n '/^MemTotal:/p; /^MemAvailable:/p' /proc/meminfo
fi
printf '%s\n' 'Complete. This inventory does not prove internet health or verified probe routing.'
