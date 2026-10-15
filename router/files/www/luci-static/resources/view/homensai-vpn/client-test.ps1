# HomenS.AI / Serhii Khomenko / https://homensai.com — MIT
# Run on an independently connected Windows LAN client. Secrets stay in memory.
param([uri]$Router='http://192.168.8.1:8080/',[DateTimeOffset]$Until=[DateTimeOffset]::Now.AddMinutes(10),[switch]$CheckOnly,[switch]$SelfTest)
$ErrorActionPreference='Stop'

function Assert-LocalRouter([uri]$Value) {
    $address=$null
    if($Value.Scheme -notin @('http','https') -or $Value.UserInfo -or -not [Net.IPAddress]::TryParse($Value.Host,[ref]$address) -or $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw 'LOCAL-ROUTER-URL-REQUIRED'}
    $bytes=$address.GetAddressBytes()
    if(-not ($bytes[0] -eq 10 -or ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or ($bytes[0] -eq 192 -and $bytes[1] -eq 168))){throw 'PRIVATE-LAN-ROUTER-REQUIRED'}
}
function Get-TraceIPv4([string]$Text) {
    $line=@($Text -split "`n"|Where-Object {$_ -match '^ip='})
    if($line.Count -ne 1){throw 'TRACE-FORMAT'}
    $address=$null;$value=$line[0].Substring(3).Trim()
    if(-not [Net.IPAddress]::TryParse($value,[ref]$address) -or $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw 'TRACE-IPV4-REQUIRED'}
    return $address.ToString()
}
function Assert-LanPath {
    foreach($destination in @('1.1.1.1','8.8.8.8')) {
        $route=@(Find-NetRoute -RemoteIPAddress $destination|Where-Object {$null -ne $_.PSObject.Properties['NextHop']})
        if($route.Count -ne 1 -or $route[0].NextHop -ne $Router.Host){throw 'CLIENT-GATEWAY-MISMATCH'}
        $servers=@((Get-DnsClientServerAddress -InterfaceIndex $route[0].InterfaceIndex -AddressFamily IPv4).ServerAddresses)
        if($servers.Count -eq 0 -or @($servers|Where-Object {$_ -ne $Router.Host}).Count){throw 'CLIENT-DNS-CONFIG-UNVERIFIED'}
    }
    if(@(Get-NetRoute -DestinationPrefix '::/0' -ErrorAction SilentlyContinue|Where-Object {$_.State -ne 'Unreachable'}).Count){throw 'CLIENT-IPV6-DEFAULT-UNVERIFIED'}
}
function Test-ClientInternet {
    Assert-LanPath
    $answers=@(Resolve-DnsName example.com -Type A -Server $Router.Host -DnsOnly|Where-Object {$_.Type -eq 'A'})
    if($answers.Count -eq 0){throw 'CLIENT-DNS-FAILED'}
    $page=Invoke-WebRequest 'https://example.com/' -NoProxy -TimeoutSec 10
    if($page.StatusCode -ne 200){throw 'CLIENT-HTTPS-FAILED'}
    $trace=Invoke-WebRequest 'https://1.1.1.1/cdn-cgi/trace' -NoProxy -TimeoutSec 10
    if($trace.StatusCode -ne 200){throw 'CLIENT-TRACE-FAILED'}
    return Get-TraceIPv4 $trace.Content
}
function Invoke-Router([string]$Object,[string]$Method,[hashtable]$Arguments) {
    $body=@{jsonrpc='2.0';id=1;method='call';params=@($script:Session,$Object,$Method,$Arguments)}|ConvertTo-Json -Depth 10 -Compress
    $reply=Invoke-RestMethod $script:Api -Method Post -ContentType application/json -Body $body -NoProxy -MaximumRedirection 0 -TimeoutSec 15
    if($null -eq $reply.result -or $reply.result[0] -ne 0){throw 'ROUTER-RPC-FAILED'}
    if($reply.result.Count -gt 1){return $reply.result[1]}
}
function Save-OwnSettings([hashtable]$Values) {
    $null=Invoke-Router 'uci' 'set' @{config='homensai_vpn';section='main';values=$Values}
    $null=Invoke-Router 'uci' 'apply' @{rollback=$true;timeout=60}
    $null=Invoke-Router 'uci' 'confirm' @{}
}

