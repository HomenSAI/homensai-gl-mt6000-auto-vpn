<!-- doc-role: current -->
# Router installation/test kit

This checkout's `02-install.sh` and `03-verify.sh` pin the candidate in [VERSION.json](../VERSION.json), not automatically stable0.9.0. Obtain the complete kit and IPK/checksum from **one chosen tag**. For stable0.9.0 use that tag's kit; never mix it with this branch's newer package.

1. Read [RU install](../docs/INSTALL.ru.md) / [EN install](../docs/INSTALL.en.md), actual platform scope and scripts. A model/architecture string does not prove native readiness.
2. Keep independent management access and a verified private recovery export. Normal Stop/cleanup precedes an upgrade; queued ACK is insufficient.
3. `01-preflight.sh` checks platform, dependencies and writable storage. Its report is local; it does not install/flash/enable Auto. Other `00-*` probes have their own stated scope.
4. `02-install.sh /tmp/<matching-package>.ipk` verifies the pinned hash/size/version and lifecycle gates before normal opkg. `03-verify.sh wait` checks runtime/services; read its actual result.
5. `04-uninstall.sh` and [emergency helper](EMERGENCY.md) are deliberate recovery operations. Never use force, arbitrary rule reordering or removal of vendor protection as an installation shortcut.

This is an application, not firmware. Setup does not accept terms or start Auto. Prepared continuous MT3000 mode and the optional client-confirmed trial have different prerequisites; restart requires explicit Auto Start.
