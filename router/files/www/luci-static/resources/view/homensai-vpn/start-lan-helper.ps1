# HomenS.AI / Serhii Khomenko / https://homensai.com — MIT
# Friendly launcher for client-test.ps1. Run it on a Windows computer in your home network (not on the router):
#   pwsh -NoProfile -File .\start-lan-helper.ps1
# Both files must be in the same folder. This launcher only asks questions and starts client-test.ps1; it changes nothing itself.
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -lt 7){Write-Host 'PowerShell 7 is required. Install it with:  winget install Microsoft.PowerShell   then start this file with  pwsh' -ForegroundColor Red;exit 1}
$helper=@('client-test.ps1','homensai-vpn-client-test.ps1')|ForEach-Object {Join-Path $PSScriptRoot $_}|Where-Object {Test-Path -LiteralPath $_}|Select-Object -First 1
if(-not $helper){Write-Host 'The helper file (client-test.ps1 or homensai-vpn-client-test.ps1) must be in the same folder as this file.' -ForegroundColor Red;exit 1}
Write-Host ''
Write-Host 'HomenS.AI LAN helper' -ForegroundColor Cyan
Write-Host 'Checks, from this computer, that your internet works through the router and (optionally) confirms an automatic switch.'
Write-Host 'Use a computer connected to the router by a LAN cable if you can. Secrets stay in memory; nothing is saved.'
Write-Host ''
$router=Read-Host 'Router address [Enter = http://192.168.8.1:8080/]'
if([string]::IsNullOrWhiteSpace($router)){$router='http://192.168.8.1:8080/'}
Write-Host ''
Write-Host 'Network adapters that are up (the number is in the first column):'
Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object @{n='Number';e={$_.InterfaceIndex}},Name,InterfaceDescription,LinkSpeed | Format-Table -AutoSize | Out-Host
$cable=Read-Host 'Number of the CABLE adapter (Enter = this computer is on Wi-Fi, no cable)'
$extra=@()
if(-not [string]::IsNullOrWhiteSpace($cable)){
    if($cable -notmatch '^[0-9]{1,5}$'){Write-Host 'The number must be digits only.' -ForegroundColor Red;exit 1}
    $extra+=@('-CableInterface',$cable)
}
Write-Host ''
Write-Host '1  Check only (read-only, changes nothing)  <- start here'
Write-Host '2  Self-test of the helper (offline, changes nothing)'
Write-Host '3  Full trial (switches VPN for a few minutes; asks for the router password and the word TEST)'
$mode=Read-Host 'Choose 1, 2 or 3 [1]'
if([string]::IsNullOrWhiteSpace($mode)){$mode='1'}
switch($mode){
    '1'{$extra+=@('-CheckOnly')}
    '2'{$extra+=@('-SelfTest')}
    '3'{Write-Host 'Calls and downloads may be interrupted for a few seconds. Keep another way to reach the router.' -ForegroundColor Yellow}
    default{Write-Host 'Please choose 1, 2 or 3.' -ForegroundColor Red;exit 1}
}
Write-Host ''
& pwsh -NoProfile -File $helper -Router $router @extra
$code=$LASTEXITCODE
Write-Host ''
Write-Host ('The helper finished with code '+$code+'. If it printed a code in capital letters, look it up in the router page: Help -> The LAN helper fails.')
exit $code
