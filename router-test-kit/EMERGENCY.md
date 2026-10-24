<!-- doc-role: current -->
# Восстановление доступа / Emergency recovery

Start with the intended router identity and a working management path. Identical private addresses on Wi-Fi/Ethernet can lead to different devices. Keep client traffic evidence separate from router reachability.

## Сначала чтение / Read first

Use the installed helper, or the matching-tag `05-emergency.sh` if needed:

```sh
homensai-vpn-emergency show
```

Keep output local. Journal/policy/status data can include private addresses, identifiers and transaction data; redact before sharing. A working reserve is not a reason to force return to an unhealthy primary. On Overview use current readiness and normal manual/return controls when available.

## Управляемая остановка / Managed stop

```sh
homensai-vpn-emergency stop-auto
```

This stops own services and attempts to disable the saved Auto flag. Stop can restore managed routing policy/interface flags; **it is not read-only and not a promise of no network effect**. Pending own UCI edits are not committed by the helper: it reports refusal after stopping services; resolve those edits deliberately before retrying. Verify the resulting phase, policy and client path.

If only a verified owned guard remains after services stop:

```sh
homensai-vpn-emergency remove-guard
```

It removes only the application's identified table, not stock KillSwitch or foreign tables. Never flush the whole firewall. If policy restoration is unconfirmed, compare private journal/baseline and preserve evidence; do not guess `uci reorder` indexes or archive the journal just to make the warning disappear.

`close-journal` is an administrator-only deliberate archive **after** independently restoring/verifying the required policy and stopping the supervisor, not an ordinary repair step. A retained reserve is not proof that the original route returned.

After recovery, `homensai-vpn-emergency start` starts own services. Confirm fresh monitoring; continuous Auto still needs explicit Start and readiness. Reboot is a last deliberate recovery step and does not repair wrong VPN credentials. Do not factory-reset, flash firmware, delete VPN profiles or disable vendor protection as a shortcut.

[Помощь и режимы](../docs/CURRENT-STATE.ru.md) · [English guide](../docs/CURRENT-STATE.en.md) · [LAN witness](../docs/CLIENT-TRIAL.md).
