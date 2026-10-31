# HomenSAI licensing guide

**Current source-distribution policy (31 October 2026):** [HomenSAI Personal & Commercial Source License v1.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSE). This is a **proprietary source-available license, not open source**.

## What is permitted under the new license?

- A natural person may run the unmodified application free of charge for private, non-commercial use on their own/household network, retaining the author notices.
- Businesses, freelancers performing professional work, employers, associations, institutions and other organizations need a **separate paid written license**, even for internal use.
- Modifying, publishing a modified build, reselling, redistributing, embedding the code, or operating a hosted service requires the copyright holder's **advance written permission**. Paying for commercial use alone does not grant these rights.
- The attribution shown in the program and related documentation must remain intact: **Serhii Khomenko / HomenS.AI — https://homensai.com**.
- A normal personal backup and documented application configuration are allowed. Mandatory statutory rights are unaffected.

Contact **info@homensai.com** for commercial terms and any modification, redistribution or integration agreement. There is no published automatic price or checkout.

## Previously MIT-licensed versions are not revoked

Before this transition, original project code and documentation were explicitly offered under MIT, with an additional project-specific MIT grant for embedded HomenS.AI-owned style/logo/robot assets. Recipients of those earlier copies can continue to exercise their previously granted MIT rights, including commercial use, modification and redistribution subject to MIT notice requirements. The [original MIT text](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSE-MIT-LEGACY) is preserved. Published tags/assets/old packages and git history are not retroactively relicensed. Merely changing the root LICENSE cannot prevent reuse of code legitimately obtained under MIT.

The new terms govern distributions made under the new license and newly copyrighted revisions licensed under it, subject to independently existing MIT rights and other earlier permissions. Check the license accompanying the **exact version** used. The separate upstream HomenSAI Style repository is not relicensed by this file.

## Embedded files and third-party components

- The included style directory carries its own [style LICENSE](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/router/files/www/luci-static/resources/view/homensai-vpn/style/LICENSE). Earlier project-specific MIT grants described above remain valid for the corresponding old materials; independent upstream rights are not changed.
- IBM Plex font binaries retain **SIL Open Font License 1.1** and their `OFL.txt` and `NOTICE.txt` in `router/files/www/luci-static/resources/view/homensai-vpn/style/fonts/ibm-plex/`.
- OpenWrt, LuCI, Python, Lua, and system dependencies retain their respective licenses. No GL.iNet firmware is relicensed or included.
- Any additional contributed/third-party files remain subject to their own notices; confirm rights before applying stricter terms to those files.

## Package and first-run terms

Future builds should include this license under `/usr/share/licenses/homensai-auto-vpn/` and the legacy MIT notice alongside it. The first-run experimental/operational terms are in [DISCLAIMER.md](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/DISCLAIMER.md) / [DISCLAIMER.ru.md](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/DISCLAIMER.ru.md); operational acceptance is not a substitute for a commercial license.

**Deployment status:** changing repository files does not update an already installed router or an already published IPK. A newly versioned package/UI build, regeneration, CI, and router-side acceptance verification remain separate steps. See [transition checklist](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/LICENSING-TRANSITION-2026-10-31.md).
