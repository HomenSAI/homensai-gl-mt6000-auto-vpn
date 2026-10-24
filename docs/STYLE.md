<!-- doc-role: current -->
# HomenS.AI Style integration

Pinned upstream style source: HomenSAI Style v1.14.3. This is a LuCI application adapter with selected local CSS, brand renderer, original robot and IBM Plex fonts; not a new standalone website and not an imported private repository history. No runtime CDN is needed for these assets.

The current generator is `python router/build_sidebar_ui.py`, normally called during the reviewed version-bump flow. Older localize/integrate scripts are predecessor build stages, not a replacement for the final current generator. Preserve pinned vendor bytes; package text outside the pinned style directory is normalized to LF. The actual selected module/CSS is in VERSION.json.

The project-specific permission in [LICENSING.md](../LICENSING.md) grants MIT use of the HomenS.AI-owned style/logo/robot files included in this project. The preserved upstream `style/LICENSE` does not by itself describe that supplementary project grant and does not relicense other upstream versions/repositories. IBM Plex retains SIL OFL1.1 and NOTICE. Keep all required notices. This paragraph summarizes the existing grant; it does not change legal texts.

Animations use reduced-motion support. Main/reserve route badges distinguish selection from connection failure; chart series have separate color semantics. [Display contract](OVERVIEW-PATH-COLOURS.md).
