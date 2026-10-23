# Version and release identity

Current application0.9.0, package0.9.0-1, release tagv0.9.0. `VERSION.json`, runtime, package builder, LuCI controller/menu, selected dashboard/CSS and router-test-kit agree. A normal number does not remove experimental terms or prove unattended operation.

The source fingerprint covers router payload/generators with current version strings neutralized. Run `python scripts/bump-version.py --check` before committing; canonical IPK SHA256 is recorded after a reproducible build. Documentation-only changes do not create a new application version. Never edit installed version bytes in place or reuse a changed package under an already published tag.

For alpha/beta development the automatic bumper advances prerelease numbers. After a numbered release, choose the next development version explicitly (for example0.9.1-alpha1) and synchronize literals/generation/fingerprint before code changes. Never bump the immutable0.9.0 tag because documentation changed. Old review/handoff1.0.0 is documentation context, not application1.0.0.
