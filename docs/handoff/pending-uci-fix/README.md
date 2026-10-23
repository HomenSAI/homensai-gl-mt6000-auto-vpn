<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](../../CURRENT-STATUS.md) · [documentation index](../../DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Unverified UCI fix checkpoint

Paused by the user on 2026-10-16. These .draft files are NOT executable package inputs, NOT validated, NOT installed and NOT released. Some are unchanged reference/test scaffolding. Do not copy them blindly into production.

Reproduced in the isolated OpenWrt guest: an earlier saved, uncommitted UCI delta (interval=99) was committed by an unrelated setup_complete save. The request returned OK. See ../../../qa/alpha7-delta-probe.json.

Prepared correction: refuse nonempty pending UCI deltas without discarding them; propagate fixed refusal codes; refuse package lifecycle operations with pending own-config changes. Still required: adapt Lua test cursor get_savedir, test all callers, reproduce refusal against real libuci, regenerate hooks, full immutable-source CI and package acceptance. configuration_guard.py remains reference only; historical Stop acknowledgement handling still requires review.

Historical checkpoint only: the active correction was implemented and verified on 2026-10-16. See ../../UCI-FIX-RESULTS-2026-10-16.md and ../STATUS.md. These archived drafts remain outside package inputs; configuration_guard.py remains an unchanged reference, not a newly accepted change.

