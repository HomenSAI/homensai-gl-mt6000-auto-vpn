<!-- doc-role: current -->
# Native OpenWrt application

Source identity is in [VERSION.json](../VERSION.json); installed/published evidence is in [CURRENT-STATUS](../docs/CURRENT-STATUS.md). The repository name retains MT6000 history, while qualified prepared continuous mode is the documented MT3000/4.11.0 path. Do not infer arbitrary firmware/device acceptance from architecture `all`.

- [Install RU](../docs/INSTALL.ru.md) / [EN](../docs/INSTALL.en.md), then [setup](../docs/FIRST-RUN-SETUP.md).
- Source: `router/files`, current `.inc.js` fragments, generator and selected immutable module/CSS. Older dashboard files are preserved generator/history inputs; only the selected pair is packaged.
- Build/verify from the exact committed archive in [pinned CI](../docs/CI-PRIMARY.md); a host build is not canonical until hashes match.
- Helpers: installed emergency tool and Windows LAN witness/launcher, each with a different side-effect scope. Never run the Windows helper on the router.
- Modes: continuous router-probed pair, optional external-LAN bounded trial and separate router-hosted evidence. No automatic credentials import, unmanaged profile creation or direct-WAN fallback is implied.

[Behavior](../docs/HOW-IT-WORKS.en.md) · [Validation](../docs/VALIDATION.md) · [History](../docs/HISTORY-RETENTION.md) · [Recovery](../router-test-kit/EMERGENCY.md).
