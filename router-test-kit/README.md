> Состояние на24.10.2026 / Status24Oct2026: разработка alpha11; public stable0.9.0; physical baseline alpha9; VM evidence alpha10. [Текущее руководство](../docs/CURRENT-STATE.ru.md) · [Current guide](../docs/CURRENT-STATE.en.md). Pinned release instructions below apply to their stated version; dated evidence is not current hardware certification.

# Router test kit — 0.9.0

Use the matching `homensai-auto-vpn_0.9.0-1_all.ipk` and `.ipk.sha256` from [v0.9.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0). `02-install.sh` pins the canonical SHA256/size/version; never copy an older kit for a newer package.

Read [installation](../docs/INSTALL.en.md), [установка](../docs/INSTALL.ru.md) and [scope](../docs/CURRENT-STATUS.md). Keep independent management access and a verified PRIVATE backup. Stop Auto normally and verify cleanup before upgrade. Do not force installation, replace feeds, mass-upgrade packages or upload backups/secrets.

1. `01-preflight.sh`: read-only model/firmware/dependency/storage checks.
2. `02-install.sh /tmp/homensai-auto-vpn_0.9.0-1_all.ipk`: verify exact hash/size, refuse active/unverified native state, install normally.
3. `03-verify.sh`: confirm installed version/services; read its actual result.
4. `04-uninstall.sh` / `05-emergency.sh`: deliberate recovery tools; read before use and verify the result, not only the command exit.

This is an application, not firmware. The kit alone does not authorize native preparation, Auto/fault trials or certify LAN traffic. The current continuous mode is qualified on the separately prepared MT3000/4.11.0; monitor-only installation and explicitly requested Auto startup are distinct steps. After router/application restart, Auto requires explicit Start.
