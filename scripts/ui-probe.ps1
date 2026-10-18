# Browser page probe gate (host side). The CI container has no browser, so this runs on the Windows host before publication.
# Offline: a loopback fixture server and a headless Microsoft Edge; no router, no network. Takes about 3 minutes.
[CmdletBinding()]
param([ValidateSet('gate','scen')][string]$Mode = 'gate')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if (-not (Test-Path -LiteralPath $edge)) { throw 'Microsoft Edge not found; the page probe cannot run.' }
Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Where-Object { $_.CommandLine -match 'private\\ui-probe' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
& python (Join-Path $repo 'qa/ui-probe/probe.py') $Mode
if ($LASTEXITCODE -ne 0) { throw "Page probe $Mode failed. See private/ui-probe/result-$Mode.json" }
