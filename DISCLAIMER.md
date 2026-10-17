# Experimental software: terms of use

[Русский](DISCLAIMER.ru.md)

**HomenS.AI Auto VPN is experimental software (alpha).** Read this before you install or use it. The same text is shown in the program the first time you open it, and Auto cannot be started until you accept it.

1. **It is experimental.** This is an early release. It has been tested only in a limited way, on a GL.iNet GL-MT6000 (firmware 4.11.0) and in a virtual OpenWrt, never on a wide range of devices, firmware versions or networks. It is not production software and must not be treated as such.
2. **It can interrupt your internet.** Switching a VPN route can drop calls, downloads and sessions for seconds or longer. A fault, a bug or an unexpected router state can leave devices on your network without internet until you repair the router by hand. Keep another way to reach the internet and the router, and make a private backup first (see the Help page and `router-test-kit/`).
3. **It changes router settings.** The program reorders your existing VPN rules and can add a temporary firewall rule. It does not edit your VPN keys. You can remove it at any time (`opkg remove homensai-auto-vpn`; see the Help page).
4. **No warranty.** The software is provided "AS IS" under the MIT License, without warranty of any kind, express or implied. The author and contributors are not liable for any damage, loss of data, loss of service, cost or other consequence of installing or using it.
5. **You are responsible.** You install and use it at your own risk. You are responsible for your router, your network, your VPN accounts, for following your VPN provider's terms and for the law that applies to you. Do not use it where an interruption could endanger people or property.
6. **Optional reports.** If you configure Telegram reports, summaries are sent through Telegram's servers with a bot token stored on your router. Nothing is sent unless you configure it.
7. **No promise of support.** Features, behaviour and these terms may change or be withdrawn in later versions; accepting them again may be required.

This text is not legal advice. If you need certainty about your obligations, ask a qualified lawyer.

## How acceptance works

When you open the program in LuCI for the first time, a full-page screen shows these terms. Two boxes must be ticked before the Continue button works. The acceptance (terms version and time) is stored on the router in the program's own configuration. Until it is stored, the controller refuses to switch anything (`TERMS-NOT-ACCEPTED`) and the Start button for Auto is refused. If the terms change, their version number changes and you accept again.

If you do not accept, remove the package and leave your router as it was. Your VPN rules are not changed by the monitor itself.

Terms version: 1.
