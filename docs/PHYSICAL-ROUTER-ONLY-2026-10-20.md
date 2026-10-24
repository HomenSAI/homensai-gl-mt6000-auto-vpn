<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# GL-MT3000 router-only continuation - 20 October 2026

The owner confirmed independent portable-router VPN profiles, personally accepted terms version1, and selected router-only testing for this stage. Fresh device readback confirmed legal acceptance; no agent accepted terms. Physical first-run completion/edit persistence remains separate and unverified until the owner saves the wizard. Windows Wi-Fi stayed on the primary network; no host adapter/address/route settings were changed.

After an owner-reported uplink/VPN change, stock WireGuard and OpenVPN were already up. Separate existing-connection probes bound sockets to each actual device/mark/table and rechecked route identity afterwards. Both returned two successful HTTPS controls and successful DNS; observed exits differed. These are router-originated checks, not LAN/IPv6 leak proof. The cable-bound host probes failed locally with WinError10051; they were not replaced with traffic over the working Wi-Fi.

## Bounded WireGuard activation and stop

The previous state was encrypted before changes. Both configured clients were explicitly saved disabled=1 and brought down through stock controls; profile/key data, routing rules and wireless settings were not edited. A private independently reviewed controller armed a detached cleanup actor before any forward action, temporarily disabled only the stock vpn-client startup gate to suppress firmware server retries, and invoked the stock ifup -w path for the same WireGuard profile. This path reloads netifd and may perform setup/down/setup; it does not invoke the Wi-Fi helper and is not described as a single protocol attempt.

Retained attempts are distinct:

| Attempt | Result |
|---|---|
| 01 | REFUSED before ARM: owner state had changed both saved VPN flags. No activation/config/boot mutation. |
| 02 | ABORTED after3.48s: the harness incorrectly treated nonzero but decreasing startup work as growing queue. Cleanup PASS with15s quiet and exact boot restoration. This is not a firmware/startup failure. |
| 03 | Bounded activation/data/stop PASS after correcting that observed predicate and retaining all actual fault guards. |

Attempt03 observed WG up and fresh handshake at4.826s after test birth (ifup dispatch0.777s). Its17 samples over roughly20s contained no recursive FW3, lock wait or retry worker. Minimum available RAM was204972KiB. During the active interval, an independent read-only bound probe returned two successful HTTPS controls, valid DNS and a stable route/device epoch. The foreground ended with OBSERVATION-COMPLETE at21.765s; cleanup saved disabled=1 at21.993s and restored the exact original startup link at42.360s after continuous15s quiet. Later host-triggered reads confirmed both VPNs disabled, no FW3/rtp/flock/vendor backlog and management access.

The cleanup result alone is not a startup PASS: attempt02 also cleaned up successfully. The final verdict combines foreground completion, fresh handshake, actual bound data probe, independent cleanup and post-restore checks. Isolated controller checks19/19 include process-death and mocked-device regressions; no physical SSH-loss/process-crash test is claimed. No vendor script patch, firewall restart/flush, old-PID recovery or firmware/power action was used.

This ran with installed alpha15. Alpha16 changes only the Calm default and current page asset; its installation is verified separately. Native application switching remains off and unsupported on this stock MT3000 target. Firmware-owned server rotation, automatic channel switching, LAN witness/IPv6/Kill Switch/special-rule behavior and unattended/power recovery remain open. The permanent stock FW3 restart recursion and recorded latent DNAT/MAC-block ordering issue are not closed by this bounded test.

Raw receipts and encrypted backups remain private in portable-router-access-2026-10-20. Only reviewed conclusions are public.

## Alpha16 installed acceptance

The canonical alpha16-1 IPK (696460 bytes, SHA256 `3678843ab1873bb2537832cad3f34b4ed14990a89853346a0628662d96536b8a`) installed successfully. All69 program files matched the package. Network, wireless, firewall, DHCP and the existing application conffile remained byte-identical across this upgrade; this comparison does not refer to the initial pre-recovery state.

Nine post-install checks passed: expected version, explicit monitor-only deployment, sole running monitor, optional/native functions off, no native journal or owned guard, preserved owner terms, vendor observation schema and Calm appearance default. A fresh normal LuCI login returned HTTP200; dashboard67 and ui44.css both matched the canonical package hashes. The probe did not accept terms or save setup. Existing terms version1 was read back separately; physical onboarding_complete remained false.

The device opens B · Calm when no valid preference exists, while preserving explicit saved designs. Both portable VPNs remain saved disabled=1 after the bounded test, and the original stock startup link is restored. A physical first-run Save/Settings round trip remains pending the owner's selected values; no draft was overwritten.
