# EXPERIMENTAL / BLOCKED

The helper candidate in this directory is **NOT APPROVED for physical application**.
It is an offline experiment, not a vendor fix or an approved recovery patch.

The exact stock `rtp2.sh` SHA256
`d6863630241e0bc68f56cc1eb8ccca45006083c1166e742e8500b28b5e2a544e`
removes `gl_vpn_rules` sections during each executed default include cycle,
recreates enabled VPN zones, and invokes the helper's `up` action. **If the
include also runs on subsequent reloads (`includeRunsOnReload=true`)**, the
candidate can observe another change each cycle and schedule an unending procd
reload sequence. The synthetic counterexample demonstrates that conditional
case, not the normal successful reload behavior of the observed router.

The observed router's `vpnclient` include has `reload=0`. The pinned FW3 source
skips that include on a normal successful reload; a missing runtime state can
instead cause fallback to start, which executes includes. The live include
metadata and successful runtime-state write must be verified before relying on
that distinction. This correction does not approve the experimental helper
patch or establish hardware acceptance. Per-helper idempotence alone is still
insufficient for a general convergence claim. FW3 applies compiled rules before
running includes, so silently dropping necessary reloads also lacks a general
policy-preservation proof.

The generator CLI refuses to generate a deployable candidate. Its pure candidate
function and transaction primitives remain available solely for counterexample
and isolated rollback tests. Earlier private candidate artifacts are superseded
and must not be applied. No full vendor helper source is bundled here.
