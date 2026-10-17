# How HomenS.AI Auto VPN works — read this before installing

[Russian](HOW-IT-WORKS.ru.md) · [Install](INSTALL.en.md) · [Terms of use](../DISCLAIMER.md)

> Experimental software for the GL.iNet GL-MT6000 (Flint 2). It can interrupt your internet and, when Auto is on, changes router VPN settings. Use at your own risk.

## What it is

An add-on page for the router (Services → HomenS.AI Auto VPN) that watches the VPN profiles you already created in GL.iNet (VPN → VPN Dashboard), shows which ones work and how they behaved over time, and — only if you switch Auto on — can move traffic from your main VPN to a reserve one when the main one fails, and back when it recovers. It does not create VPN profiles, import keys or connect VPNs that you did not connect.

## Where it is installed

It is one software package (`homensai-auto-vpn_<version>_all.ipk`) installed on the router itself, not on your computer. It adds:

- the web page and its scripts under `/www/luci-static/resources/view/homensai-vpn/`;
- the program (Python and Lua) under `/usr/lib/homensai-vpn/` and `/usr/libexec/rpcd/homensai-vpn`;
- its own settings file `/etc/config/homensai_vpn` and a service `homensai-vpn` (`/etc/init.d/homensai-vpn`);
- a recovery helper `/usr/sbin/homensai-vpn-emergency`.

It needs these standard OpenWrt packages from the vendor feeds: python3, lua, lua-cjson, libuci-lua, ip-full, ubus, rpcd, luci-base, ca-bundle.

## How it is installed

1. Download the `.ipk` and its `.sha256` from the same release and compare the checksum.
2. Either LuCI → System → Software → Upload Package → Install (never “Flash Firmware”), or over SSH:

```sh
scp homensai-auto-vpn_<version>_all.ipk root@192.168.8.1:/tmp/
ssh root@192.168.8.1 "sha256sum /tmp/homensai-auto-vpn_<version>_all.ipk && opkg install /tmp/homensai-auto-vpn_<version>_all.ipk"
```

3. Open Services → HomenS.AI Auto VPN, read and accept the terms, press Start on the monitor service. Keep Auto off until you have tested.

Remove it completely with `opkg remove homensai-auto-vpn`.

## How it works

1. **Monitor (always, read-only).** About every 30 seconds it checks, through each connected VPN, that the internet really works (an HTTPS request), and keeps short-term statistics. Nothing is changed.
2. **Setup.** In Settings you pick a primary and a reserve profile and (optionally) Telegram reports.
3. **Step 1 · Check the VPNs now** on the Overview page tests all connected VPNs immediately.
4. **Step 2 · Auto.** After a test from your own computer on the LAN (the “LAN helper”) passes, you may switch Auto on. If the primary fails several checks in a row, the program switches traffic to the reserve using the router’s own VPN policy, waits for your computer to confirm that the internet works, and otherwise rolls back. When the primary is stable again it returns (or waits for your “Return to primary”, depending on the rule you chose).
5. **Safety.** While a switch is in progress an owned traffic block prevents leaks; if anything goes wrong it is removed on a timer. The traffic light on the page shows the state; Help → “I have no internet” lists the recovery commands.

## What it changes — and what it does not

- Auto OFF: it only reads. No routes, DNS or firewall rules are changed.
- Auto ON, during a switch: it changes which VPN profile carries traffic and adds and removes its own firewall table `homensai_vpn_guard`.
- It does not change your Wi-Fi, LAN, DHCP, passwords or the GL.iNet firmware, and does not send your data anywhere except the optional Telegram messages that you configure.

Before relying on it, read the terms, test with Auto off, and keep a way to reach the router that does not depend on the VPN.
