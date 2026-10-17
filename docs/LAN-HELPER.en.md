# The LAN helper: what it is and how to run it

[Russian](LAN-HELPER.ru.md) · [How it works](HOW-IT-WORKS.en.md) · [Install](INSTALL.en.md)

> Experimental software. Read the [terms](../DISCLAIMER.md). A full trial briefly switches your VPN and can interrupt calls and downloads.

## What it is

A small script for **Windows, written in PowerShell 7**. The source is a plain text file, `client-test.ps1` (about 325 lines), in this repository under `router/files/www/luci-static/resources/view/homensai-vpn/`; the router page also serves it as “Download LAN helper”. You can open it in Notepad and read it before you run it.

It runs on **your computer**, not on the router. Its job is to prove, from the computer’s side, that the internet really works through the router before and after an automatic switch (gateway, router DNS, HTTPS and the VPN exit address). The router cannot see this by itself, which is why Auto asks for a passed LAN trial first.

What it does not do: it installs nothing, saves nothing (the router password is typed privately and kept in memory only), and changes no network settings of the computer. During a full trial it only adds two temporary probe routes and removes them at the end.

## Files

- `client-test.ps1` - the helper itself.
- `start-lan-helper.ps1` - a launcher that asks the questions (router address, cable adapter, mode) and starts the helper. `start-lan-helper.cmd` is a double-click wrapper for it.

Put the helper and the launcher in the same folder (the router page downloads the helper as `homensai-vpn-client-test.ps1`; the launcher finds either name).

## How to run

1. Install PowerShell 7 once: `winget install Microsoft.PowerShell`.
2. Prefer a computer connected to the router by a **LAN cable** (the cable is independent of Wi-Fi).
3. In the folder with the files run: `pwsh -NoProfile -File .\start-lan-helper.ps1`
4. Choose **1 · check only** first. It only reads and changes nothing.
5. If it passes, run it again and choose **3 · full trial**. It asks for the router password and the word `TEST`, switches to the reserve for a few minutes, checks the internet from the computer and confirms the result to the router.

Without the launcher the same thing is: `pwsh -NoProfile -File .\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly` (replace `3` with your cable adapter number from `Get-NetAdapter`; remove `-CheckOnly` for the trial; `-SelfTest` is an offline self-test).

If it stops with a code in capital letters, see Help → “The LAN helper fails” on the router page.

## Why it is not a Linux or phone app

It measures the path of a Windows computer on your LAN, using Windows networking commands (`Get-NetAdapter`, `Find-NetRoute`, `Get-DnsClientServerAddress`). A version for Linux or macOS does not exist yet; it is not required to run the product and could be added later.
