# SDK build acceptance — NEXT-10

Status: BLOCKED pending a verified SDK for the documented vendor target/revision.
Package payload/mode parity and custom interpreted-IPK reproducibility are tested;
they are not a completed vendor SDK build.

The checked official [GL.iNet SDK README](https://github.com/gl-inet/sdk/blob/master/README.md)
lists older targets and does not identify a GL-MT6000 / firmware 4.11.0 SDK in that
table. Its instructions require a case-sensitive Linux filesystem and non-root
builds. The separate [MediaTek feeds repository](https://github.com/gl-inet/mtk-openwrt-feeds)
contains feed/build material; its existence does not establish an exact match to
the recorded vendor revision. These sources were checked on 2026-10-16. No claim
is made that an appropriate SDK is unavailable everywhere.

Required provenance before the full build:

- Supplier URL, immutable revision/archive SHA256 and licence/source metadata.
- Board/target: GL-MT6000, mediatek/mt7986, aarch64_cortex-a53.
- Match or explain divergence from OpenWrt 21.02-SNAPSHOT
  r15812+1095-46b6ee7ffc / vendor 4.11.0 / Linux 5.4.238.
- Preserve SDK `.config`, feeds revisions, compiler/libc metadata and dependency
  package versions. Never replace the user's router feeds to fit a build.
- Build in a dedicated Linux volume, not the Windows-mounted project tree.
- Place the reviewed package under the SDK package tree and run only its package
  target as a non-root user. Retain the complete log and resulting metadata/hash.
- Compare selected payload names, modes, bytes and dependencies with
  `router/stage_files.py` and the custom builder. Explain every difference.

Do not substitute a generic OpenWrt 24/25 or x86 SDK and label it the matching
4.11.0 build. No firmware flashing, host-wide package upgrades or router changes
are part of this acceptance step.
