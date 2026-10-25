# Execute the real helper with mocked Windows routing. No network/router/password calls.
$ErrorActionPreference='Stop'
$taskHelperPath=Join-Path $PSScriptRoot '../router/files/www/luci-static/resources/view/homensai-vpn/client-test.ps1'
$global:DocAuditControlInterface=14
$global:DocAuditHttpCalls=0
$global:DocAuditPasswordPrompts=0
function Get-NetAdapter {param([switch]$IncludeHidden) [pscustomobject]@{InterfaceIndex=3;Status='Up'}}
function Get-NetIPAddress {param($InterfaceIndex,$AddressFamily) [pscustomobject]@{InterfaceIndex=3;AddressState='Preferred';IPAddress='192.168.8.2'}}
function Find-NetRoute {
 param($InterfaceIndex,$LocalIPAddress,$RemoteIPAddress)
 if($InterfaceIndex){$chosen=$InterfaceIndex}else{$chosen=$global:DocAuditControlInterface}
 [pscustomobject]@{InterfaceIndex=$chosen;NextHop=$(if($RemoteIPAddress -eq '192.168.8.1'){'0.0.0.0'}else{'192.168.8.1'})}
}
function Read-Host {$global:DocAuditPasswordPrompts++;throw 'UNEXPECTED-PASSWORD-PROMPT'}
function Invoke-RestMethod {$global:DocAuditHttpCalls++;throw 'UNEXPECTED-HTTP'}
$output=@(& $taskHelperPath -Router 'http://192.168.8.1:8080/' -CableInterface 3 -CheckOnly)
if($LASTEXITCODE -ne 2 -or ($output -join ' ') -notmatch 'CLIENT-CONTROL-PATH-MISMATCH'){throw 'CONTROL-MISMATCH-NOT-REFUSED'}
if($global:DocAuditHttpCalls -or $global:DocAuditPasswordPrompts){throw 'SECRET-OR-HTTP-BEFORE-REFUSAL'}
$global:DocAuditControlInterface=3
$output=@(& $taskHelperPath -Router 'http://192.168.8.1:8080/' -CableInterface 3 -CheckOnly)
if($LASTEXITCODE -ne 0 -or ($output -join ' ') -notmatch 'prerequisites verified'){throw 'VALID-CONTROL-PATH-REFUSED'}
if($global:DocAuditHttpCalls -or $global:DocAuditPasswordPrompts){throw 'CHECKONLY-CHANGED-SCOPE'}
Write-Output 'PASS: same-IP wrong-interface control refused before credentials/HTTP; matching cable CheckOnly accepted; no OS/network changes.'
