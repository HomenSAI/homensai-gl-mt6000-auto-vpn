# Live speed graphs —25 October2026 / Текущая задача

Owner: when Test speed is pressed, graphs must update in real time with download/upload for both primary and reserve. The old chart joins completed historical averages and is not live.

Implement measured transfer progress (no simulated samples), bounded RAM storage, a lightweight read-only RPC and one-second UI updates. Show two primary/reserve panels with exact servers, direction, Mbps, phase and elapsed seconds. Tests remain sequential and quota-bound; waiting channel says waiting. Never invent zero values for errors/inactive/not-tested directions or mix jobs/profiles. Cancel/error/finished states explicit. Retain historical table and hide the old history chart under a clear closed disclosure.

Next: backend/transport/UI tests, canonical new alpha23/modules99/css71, exact dual-runtime CI, dedicated MT3000 normal backup/Stop/update/Start/reserve, actual bounded speed test/progress capture, GitHub/Gitea publication. Preserve operator settings/history and stable0.9.0. Baseline alpha22 complete. Private continuation: private/speed-live-alpha23-20261025. Native visual remains separate from automated/device proof.

Status: delivered in0.9.1-alpha23 on MT3000 and published GitHub/Gitea.55UI suites and778app/112QA tests each runtime passed. Actual two-VPN test produced6RPCframes/4RUNNINGframes with points; primary4download/2upload, reserve7download/3upload. Four prior results retained, six after test;8MiB/channel reserved. AutoONreserve, bothVPNhealthy. Native visual remains unverified. See ../VERIFICATION-ALPHA23-2026-10-25.md; final private receipt speed-live-alpha23-20261025/FINAL.json.
