<!-- doc-role: current -->
# Validation procedure

[Current evidence](CURRENT-STATUS.md) · [Exact-source CI](CI-PRIMARY.md) · [Failure matrix](../router/tests/test_failure_matrix.py)

1. Review and commit one source snapshot. Version/fingerprint, selected LuCI module/CSS and artifact metadata must agree.
2. Run `scripts/offline-ci.ps1` against that commit. It tests isolated archives in pinned Python3.9/Lua and primary Python/Node environments. Complementary skips must be explicit. A changing worktree is not the tested source.
3. Use the package emitted by the pinned canonical environment and match both runtime hashes. Host Python3.15/zlib-ng can compress identical files differently; changing metadata to bless a different package is not verification.
4. Run relevant source/DOM, helper SelfTest and bounded synthetic-persona cases. Record fixture/source identities and retain failed/incomplete attempts. No model/fuzzer is a real LAN or hardware acceptance test.
5. In a marked disposable OpenWrt VM, check normal opkg install/update, actual files/modes/RPC/HTTP, typed UCI, negative cases, persistence and bounded cleanup. Keep real x86 identity; unsupported GL checks remain refused.
6. Physical work needs the named device, fresh verified private recovery, normal Stop/install/Start where authorized, and actual final channel/health/settings checks. Never promote older-version evidence or an ACK into acceptance.

Documentation audit: `python qa/audit_documentation.py`. Prompt equality, command contracts, scope classification, links and per-file hashes are part of the audit. [Verification meanings](VERIFICATION.md).
