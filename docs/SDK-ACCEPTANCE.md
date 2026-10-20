# SDK build acceptance — NEXT-10

Matching vendor SDK: BLOCKED pending verified provenance for the observed device/firmware.
Generic upstream SDK work is separate; see the 20 October checkpoint below.
Package payload/mode parity and custom interpreted-IPK reproducibility are tested;
they are not a completed vendor SDK build.

## Current bounded result: exact committed alpha12 source

**PASS for the generic SDK child-package payload target** at source commit
`586a2a5305dbb638dfeac05755c8f9e1de736408`. The committed root-context exporter preserved
repository-root attributes and rewrote only the TAR path prefix. The source snapshot
contains **293 files**, TAR SHA256
`4b50f923b4bfb13ab74d23ce0959585d67e744790b21adb7101cc5ee89edf061`.

| Evidence | Verified result |
| --- | --- |
| Both clean SDK child-target builds | `homensai-auto-vpn_0.9.0-alpha12-1_all.ipk`, **657566 bytes**, SHA256 `1fbefecb251b1ff171cf316d035528bf9baebdb26089a6327480008b92043ea3` |
| Same-source custom reference | **654970 bytes**, SHA256 `d7a2b47e1c3afc4b6c042e7f1ea1b23941d438630915fd9b83597ae381203b29`, exactly matching the canonical alpha12 package |
| Architecture / repeatability | `Architecture: all`, `_all.ipk` filename and byte-identical complete SDK packages after two clean builds |
| Payload / lifecycle parity | All **69** selected paths, modes and bytes match the canonical custom package; hooks match with only the exact pinned SDK wrappers and implicit libc dependency described below |
| Source / receipt consistency | All **293** actual SDK package source file hashes match the exact committed export; both command receipt/log chains and package SHA256 values are checked |
| Package Makefile | SHA256 `28b3f4842abb0d08378ea5b94645971382657a329f9a1172b80e1fe94f6b4da8` in the actual SDK package tree |

Both builds used the verified upstream 21.02.7 x86/64 SDK, UID 10001, network none and the
standard SDK child package rules. The compiler/runtime dependency graph was **not** rebuilt
recursively. The SDK IPK differs from the canonical custom IPK because of the documented
SDK control metadata/wrappers; it is a separate private proof artifact, not a replacement
release asset. No package dependency, vendor guard or payload was removed to obtain this result.

The reviewed current result is in [SDK-UPSTREAM-2026-10-20.json](../qa/SDK-UPSTREAM-2026-10-20.json).
Private `commit586-first`, `commit586-second`, `commit586-reference` logs/artifacts and the
source/evidence indexes retain the complete proof. Older working-snapshot and rejected
subtree-export experiments below remain historical; they do not override this exact-source
payload result. Full recursive runtime-dependency compilation, a matching GL.iNet firmware
SDK, native adapter certification and device acceptance remain open. This SDK proof grants no
installation permission and does not execute or accept the first-run terms.

### Preserved exact alpha11 checkpoint

The previous exact-source payload proof at
`82591bd30e1aba7353169a1488f4b19b60bd6dfd` remains valid for that checkpoint: 292 source
files, source TAR SHA256 `612ef3da83013ae18ffca43657d1dd63824c7ba34da17aec42de13547dcbff4a`;
two identical 657285-byte SDK packages, SHA256
`24559785d6cdcd4e42f7809eee456c96e425b27524aeaf7394f2d553015adfa7`; exact canonical
654655-byte custom reference, SHA256
`f196ef07d85b4cb7edaeed8092dc5978bb3ad86845ce0c6b4ce86674e2126f4c`.
All 69 payload files and lifecycle hooks matched under the same narrowly documented SDK
differences. Its private `commit825-*` artifacts, source/evidence indexes and aggregate copy
are retained. The current alpha12 result supersedes only the current-candidate pointer.

