# First-run setup

Owner request, 20 October 2026: a person opening the application must be able to choose the initial system parameters in one wizard. The choices are remembered; subsequent changes belong in Settings.

The first-run wizard follows the separate, explicit terms screen. It covers the application's supported preferences: interface language and appearance, monitoring and checkpoints, existing profile selection and monitoring metadata, bounded trial preferences, recovery thresholds, optional speed-test limits, and optional Telegram reporting. Router WAN/Wi-Fi configuration and VPN credentials remain on their existing router pages. The application's reporting timezone is Europe/Berlin.

The complete configuration and a dedicated onboarding schema marker are saved together in the application's own UCI configuration. The existing `setup_complete` flag only describes profile setup and must not be treated as proof that the entire first-run wizard was completed. Existing installations retain their current values when the wizard is first offered. A user without two installed profiles can defer the primary/reserve pair and finish the other preferences.

Saving requires a final review. A failed or unconfirmed save keeps the wizard available and does not claim completion. A blank Telegram token preserves an existing secret; tokens are not returned, shown on the review, or stored in browser persistence. Completing setup does not accept terms, start Auto, certify the router, or run a speed test. Later changes are available from Settings, including reopening the complete setup form. Emergency Stop remains independent of saving and navigation. An explicit dashboard link permits recovery actions while setup is incomplete; it consumes a one-entry URL flag, never sets the completion marker, and does not bypass the terms screen. A fresh entry offers the unfinished wizard again.

Validation evidence for the implementation is recorded in the current handoff. Synthetic browser tests and isolated UCI tests do not establish physical GL-MT3000 or vendor-adapter acceptance.
