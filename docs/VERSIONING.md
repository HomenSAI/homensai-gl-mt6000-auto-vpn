# Version and release identity — 24 October2026

Текущая разработка / Current development: **0.9.1-alpha11**, package **0.9.1-alpha11-1**, selected **dashboard87/ui59.css**. Public stable release remains **0.9.0**. Last verified dedicated physical baseline isalpha9; VM report coversalpha10. [RU guide](CURRENT-STATE.ru.md) · [EN guide](CURRENT-STATE.en.md).

VERSION.json, runtime, package builder, LuCI controller/menu and candidate test-kit must agree. The source fingerprint covers payload/generators with version strings neutralised. Use scripts/bump-version.py --check before a commit; a changed product needs a fresh prerelease identity. Build the canonical IPK from the exact reviewed Git tree in Linux and record its SHA256/size in VERSION.json and the matching kit. Match reproducible bytes across runtimes. Native UI content changes use a new immutable dashboard/CSS path to avoid serving old cached assets.

Documentation-only closure does not change the application version. Do not replace published stable tags/assets or edit installed version bytes in place. Release tags are separate from publishing a feature branch; a manifest release_tag is not proof that a GitHub/Gitea Release exists. Old handoff1.0.0 is documentation context, not application1.0.0.
