# Primary-Gitea CI preparation

`scripts/offline-ci.ps1` tests a **clean committed SHA**, never a changing checkout.
It exports a Git source archive and bounded file manifest into private `.git/handoff`.
Two preinstalled images check Python/UI/privacy/packaging and Python 3.9.15/Lua/CJSON.
Matching package SHA256 is mandatory. A failure issues no successful receipt.

Every test container has network disabled, a read-only root filesystem, UID 65534,
all capabilities dropped, no-new-privileges, 512 MiB / 2 CPU / 128 PID limits and
private bounded temporary filesystems. It receives only the source archive and
manifest. It never receives .git, user directories, keys, API tokens, Docker socket,
router access, host networking or host devices. Parent-side Docker access is only
for the reviewed local launcher; untrusted PR code must never run on that parent.

Local checks:

```powershell
.\scripts\offline-ci.ps1
.\scripts\offline-ci.ps1 -InjectFailure  # expected refusal, synthetic exit 17
```

The second command is a fail-propagation test, not a passing CI run. Receipts name
the exact source commit and artefact hash; retained source archives stay private.

NEXT-13 automatic activation remains BLOCKED until a dedicated restricted Gitea
runner and a reviewed trusted orchestration boundary are configured. No daemon,
runner-registration credential or commit/PR hook is created automatically here.
No repeating chat notifications are introduced.

Activation requirements: repository-scoped read-only checkout token; no production
secrets; trusted orchestration outside untrusted PR source; isolated ephemeral job
workspace; no host Docker socket inside job containers; pinned reviewed actions;
manual approval for untrusted/forked code; exact-SHA artefact validation. Configure
commit/PR triggers only after demonstrating a failing job blocks acceptance and a
passing job returns the same receipts as the local launcher. A matching SDK job
remains separately conditional on NEXT-10 provenance.
