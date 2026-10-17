[CmdletBinding()]
param([string[]]$Tags = @())
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gitExe = 'C:\Program Files\Git\cmd\git.exe'
function Assert-Exit([string]$Action) { if ($LASTEXITCODE -ne 0) { throw "$Action failed. Local commits are preserved; no force update was attempted." } }
$branchName = (& $gitExe -C $repoPath branch --show-current).Trim(); Assert-Exit 'Read branch'
if ($branchName -notmatch '^(feature|fix|hotfix|backup)/[A-Za-z0-9._/-]+$') { throw 'Save a reviewed feature/fix/hotfix/backup branch; direct main publication is refused.' }
& $gitExe check-ref-format "refs/heads/$branchName"; Assert-Exit 'Validate branch'
$dirty = & $gitExe -C $repoPath status --porcelain
if ($dirty) { throw 'Commit or checkpoint the working changes first; this command saves committed, clean work only.' }
$headSha = (& $gitExe -C $repoPath rev-parse HEAD).Trim(); Assert-Exit 'Read HEAD'
foreach ($tagName in $Tags) { if ($tagName -notmatch '^v[0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|beta)[0-9]+)?$') { throw 'Unsupported release tag name' }; & $gitExe -C $repoPath show-ref --verify --quiet "refs/tags/$tagName"; Assert-Exit 'Verify local tag' }
$commonGit = (& $gitExe -C $repoPath rev-parse --git-common-dir).Trim(); Assert-Exit 'Read common Git directory'
if (-not [IO.Path]::IsPathRooted($commonGit)) { $commonGit = Join-Path $repoPath $commonGit }
$privateDir = Join-Path $commonGit 'handoff'
New-Item -ItemType Directory -Force -Path $privateDir | Out-Null
$transferName = 'source-' + [Guid]::NewGuid().ToString('N') + '.bundle'
$bundlePath = Join-Path $privateDir $transferName
$refs = @("refs/heads/$branchName") + @($Tags | ForEach-Object { "refs/tags/$_" })
& $gitExe -C $repoPath bundle create $bundlePath @refs; Assert-Exit 'Create source bundle'
$bundleHead = & $gitExe -C $repoPath bundle list-heads $bundlePath "refs/heads/$branchName"; Assert-Exit 'Verify bundle branch'
if (($bundleHead -split '\s+')[0] -ne $headSha) { throw 'Branch changed during export. Nothing was published.' }
& docker cp $bundlePath "local-codex:/tmp/$transferName"; Assert-Exit 'Transfer committed objects'
$refspecs = @("refs/heads/${branchName}:refs/heads/${branchName}") + @($Tags | ForEach-Object { "refs/tags/${_}:refs/tags/${_}" })
& docker exec -u node -w /workspace/gl-mt6000-alta-vpn local-codex git -c gc.auto=0 -c maintenance.auto=false fetch --no-tags "/tmp/$transferName" @refspecs; Assert-Exit 'Import without force'
$reply = & docker exec -u node -w /workspace/gl-mt6000-gitflow local-codex python3 tools/gitflow.py save --branch $branchName; Assert-Exit 'Save primary Gitea'
$receipt = ($reply -join "`n") | ConvertFrom-Json
if ($receipt.result -ne 'SAVED' -or $receipt.head -ne $headSha) { throw 'Primary branch SHA not confirmed. Inspect the retained bundle and receipt.' }
foreach ($tagName in $Tags) {
    & docker exec -u node -w /workspace/gl-mt6000-alta-vpn local-codex git push origin "refs/tags/$tagName"; Assert-Exit 'Save immutable primary tag'
    $wanted = (& $gitExe -C $repoPath rev-parse "refs/tags/$tagName").Trim()
    $remoteTag = & docker exec -u node -w /workspace/gl-mt6000-alta-vpn local-codex git ls-remote --tags origin "refs/tags/$tagName"; Assert-Exit 'Verify primary tag'
    if (($remoteTag -split '\s+')[0] -ne $wanted) { throw 'Primary tag object mismatch' }
}
[PSCustomObject]@{Result='SAVED';Primary='Gitea';Branch=$branchName;Head=$headSha;GitHubPublished=$false;PrivateBundle=$bundlePath}
