<!-- current-release-context:0.9.0 -->
> Component/lab reference, not current product-readiness evidence. [Current release and scope](../../docs/CURRENT-STATUS.md).

# OpenWrt virtual acceptance laboratory

This is a real OpenWrt 21.02.7 x86/64 guest kernel under QEMU TCG inside Docker. It is **not** GL.iNet firmware or a GL-MT6000 emulator. Do not use it as evidence for proprietary GL.iNet workers, hardware acceleration, production VPN switching, radio drivers or physical power-loss behavior.

Official image and SHA256: https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/
QEMU method: https://openwrt.org/docs/guide-user/virtualization/qemu
The old OpenWrt series is used to approximate the package's Python/UCI generation. It is for this isolated compatibility lab, not an Internet-facing deployment recommendation.

Build/run from the repository:

```sh
docker build -t homensai-vpn-qemu-lab lab/openwrt-qemu
docker run -d --name homensai-vpn-qemu --memory 1g --cpus 2 --security-opt no-new-privileges homensai-vpn-qemu-lab
docker cp lab/qemu_console.py homensai-vpn-qemu:/lab/qemu_console.py
docker exec homensai-vpn-qemu python3 /lab/qemu_console.py 'cat /etc/openwrt_release; ubus list'
```

No privileged mode, host network, host device, TAP, physical-interface bridge or published host port is required. Serial and management forwarding bind only to loopback **inside** the container. LAN and WAN are QEMU user networks. Package downloads use outbound NAT. Do not add production credentials or profiles.

Install Python and application dependencies with `opkg` in the guest. Transfer the checked IPK through a temporary HTTP server inside this container, reachable by the guest at 10.0.3.2. Verify SHA256 before `opkg install`. Wait for `ubus list` to show `homensai-vpn`: `rpcd` startup is asynchronous and TCG is slower than hardware.

`../openwrt_acceptance.py` refuses execution unless the guest identifies as x86/64 OpenWrt and `/tmp/HOMENSAI_VIRTUAL_LAB` exists. It uses synthetic profile metadata and real UCI/RPC/service operations, never enabling native Auto or sending Telegram messages. Read the script before running it; use a fresh disposable guest with no user data.

A disk persists only while this container's `/lab/openwrt.img` persists. Reboot tests preserve that disk. A QEMU process crash is a virtual abrupt power interruption; it does not reproduce flash hardware or the GL.iNet boot sequence.


The observed legacy disk/GRUB **warm reboot did not complete** within the lab deadline: the QMP display remained at Linux decompression, before application startup. Preserved-disk cold startup worked. `run.py --direct-kernel` optionally verifies/downloads the matching official kernel and uses `root=/dev/vda2`; this is an alternate boot path, not proof that the original failure was fixed. QMP is a private Unix socket inside the container; use `docker exec -u root ... python3 /lab/qemu_status.py` to inspect it.

`openwrt_recovery.py` kills only a PID whose exact argv identifies this application's monitor in the marked guest. It validates procd replacement and fresh status, keeping native Auto off. `openwrt_boot_check.py` records boot identity changes without exporting the identifier and has a bounded host-clock deadline. Test timings in guest clock and host wall clock must not be interchanged.
