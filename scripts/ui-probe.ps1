# Browser page probe gate (host side). The CI container has no browser, so this runs on the Windows host before publication.
# Offline: a loopback fixture server and a headless Microsoft Edge; no router, no network. One browser process; bounded current matrix.
[CmdletBinding()]
param([ValidateSet('gate','scen','legacy-gate')][string]$Mode = 'gate')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if (-not (Test-Path -LiteralPath $edge)) { throw 'Microsoft Edge not found; the page probe cannot run.' }
if ($Mode -eq 'gate') { & python (Join-Path $repo 'qa/ui-probe/current_gate.py') }
else { & python (Join-Path $repo 'qa/ui-probe/probe.py') $Mode }
if ($LASTEXITCODE -ne 0) { throw "Page probe $Mode failed. See the new result JSON in private/ui-probe/" }