The checked official [GL.iNet SDK README](https://github.com/gl-inet/sdk/blob/master/README.md)
lists older targets and does not identify a GL-MT6000 / firmware 4.11.0 SDK in that
table. Its instructions require a case-sensitive Linux filesystem and non-root
builds. The separate [MediaTek feeds repository](https://github.com/gl-inet/mtk-openwrt-feeds)
contains feed/build material; its existence does not establish an exact match to
the recorded vendor revision. These sources were checked on 2026-10-16. No claim
is made that an appropriate SDK is unavailable everywhere.

Required provenance before the full build:

- Supplier URL, immutable revision/archive SHA256 and licence/source metadata.
- Historical target to explain: GL-MT6000, mediatek/mt7986, aarch64_cortex-a53.
  This is not the identity of the new mobile GL-MT3000 test device, which has not
  been connected. Its actual firmware/bootloader/target remain unobserved.
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

## 20 October 2026: generic upstream SDK evidence

The official [GL.iNet SDK README](https://github.com/gl-inet/sdk/blob/d8ad57d4474c2978ea3c9a530ee48c414c057bab/README.md)
and [download selector](https://github.com/gl-inet/sdk/blob/d8ad57d4474c2978ea3c9a530ee48c414c057bab/download.sh)
still enumerate older targets without establishing this exact vendor firmware SDK.
Read-only Git ref checks on 20 October resolved SDK master to
`d8ad57d4474c2978ea3c9a530ee48c414c057bab` and the separate
[MediaTek feeds](https://github.com/gl-inet/mtk-openwrt-feeds/tree/35a658aadcf5bfa6a23a750ebc36074a46308c89)
master to `35a658aadcf5bfa6a23a750ebc36074a46308c89`. A feed revision is not a firmware
SDK match, and this review does not prove no suitable SDK exists elsewhere.

The [official OpenWrt 21.02.7 x86/64 SDK listing](https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/)
and [supplier checksum list](https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/sha256sums)
identify `openwrt-sdk-21.02.7-x86-64_gcc-8.4.0_musl.Linux-x86_64.tar.xz`.
It was downloaded to private storage: **120343288 bytes**, SHA256
`21c75e4c5a429da487f8a885555cb49eee80cfc355d5dbe35d2b3ae05324a09d`.
This is an upstream x86 SDK, not a GL.iNet MT6000/MT3000 SDK. Matching the downloaded
HTTPS checksum is recorded separately from signature verification, which was not performed.

The dedicated [SDK Dockerfile](../qa/sdk/Dockerfile) prepares Debian build tools in
an isolated image. Build with `docker build --pull=false -t homensai-vpn-sdk:20261020 qa/sdk`;
do not use the entire private workspace as build context. The prepared image digest was
`sha256:01bf22e30db44d49d4d0d8b7ca812f219d33932fec1ca59690fda11915305cf8`.
Debian package acquisition is a preparation step; actual package builds use network none,
UID 10001, a read-only root, bounded resources and a new Linux volume. No preserved VM,
physical router, host package installation or service modification is involved.

The historical first experiment used `git archive HEAD:router` from baseline commit
`8c5433990f825890dcdf60e5b81f5c9a74466530`; source TAR SHA256
`3a25fcd702a8434f94491d0f6432490bbcdc0bfda917b93cbde48ec0e890a93c`.
Concurrent working-tree changes are excluded. Later Makefile-only experiments record the
actual overlaid Makefile SHA separately and must not be called that exact committed tree.
At that checkpoint, final-source acceptance required a new immutable snapshot after the
pending product changes; the exact alpha11 payload proof above now closes that source gate.
The later source-export investigation below rejects that subtree shortcut for canonical
source comparison because it discards repository-root attributes.

The first real `make defconfig` and `make -j1 package/homensai-auto-vpn/compile V=s`
both exited zero, in 20.401 s and 43.838 s. This first stage is **PARTIAL**, because
the SDK did not yet have the package dependency feeds installed. Its 69 payload files
exactly match names, modes and bytes from a custom-builder package produced from the
same archived source. Same-source custom reference: 648793 bytes, SHA256
`156577602dc939848e16890d833bf0c60a7e2c25fe4d1b14157673fc4997b47b`.
This reference is not a published release asset. Comparing a different release previously
showed 11 style text CRLF/LF differences; that cross-source comparison is not parity proof.
The existing staging code preserves raw style bytes correctly and was not modified.

The actual SDK exposed a packaging defect: global `PKGARCH:=all` was overridden by
the default package definition, emitting an x86_64 package. The SDK-specific fix moves
`PKGARCH:=all` into `define Package/homensai-auto-vpn`. Verification must inspect both
the `_all.ipk` filename and `Architecture: all`; a successful make exit alone is insufficient.

Standard SDK control metadata adds implicit `libc`. Its exact default postinst/prerm
wrappers dispatch to `postinst-pkg`/`prerm-pkg`; those package-hook bytes and modes must
match the custom hooks. `preinst` and `conffiles` must match directly. The evidence checker
permits only those pinned wrapper bytes and that dependency difference, rejecting changed
hooks, extra dependencies, payload/mode changes and unexplained control entries.

Pinned source feeds prepared separately from the offline build:

| Feed | Immutable revision | Downloaded TAR SHA256 |
| --- | --- | --- |
| Base, upstream tag v21.02.7 | `57a6d97ddf8f6541a52e0f8fad8c6f47685a1bc3` | `d1a7e71cababe3e6cf95a892b4476cbd34f36ce4b30f82f09101168141c2bec8` |
| Packages | `48242ee7a190db7740f7b9b3ef1debfa4d5857f6` | `8cee4b764fd5e9829c48a0b5e9bf23ad4ab5579c50cdf1daa0aef43b222f976e` |
| LuCI | `e98243ef9eb838cca80cdd6d1bd0cf69a509d103` | `653556192de032ff9a98f6e486bb540eaaa92a9068f7c76af4e29bcf795d5eb4` |

Packages/LuCI commits came from the verified SDK feed configuration. The base tag was
resolved read-only against the official upstream Git repository. Archives came from the
official OpenWrt GitHub mirrors; their listed hashes were computed locally after download.
The SDK uses local links to those pinned snapshots, not floating feed updates.

With real feeds installed, a further compile correctly refused to obtain missing sources
under network none. The attempt was stopped while retrying a pinned ca-certificates source
download; it is retained as **STOPPED**, not a passing complete build. SDK defaults also
select a very broad package set, so downloading all configured packages blindly is unsuitable.
Preparation must follow the exact recursive package dependency graph and retain source hashes
before a full credential-free offline dependency build. Full recursive dependency compilation
remains open; the exact alpha11 payload/source repeatability proof above is a separate bounded result.

### Bounded alpha10 payload result

A current working snapshot was frozen after generation of alpha10: **291 router source
files**, source TAR SHA256
`eb179e4c6bb615ba9f13f3af7b96ef3aba41a34fe9689815dbb23729cc22e6c8`.
Its baseline commit is the older `8c5433990f825890dcdf60e5b81f5c9a74466530`; the snapshot
includes pending product changes and is explicitly **not that exact committed tree**.
The actual package Makefile SHA256 was
`84ac33a8484079503a625b99d896b406195722a0cf274985ad911fa09f40a985`.

With full pinned feed metadata available, two real SDK child-package clean/compile runs
completed offline. The package command was:

```sh
make -j1 -C package/homensai-auto-vpn TOPDIR=/work/first V=s clean
make -j1 -C package/homensai-auto-vpn TOPDIR=/work/first V=s compile
```

This invokes the standard SDK package rules/install/hooks while **excluding recursive
runtime-dependency compilation**. It is a bounded generic payload acceptance result,
not completion of `make package/homensai-auto-vpn/compile` with its full dependency graph.
No errors were ignored and no package dependency declaration or vendor guard was removed.

| Evidence | Verified result |
| --- | --- |
| Both SDK payload packages | `homensai-auto-vpn_0.9.0-alpha10-1_all.ipk`, **656757 bytes**, SHA256 `5c0fa20bfa238c323625a0b95de04dca90697a559e66828187278330796d5630` |
| Architecture | Filename `_all.ipk` and `Architecture: all` both verified after the Makefile fix |
| Repeatability | Two clean SDK child-target builds produced byte-identical complete IPKs |
| Same-snapshot custom reference | **654099 bytes**, SHA256 `9c077f5cc235f95c028f9ec35fa573e0880e7276fc566480199f326f73a3ac98` |
| Payload / hooks | All **69** selected payload names, modes and bytes match; lifecycle hooks match with only the exact SDK wrappers and implicit libc dependency described above |
| Source consistency | Collector rechecked all **291** frozen source file hashes in the actual SDK package tree, both attempt receipts, command exit codes and log hashes |
| Checker regressions | **11 tests PASS**, 0 failures, 0 skips; final recorded run **0.242 s** |

Raw input archives, logs, package artifacts and the evidence index/result remain private
under `private/sdk-20261020/`. [collect-sdk-evidence.py](../scripts/collect-sdk-evidence.py)
checks the actual snapshot/attempt linkage and generates this index after builds and a
same-snapshot custom reference exist. [The reviewed aggregate](../qa/SDK-UPSTREAM-2026-10-20.json)
contains no raw device data. The result is EVIDENCE-CONSISTENT with vendor/device/install/native
acceptance explicitly false. Do not publish the private evidence tree as a release artifact.

The separate `homensai-vpn-sdk-20261020` Linux volume preserves the SDK and previous package
source. Every named test/build container used `--rm` and exited after its bounded command;
the stopped full-dependency attempt was not resumed automatically. Preserved VM disks and
physical routers were not used. This historical working-snapshot result was later superseded
by the exact committed alpha11 payload rerun above. A full recursive dependency build remains
separate; an upstream x86 SDK cannot establish the observed
GL.iNet firmware SDK provenance or native adapter compatibility.

## Evidence tooling and acceptance limits

Use [export-sdk-source.py](../scripts/export-sdk-source.py) to prepare the SDK source:

```text
python scripts/export-sdk-source.py --commit FULL_40_CHARACTER_SHA --archive PRIVATE_SDK_SOURCE.tar
```

It runs `git archive FULL_SHA -- router` with repository-root attribute context, then
strips only the TAR member prefix in memory. It never checks out/extracts source files,
overwrites an existing archive/index, or changes Git. Its JSON index records the exact
commit, input bytes/hash/count and `source_strip_components: 0`. The build runner consumes
that rewritten TAR directly. The fixture regression deliberately sets `core.autocrlf=true`
and a root `-text` rule, verifies exported bytes equal the committed blob, and demonstrates
that `FULL_SHA:router` changes the pinned asset bytes. Git-dependent tests explicitly skip
where Git is unavailable; they were executed in the Linux SDK tool image.

### Retained rejected export experiment at commit 9847811

Two direct SDK builds from the subtree shortcut at
`984781141d5eddce4442941ee28ff851da7cbf28` reproduced the same IPK, but **canonical release
equivalence was rejected**. Subtree source TAR SHA256 was
`704fdc1b3c110f8b57ce3251542151abb7c87e28c7fcc32d71f4eeabe6a736db`;
the resulting SDK package was 656898 bytes, SHA256
`49982dbb2bf585b3097efa1a6c15be04fe1e42ac40edcacd1902aa2edd407c32`.
Its same-export custom reference was 654226 bytes, SHA256
`cfddd22f1dda72a555e85eec894d79c4b09266a9a0506b1b53c632e8960b0e9c`,
which differs from canonical 654099-byte reference `9c077f5c...` above.

This was an SDK source-preparation error, not a product/staging defect. Root attributes
mark `style/**` as `-text`; using a subtree as the archive root lost that rule and enabled
CRLF conversion in 11 style text assets. The payload differences were EOL-only, with equal
paths/modes and lifecycle hooks. For `style/css/tokens.css`, the raw Git blob and root-context
archive both contain 10442 bytes, SHA256
`3d512fb0833321bf7709dd1a8e3468b22190683c716d10b7c82d27b53183ed14`;
the subtree export contains 10786 bytes / 344 CRLF pairs, SHA256
`4d6ca08915f2d22396904d6ed61b7e78ae35a265516efcdb869403518c86ca13`.
The builder and staging code were not changed. Private failed-run logs/artifacts and the
11-path hash/size rejection record are retained. The corrected canonical rerun was performed
on the next frozen alpha11 commit listed above; no additional 9847811 SDK runs were started
after the cause was found. This rejected attempt is never counted as canonical release parity.

[run-upstream-sdk.py](../scripts/run-upstream-sdk.py) checks the pinned SDK/source hashes,
refuses root and reused output directories, uses bounded subprocesses, records individual
make exit codes/log hashes and distinguishes configuration-only from compile commands.
Archive extraction and compilation belong inside the dedicated Linux volume. A successful
command record is not a claim that dependency resolution, package parity or installation passed.

[check-sdk-evidence.py](../scripts/check-sdk-evidence.py) reads an evidence JSON index and
local files only. It requires schema 1, `sdk_scope: upstream`, a source commit, the official
HTTPS release SDK URL, and distinct files with declared SHA256 for `sdk_archive`,
`supplier_checksums`, `config`, `feeds`, `toolchain`, `licence`, `build_log_first`,
`build_log_second`, `package_first`, `package_second`, and `reference_package`.
Paths are relative to the index directory. Absolute/escaping paths, missing/changed evidence,
floating feed pins, package traversal/links/duplicate members, nonreproducible package bytes,
wrong metadata/dependencies and payload/hook/mode differences refuse.

Run `python scripts/check-sdk-evidence.py PRIVATE_EVIDENCE.json` locally. A consistent index
returns **EVIDENCE-CONSISTENT**, never a vendor SDK or hardware acceptance PASS. Evidence
indexes, logs and checksums can be authored by anyone; actual build execution, supplier origin
and their relation to the source snapshot still require independent review. The checker
always keeps vendor firmware match, installation and native certification false, and rejects
attempts to relabel generic evidence as a vendor build. Negative tests are in
[test_sdk_evidence.py](../qa/test_sdk_evidence.py).