if($SelfTest) {
    Assert-LocalRouter ([uri]'http://192.168.8.1:8080/')
    foreach($url in @('https://example.com/','http://user:password@192.168.8.1/','http://127.0.0.1/','http://8.8.8.8/')) {
        $rejected=$false;try {Assert-LocalRouter ([uri]$url)}catch{$rejected=$true}
        if(-not $rejected){throw 'SELFTEST-URL'}
    }
    if((Get-TraceIPv4 "ip=9.9.9.9`nhttp=http/1.1") -ne '9.9.9.9'){throw 'SELFTEST-TRACE'}
    foreach($text in @('none',"ip=9.9.9.9`nip=8.8.8.8",'ip=::1','ip=bad')) {
        $rejected=$false;try {$null=Get-TraceIPv4 $text}catch{$rejected=$true}
        if(-not $rejected){throw 'SELFTEST-TRACE-REJECT'}
    }
    Write-Output 'PASS: input validation; no network calls or router changes.';exit 0
}

$script:Session=$null;$started=$false;$trialPassed=$false;$retainedReserve=$false;$stopRequested=$false
try {
    if($PSVersionTable.PSVersion.Major -lt 7){throw 'POWERSHELL-7-REQUIRED'}
    Assert-LocalRouter $Router
    Assert-LanPath
    if($CheckOnly){Write-Output 'LAN gateway, DNS configuration and IPv6 prerequisites verified; no router changes.';exit 0}
    if($Until -le [DateTimeOffset]::Now -or $Until -gt [DateTimeOffset]::Now.AddHours(4)){throw 'BOUNDED-DEADLINE-REQUIRED'}
    $baseline=Test-ClientInternet
    $script:Api=([uri]::new($Router,'/ubus/')).AbsoluteUri
    $secure=Read-Host 'Router root password (private; never paste it into chat)' -AsSecureString
    $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        $body=@{jsonrpc='2.0';id=1;method='call';params=@('00000000000000000000000000000000','session','login',@{username='root';password=$plain;timeout=1200})}|ConvertTo-Json -Depth 8 -Compress
    } finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer);Remove-Variable plain,secure -ErrorAction SilentlyContinue}
    $reply=Invoke-RestMethod $script:Api -Method Post -ContentType application/json -Body $body -NoProxy -MaximumRedirection 0 -TimeoutSec 15
    Remove-Variable body -ErrorAction SilentlyContinue
    if($null -eq $reply.result -or $reply.result[0] -ne 0){throw 'ROUTER-LOGIN-FAILED'}
    $script:Session=$reply.result[1].ubus_rpc_session;Remove-Variable reply
    $inventory=Invoke-Router 'homensai-vpn' 'inventory' @{}
    if(-not $PSBoundParameters.ContainsKey('Until')){$Until=[DateTimeOffset]::Now.AddMinutes([int]$inventory.settings.native_duration)}
    $source=$inventory.settings.plan_source;$target=$inventory.settings.plan_target
    if(-not $source -or -not $target -or $source -eq $target){throw 'SELECT-SOURCE-RESERVE-IN-LUCI'}
    if($inventory.settings.native_session_loss -ne $true){throw 'ACCEPT-SESSION-LOSS-IN-LUCI'}
    $status=Invoke-Router 'homensai-vpn' 'status' @{}
    $a=@($inventory.native_candidates|Where-Object {$_.id -eq $source})
    $b=@($inventory.native_candidates|Where-Object {$_.id -eq $target})
    if($a.Count -ne 1 -or $b.Count -ne 1){throw 'PROFILES-NOT-ELIGIBLE-GENERIC-RULES'}
    $direction=if($a[0].order -lt $b[0].order){'first'}else{'last'}
    # Save only own metadata first; the controller stays disabled during preflight.
    $trial=[guid]::NewGuid().ToString('N')
    Save-OwnSettings @{native_enabled='0';native_trial=$trial;native_order_direction=$direction;native_baseline_exit=$baseline;native_until=$Until.ToString('o')}
    Start-Sleep -Seconds 6
    $status=Invoke-Router 'homensai-vpn' 'status' @{}
    if(@($status.native_failover.blockers).Count){throw 'NATIVE-PREFLIGHT-BLOCKED'}
    Write-Host 'A brief outage is possible. Original policy must be restored after the first trial.'
    if((Read-Host 'Type TEST to start') -cne 'TEST'){throw 'CLIENT-CANCELLED'}
    Save-OwnSettings @{native_enabled='1';native_trial=$trial;native_until=$Until.ToString('o');native_session_loss='1'}
    $started=$true;$lastTx=$null;$end=[DateTimeOffset]::UtcNow.AddSeconds(100)
    while([DateTimeOffset]::UtcNow -lt $Until -and [DateTimeOffset]::UtcNow -lt $end) {
        $status=Invoke-Router 'homensai-vpn' 'status' @{};$native=$status.native_failover
        if($native.state -eq 'WAIT-CLIENT' -and $native.tx -ne $lastTx) {
            $exit=Test-ClientInternet
            if($exit -ne $native.expected_exit){throw 'CLIENT-EXIT-MISMATCH'}
            $null=Invoke-Router 'homensai-vpn' 'native_confirm' @{tx=$native.tx;exit_ipv4=$exit;dns_ok=$true;https_ok=$true}
            $lastTx=$native.tx
        }
        if($native.state -eq 'ARMED' -and $native.reason -eq 'TRIAL-PASSED') {
            $restored=Test-ClientInternet
            if($restored -ne $baseline){throw 'CLIENT-RESTORE-MISMATCH'}
            $trialPassed=$true
            Write-Output 'Trial passed and original client path restored. Continue client monitoring until the deadline.'
            $end=$Until
        }
        if($native.state -eq 'STOPPED-ON-RESERVE') {
            $exit=Test-ClientInternet
            if($exit -ne $native.expected_exit){throw 'CLIENT-RESERVE-NOT-VERIFIED'}
            $retainedReserve=$true
            Write-Output 'Original source is not verified healthy. Trial halted; verified reserve retained. Original route was NOT restored.'
            break
        }
        if($native.state -in @('BLOCKED','STOPPED','ROLLED-BACK')){throw 'CONTROLLER-STOPPED-OR-BLOCKED'}
        Start-Sleep -Seconds 2
    }
    if(-not $trialPassed -and -not $retainedReserve){throw 'CLIENT-TRIAL-UNCONFIRMED'}
    $null=Invoke-Router 'homensai-vpn' 'native_stop' @{};$stopRequested=$true
    $stopDeadline=[DateTimeOffset]::UtcNow.AddSeconds(90);$verifiedStop=$false
    while([DateTimeOffset]::UtcNow -lt $stopDeadline) {
        $status=Invoke-Router 'homensai-vpn' 'status' @{};$native=$status.native_failover
        if($native.state -eq 'STOPPED-ON-RESERVE') {
            if((Test-ClientInternet) -ne $native.expected_exit){throw 'CLIENT-RESERVE-NOT-VERIFIED'}
            Write-Output 'Stopped with verified reserve retained; original source not restored.';$verifiedStop=$true;$retainedReserve=$true;break
        }
        if($native.state -in @('STOPPED','EXPIRED','ROLLED-BACK')) {
            if((Test-ClientInternet) -ne $baseline){throw 'CLIENT-RESTORE-MISMATCH'}
            Write-Output 'Stop and original client path restoration verified.';$verifiedStop=$true;break
        }
        if($native.state -eq 'BLOCKED'){throw 'STOP-RESTORE-UNVERIFIED'}
        Start-Sleep -Seconds 2
    }
    if(-not $verifiedStop){throw 'STOP-CONFIRMATION-TIMEOUT'}
    if($retainedReserve){exit 3}
} catch {
    # Deliberately do not print exception payloads, credentials, RPC session or exit IP.
    $code=if($_.Exception.Message -match '^[A-Z0-9_-]{1,96}$'){$_.Exception.Message}else{'CLIENT-CHECK-FAILED'}
    Write-Output ('Client verification failed: '+$code+'. Stop requested if a trial started.')
    if($started -and $script:Session -and -not $stopRequested){try {$null=Invoke-Router 'homensai-vpn' 'native_stop' @{};$stopRequested=$true}catch {Write-Output 'Stop request unavailable; independent router watchdog must roll back without confirmation.'}}
    exit 2
} finally {
    if($started -and $script:Session -and -not $stopRequested){try {$null=Invoke-Router 'homensai-vpn' 'native_stop' @{};$stopRequested=$true}catch {}}
    Remove-Variable Session,baseline,exit,body,reply,trial -Scope Script -ErrorAction SilentlyContinue
}
