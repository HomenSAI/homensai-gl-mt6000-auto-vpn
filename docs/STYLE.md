# HomenS.AI Style integration

Pinned source: HomenSAI/homensai-style tag **v1.14.3**. The owner explicitly requested reuse of his logo, original TV robot and style core in this public router project. Only the selected CSS, brand renderer, robot and local fonts are embedded, not the private repository/history.

This is a **LuCI application adapter**, not a new standalone website. LuCI retains its own navigation/authentication/settings form. The adapter uses the existing Nordic tokens, IBM Plex, original robot and brand-generated footer without changing the private style core. Assets are local and versioned; no runtime CDN requests. Animation honours the original reduced-motion behaviour.

Regenerate application resources with `python3 router/localize_ui.py` then `python3 router/integrate_style.py`. The style files remain byte-identical to the pinned source. Font bytes are preserved by the ipk builder; text files are normalised to LF.

Embedded HomenS.AI Style material remains copyright Serhii Khomenko, all rights reserved; see the included `style/LICENSE`. The owner's instruction to embed his resources does not give third parties an open licence. Unmodified IBM Plex fonts retain SIL OFL 1.1, `OFL.txt` and `NOTICE.txt`. Public visibility is not an MIT/GPL grant.

Canonical repository naming: `homensai-<name>`. This project's exact name is **homensai-gl-mt6000-auto-vpn** in local Gitea and public GitHub. Develop/commit/tag locally before publishing the matching public snapshot.
