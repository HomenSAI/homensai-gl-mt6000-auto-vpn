# External prerequisites and evidence boundaries

Reviewed 2026-10-17. No physical router access is authorized in this work window.

## Matching SDK

Official GL.iNet SDK repository master d8ad57d4474c2978ea3c9a530ee48c414c057bab and its download.sh enumerate older target SDKs; no exact GL-MT6000/MT7986 firmware 4.11.0 SDK provenance was established. Official firmware download availability is not SDK equivalence. The official mtk-openwrt-feeds repository contains relevant MT798x integration, but does not itself establish the exact firmware SDK revision.

Sources: https://github.com/gl-inet/sdk/blob/master/README.md ; https://github.com/gl-inet/mtk-openwrt-feeds ; https://dl.gl-inet.com/release/router/release/mt6000/4.11.0 . A standard matching-vendor SDK build remains BLOCKED pending target, feed revisions and toolchain provenance. Existing reproducible interpreted ipk packaging is tested separately and is not advertised as an SDK build.

## Gitea server-triggered CI

The existing local immutable runner executes two installed runtime images with network none, read-only root, UID 65534, all capabilities dropped, no-new-privileges, bounded memory/CPU/PIDs and no credentials or Docker socket in child jobs. It propagates failure before issuing a PASS receipt. This is local CI, not proof of activated Gitea Actions or untrusted PR automation. A read-only unauthenticated repository API query returned HTTP 404; it does not prove repository absence. No repository-scoped runner credential/server administration path is confirmed. Do not obtain broad admin tokens or modify Gitea SQL to bypass this prerequisite.

## Deferred device acceptance

Actual GL.iNet workers, native server/channel/protocol transitions, DNS/Kill Switch and IPv6 LAN witness, isolated inactive-provider startup and 24-48 hour flash/resource observation require a separate authorized physical test. Generic x86 refusal and synthetic cascades cannot certify them. Prepared virtual upgrade/crash/warm-boot results have their own scope in POST-ALPHA10-VIRTUAL-CHECKPOINT.md.
