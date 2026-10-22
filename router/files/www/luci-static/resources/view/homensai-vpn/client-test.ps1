# HomenS.AI / Serhii Khomenko / https://homensai.com — MIT
# Run on an independently connected Windows LAN client. Secrets stay in memory.
param([uri]$Router='http://192.168.8.1:8080/',[DateTimeOffset]$Until=[DateTimeOffset]::Now.AddMinutes(10),[int]$CableInterface=0,[switch]$CheckOnly,[switch]$ProbeOnly,[switch]$SelfTest)
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
    if($CableInterface -gt 0) {
        $adapter=@(Get-NetAdapter -IncludeHidden|Where-Object {$_.InterfaceIndex -eq $CableInterface})
        if($adapter.Count -ne 1 -or $adapter[0].Status -ne 'Up'){throw 'CLIENT-CABLE-LINK-DOWN'}
        $local=@(Find-NetRoute -InterfaceIndex $CableInterface -LocalIPAddress $script:CableAddress -RemoteIPAddress $Router.Host|Where-Object {$null -ne $_.PSObject.Properties['NextHop']})
        if($local.Count -ne 1 -or $local[0].InterfaceIndex -ne $CableInterface -or $local[0].NextHop -ne '0.0.0.0'){throw 'CLIENT-CABLE-NOT-LOCAL'}
        foreach($destination in @('1.1.1.1','1.0.0.1')) {
            try {$route=@(Find-NetRoute -InterfaceIndex $CableInterface -LocalIPAddress $script:CableAddress -RemoteIPAddress $destination|Where-Object {$null -ne $_.PSObject.Properties['NextHop']})}catch{throw 'CLIENT-CABLE-PROBE-ROUTE-MISMATCH'}
            if($route.Count -ne 1 -or $route[0].InterfaceIndex -ne $CableInterface -or $route[0].NextHop -ne $Router.Host){throw 'CLIENT-CABLE-PROBE-ROUTE-MISMATCH'}
        }
        return
    }
    foreach($destination in @('1.1.1.1','8.8.8.8')) {
        $route=@(Find-NetRoute -RemoteIPAddress $destination|Where-Object {$null -ne $_.PSObject.Properties['NextHop']})
        if($route.Count -ne 1 -or $route[0].NextHop -ne $Router.Host){throw 'CLIENT-GATEWAY-MISMATCH'}
        $servers=@((Get-DnsClientServerAddress -InterfaceIndex $route[0].InterfaceIndex -AddressFamily IPv4).ServerAddresses)
        if($servers.Count -eq 0 -or @($servers|Where-Object {$_ -ne $Router.Host}).Count){throw 'CLIENT-DNS-CONFIG-UNVERIFIED'}
    }
    if(@(Get-NetRoute -DestinationPrefix '::/0' -ErrorAction SilentlyContinue|Where-Object {$_.State -ne 'Unreachable'}).Count){throw 'CLIENT-IPV6-DEFAULT-UNVERIFIED'}
}
# Source-bound IPv4 witness. These functions change no routes or adapters.
function Get-ClientBinding {
    Assert-LanPath
    $index=$CableInterface
    if($index -le 0){
        $route=@(Find-NetRoute -RemoteIPAddress '1.1.1.1'|Where-Object {$null -ne $_.PSObject.Properties['NextHop']})
        if($route.Count -ne 1 -or $route[0].NextHop -ne $Router.Host){throw 'CLIENT-GATEWAY-MISMATCH'}
        $index=$route[0].InterfaceIndex
    }
    $addresses=@(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4|Where-Object {$_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '169.254.*'})
    if($addresses.Count -ne 1){throw 'CLIENT-BOUND-ADDRESS-AMBIGUOUS'}
    if($CableInterface -gt 0 -and $addresses[0].IPAddress -ne $script:CableAddress){throw 'CLIENT-BOUND-ADDRESS-CHANGED'}
    return @{Index=[int]$index;Address=[string]$addresses[0].IPAddress}
}
function Assert-ClientBinding($Expected,$Observed) {
    if($Expected.Index -le 0 -or $Observed.Index -ne $Expected.Index -or $Observed.Address -ne $Expected.Address){throw 'CLIENT-BOUND-INTERFACE-CHANGED'}
}
function New-DnsQuery([int]$Id) {
    if($Id -lt 0 -or $Id -gt 65535){throw 'CLIENT-DNS-ID'}
    $bytes=[Collections.Generic.List[byte]]::new()
    $bytes.AddRange([byte[]]@(($Id -shr 8),($Id -band 255),1,0,0,1,0,0,0,0,0,0))
    foreach($label in @('example','com')){$bytes.Add([byte]$label.Length);$bytes.AddRange([Text.Encoding]::ASCII.GetBytes($label))}
    $bytes.AddRange([byte[]]@(0,0,1,0,1))
    return ,$bytes.ToArray()
}
function Read-DnsNameEnd([byte[]]$Packet,[int]$Offset) {
    for($i=0;$i -lt 128;$i++){
        if($Offset -ge $Packet.Length){throw 'CLIENT-DNS-NAME'}
        $size=[int]$Packet[$Offset]
        if($size -eq 0){return ($Offset+1)}
        if(($size -band 192) -eq 192){
            if($Offset+1 -ge $Packet.Length){throw 'CLIENT-DNS-POINTER'}
            $pointer=(($size -band 63) -shl 8) -bor $Packet[$Offset+1]
            if($pointer -ge $Packet.Length){throw 'CLIENT-DNS-POINTER'}
            return ($Offset+2)
        }
        if(($size -band 192) -ne 0 -or $size -gt 63 -or $Offset+1+$size -gt $Packet.Length){throw 'CLIENT-DNS-NAME'}
        $Offset+=1+$size
    }
    throw 'CLIENT-DNS-NAME-LIMIT'
}
function Test-DnsReply([byte[]]$Reply,[byte[]]$Query) {
    if($Reply.Length -lt $Query.Length -or $Reply.Length -gt 4096 -or $Reply[0] -ne $Query[0] -or $Reply[1] -ne $Query[1]){throw 'CLIENT-DNS-REPLY'}
    $flags=([int]$Reply[2] -shl 8) -bor $Reply[3]
    if(($flags -band 32768) -eq 0 -or ($flags -band 30735) -ne 0 -or ($flags -band 512) -ne 0 -or $Reply[4] -ne 0 -or $Reply[5] -ne 1){throw 'CLIENT-DNS-FLAGS'}
    # Require the exact echoed question; never accept a reply to another query.
    for($i=12;$i -lt $Query.Length;$i++){if($Reply[$i] -ne $Query[$i]){throw 'CLIENT-DNS-QUESTION'}}
    $answers=([int]$Reply[6] -shl 8) -bor $Reply[7]
    if($answers -lt 1 -or $answers -gt 64){throw 'CLIENT-DNS-ANSWER-COUNT'}
    $offset=$Query.Length;$found=$false
    for($i=0;$i -lt $answers;$i++){
        $offset=Read-DnsNameEnd $Reply $offset
        if($offset+10 -gt $Reply.Length){throw 'CLIENT-DNS-ANSWER'}
        $type=([int]$Reply[$offset] -shl 8) -bor $Reply[$offset+1]
        $class=([int]$Reply[$offset+2] -shl 8) -bor $Reply[$offset+3]
        $size=([int]$Reply[$offset+8] -shl 8) -bor $Reply[$offset+9]
        $offset+=10
        if($offset+$size -gt $Reply.Length){throw 'CLIENT-DNS-RDATA'}
        if($type -eq 1 -and $class -eq 1 -and $size -eq 4){$found=$true}
        $offset+=$size
    }
    if(-not $found){throw 'CLIENT-DNS-NO-A'}
    return $true
}
function Test-BoundDns($Binding) {
    $random=[Security.Cryptography.RandomNumberGenerator]::GetBytes(2)
    $id=([int]$random[0] -shl 8) -bor $random[1]
    $query=New-DnsQuery $id
    $client=[Net.Sockets.UdpClient]::new([Net.Sockets.AddressFamily]::InterNetwork)
    try {
        if($IsWindows){$client.Client.SetSocketOption([Net.Sockets.SocketOptionLevel]::IP,[Net.Sockets.SocketOptionName]31,[Net.IPAddress]::HostToNetworkOrder([int]$Binding.Index))}
        $client.Client.Bind([Net.IPEndPoint]::new([Net.IPAddress]::Parse($Binding.Address),0))
        $client.Client.ReceiveTimeout=5000
        $server=[Net.IPEndPoint]::new([Net.IPAddress]::Parse($Router.Host),53)
        $null=$client.Send($query,$query.Length,$server)
        $sender=[Net.IPEndPoint]::new([Net.IPAddress]::Any,0)
        $reply=$client.Receive([ref]$sender)
        if($sender.Address.ToString() -ne $Router.Host -or $sender.Port -ne 53){throw 'CLIENT-DNS-SENDER'}
        return (Test-DnsReply $reply $query)
    } finally {$client.Dispose()}
}
function New-ClientConfirmation($Native,[double]$Now,[double]$ObservedAt,$Binding,$ObservedBinding,[string]$Exit,$Consumed,$DnsVerified,$HttpsVerified) {
    Assert-ClientBinding $Binding $ObservedBinding
    if($DnsVerified -isnot [bool] -or $HttpsVerified -isnot [bool] -or -not $DnsVerified -or -not $HttpsVerified){throw 'CLIENT-PROOF-UNVERIFIED'}
    if(-not [double]::IsFinite($Now) -or -not [double]::IsFinite($ObservedAt) -or $ObservedAt -gt $Now -or $Now-$ObservedAt -gt 30){throw 'CLIENT-PROOF-STALE'}
    if($Native.state -ne 'WAIT-CLIENT' -or $Native.tx -cnotmatch '^[a-f0-9]{32}$' -or $Consumed.Contains([string]$Native.tx) -or $Consumed.Count -ge 64){throw 'CLIENT-PROOF-TRANSACTION'}
    $time=[double]$Native.time;$deadline=[double]$Native.deadline
    if(-not [double]::IsFinite($time) -or -not [double]::IsFinite($deadline) -or $time -le 0 -or $time -gt $ObservedAt -or $Now-$time -gt 30 -or $Now -ge $deadline){throw 'CLIENT-PROOF-DEADLINE'}
    if($Exit -ne $Native.expected_exit){throw 'CLIENT-EXIT-MISMATCH'}
    $address=$null
    if(-not [Net.IPAddress]::TryParse($Exit,[ref]$address) -or $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw 'CLIENT-EXIT-IPV4'}
    return @{tx=$Native.tx;exit_ipv4=$Exit;dns_ok=$true;https_ok=$true}
}

function Initialize-BoundHttps {
    if('HomenSAIBoundIPv4' -as [type]){return}
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
public static class HomenSAIBoundIPv4 {
 public static async Task<string> Trace(int index, string source, string destination) {
  if(index<=0 || (destination!="1.1.1.1" && destination!="1.0.0.1")) throw new InvalidOperationException();
  using(var cancel=new CancellationTokenSource(TimeSpan.FromSeconds(10)))
  using(var handler=new SocketsHttpHandler { UseProxy=false, AllowAutoRedirect=false }) {
   handler.ConnectCallback=async (context, token) => {
    if(context.DnsEndPoint.Host!=destination || context.DnsEndPoint.Port!=443) throw new InvalidOperationException();
    var socket=new Socket(AddressFamily.InterNetwork,SocketType.Stream,ProtocolType.Tcp);
    try {
     if(OperatingSystem.IsWindows()) socket.SetSocketOption(SocketOptionLevel.IP,(SocketOptionName)31,IPAddress.HostToNetworkOrder(index));
     socket.Bind(new IPEndPoint(IPAddress.Parse(source),0));
     await socket.ConnectAsync(new IPEndPoint(IPAddress.Parse(destination),443),token).ConfigureAwait(false);
     if(((IPEndPoint)socket.LocalEndPoint).Address.ToString()!=source) throw new InvalidOperationException();
     return new NetworkStream(socket,true);
    } catch { socket.Dispose(); throw; }
   };
   using(var client=new HttpClient(handler) { Timeout=Timeout.InfiniteTimeSpan })
   using(var request=new HttpRequestMessage(HttpMethod.Get,"https://"+destination+"/cdn-cgi/trace")) {
    request.Version=HttpVersion.Version11;
    request.VersionPolicy=HttpVersionPolicy.RequestVersionExact;
    using(var response=await client.SendAsync(request,HttpCompletionOption.ResponseHeadersRead,cancel.Token).ConfigureAwait(false)) {
     response.EnsureSuccessStatusCode();
     using(var stream=await response.Content.ReadAsStreamAsync(cancel.Token).ConfigureAwait(false))
     using(var body=new MemoryStream()) {
      var buffer=new byte[4096];
      while(true) {
       int size=await stream.ReadAsync(buffer.AsMemory(),cancel.Token).ConfigureAwait(false);
       if(size==0) break;
       if(body.Length+size>32768) throw new InvalidOperationException();
       body.Write(buffer,0,size);
      }
      cancel.Token.ThrowIfCancellationRequested();
      return System.Text.Encoding.ASCII.GetString(body.ToArray());
     }
    }
   }
  }
 }
}
'@
}
function Test-ClientInternet {
    $binding=Get-ClientBinding
    $null=Test-BoundDns $binding
    Initialize-BoundHttps
    $exits=@()
    foreach($destination in @('1.1.1.1','1.0.0.1')) {
        try {$text=[HomenSAIBoundIPv4]::Trace([int]$binding.Index,$binding.Address,$destination).GetAwaiter().GetResult()}catch{throw 'CLIENT-CABLE-HTTPS-FAILED'}
        $exits+=Get-TraceIPv4 $text
    }
    Assert-ClientBinding $binding (Get-ClientBinding)
    if($exits[0] -ne $exits[1]){throw 'CLIENT-CABLE-EXIT-INCONSISTENT'}
    return $exits[0]
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

function Test-TransientNetworkError($Record) {
    return ($Record.Exception -is [System.ComponentModel.Win32Exception] -or
        $Record.Exception -is [System.Net.Http.HttpRequestException] -or
        $Record.Exception -is [System.TimeoutException] -or
        $Record.Exception -is [System.Threading.Tasks.TaskCanceledException] -or
        $Record.Exception.Message -in @('CLIENT-DNS-FAILED','CLIENT-CABLE-HTTPS-FAILED','CLIENT-HTTPS-FAILED','CLIENT-TRACE-FAILED'))
}

if($SelfTest) {
    Initialize-BoundHttps
    foreach($bad in @(@(0,'1.1.1.1'),@(3,'127.0.0.1'))){
        $rejected=$false
        try {$null=[HomenSAIBoundIPv4]::Trace([int]$bad[0],'192.168.8.2',[string]$bad[1]).GetAwaiter().GetResult()}catch{$rejected=$true}
        if(-not $rejected){throw 'SELFTEST-BOUND-HTTPS-SCOPE'}
    }
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
    $query=New-DnsQuery 1234
    $reply=[byte[]]($query+[byte[]]@(192,12,0,1,0,1,0,0,0,60,0,4,9,9,9,9))
    $reply[2]=129;$reply[3]=128;$reply[7]=1
    if(-not (Test-DnsReply $reply $query)){throw 'SELFTEST-DNS'}
    foreach($kind in @('id','question','rcode','truncated','no-answer','bad-pointer','rdata')){
        $bad=$reply.Clone()
        switch($kind){'id'{$bad[0]=0};'question'{$bad[13]=0};'rcode'{$bad[3]=131};'truncated'{$bad[2]=131};'no-answer'{$bad[7]=0};'bad-pointer'{$bad[$query.Length+1]=255};'rdata'{$bad[$query.Length+11]=255}}
        $rejected=$false;try {$null=Test-DnsReply $bad $query}catch{$rejected=$true}
        if(-not $rejected){throw 'SELFTEST-DNS-REJECT'}
    }
    $binding=@{Index=3;Address='192.168.8.2'};$seen=[Collections.Generic.HashSet[string]]::new()
    foreach($tx in @(('a'*32),('b'*32),('c'*32))){
        $native=@{state='WAIT-CLIENT';tx=$tx;time=100;deadline=125;expected_exit='9.9.9.9'}
        $proof=New-ClientConfirmation $native 102 101 $binding $binding '9.9.9.9' $seen $true $true
        if($proof.tx -ne $tx -or $proof.dns_ok -ne $true -or $proof.https_ok -ne $true){throw 'SELFTEST-PROOF'}
        $null=$seen.Add($tx)
        $rejected=$false;try {$null=New-ClientConfirmation $native 102 101 $binding $binding '9.9.9.9' $seen $true $true}catch{$rejected=$true}
        if(-not $rejected){throw 'SELFTEST-PROOF-REPLAY'}
    }
    foreach($kind in @('interface','address','exit','stale','future','deadline','state','dns','https','unknown-dns')){
        $native=@{state='WAIT-CLIENT';tx=('d'*32);time=100;deadline=125;expected_exit='9.9.9.9'}
        $observed=@{Index=3;Address='192.168.8.2'};$exit='9.9.9.9';$stamp=101;$now=102;$dns=$true;$https=$true
        switch($kind){'interface'{$observed.Index=4};'address'{$observed.Address='192.168.8.3'};'exit'{$exit='8.8.8.8'};'stale'{$now=140};'future'{$stamp=103};'deadline'{$native.deadline=102};'state'{$native.state='COMMITTED'};'dns'{$dns=$false};'https'{$https=$false};'unknown-dns'{$dns=1}}
        $rejected=$false;try {$null=New-ClientConfirmation $native $now $stamp $binding $observed $exit $seen $dns $https}catch{$rejected=$true}
        if(-not $rejected){throw 'SELFTEST-PROOF-REJECT'}
    }
    Write-Output 'PASS: input/DNS parsers, three sequential witnesses, replay/interface/exit/freshness/DNS/HTTPS refusals; no network calls or router changes.';exit 0
}

$script:Session=$null;$started=$false;$trialPassed=$false;$retainedReserve=$false;$stopRequested=$false
try {
    if($PSVersionTable.PSVersion.Major -lt 7){throw 'POWERSHELL-7-REQUIRED'}
    Assert-LocalRouter $Router
    if($CableInterface -gt 0) {
        $script:CableAddress=@(Get-NetIPAddress -InterfaceIndex $CableInterface -AddressFamily IPv4|Where-Object {$_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '169.254.*'})
        if($script:CableAddress.Count -ne 1){throw 'CLIENT-CABLE-ADDRESS-AMBIGUOUS'}
        $script:CableAddress=$script:CableAddress[0].IPAddress
    }
    Assert-LanPath
    if($CheckOnly){Write-Output 'Selected client path prerequisites verified; router unchanged. Cable mode preserves Wi-Fi default.';exit 0}
    if($ProbeOnly){$null=Test-ClientInternet;Write-Output 'PASS: physical LAN DNS and two bound HTTPS checks; no settings changed.';exit 0}
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
    Save-OwnSettings @{native_enabled='0';native_proof_scope='external-lan';native_trial=$trial;native_order_direction=$direction;native_baseline_exit=$baseline;native_until=$Until.ToString('o')}
    Start-Sleep -Seconds 6
    $status=Invoke-Router 'homensai-vpn' 'status' @{}
    if(@($status.native_failover.blockers).Count){throw 'NATIVE-PREFLIGHT-BLOCKED'}
    Write-Host 'A brief outage is possible. Original policy must be restored after the first trial.'
    if((Read-Host 'Type TEST to start') -cne 'TEST'){throw 'CLIENT-CANCELLED'}
    Save-OwnSettings @{native_enabled='0';native_trial=$trial;native_until=$Until.ToString('o');native_session_loss='1'}
    $revision=(Invoke-Router 'homensai-vpn' 'status' @{}).auto_control.control_revision
    $begin=Invoke-Router 'homensai-vpn' 'native_trial_start' @{control_revision=$revision;trial=$trial}
    if($begin.accepted -ne $true){throw 'CLIENT-TRIAL-START-REFUSED'}
    $started=$true;$lastTx=$null;$confirmedTx=[Collections.Generic.HashSet[string]]::new();$end=[DateTimeOffset]::UtcNow.AddSeconds(100)
    while([DateTimeOffset]::UtcNow -lt $Until -and [DateTimeOffset]::UtcNow -lt $end) {
        $status=Invoke-Router 'homensai-vpn' 'status' @{};$native=$status.native_failover
        if($native.state -eq 'WAIT-CLIENT' -and $native.tx -ne $lastTx) {
            $beforeBinding=Get-ClientBinding
            $probeStarted=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0
            $exit=Test-ClientInternet
            $afterBinding=Get-ClientBinding
            $now=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0
            $proof=New-ClientConfirmation $native $now $probeStarted $beforeBinding $afterBinding $exit $confirmedTx $true $true
            # Re-read pending identity after probing; the typed RPC checks it again.
            $latest=(Invoke-Router 'homensai-vpn' 'status' @{}).native_failover
            if($latest.state -ne 'WAIT-CLIENT' -or $latest.tx -ne $native.tx -or $latest.expected_exit -ne $native.expected_exit){throw 'CLIENT-TRANSACTION-CHANGED'}
            # The private trial number is known only to the helper that started this trial and to root on the router.
            $proof['trial']=$trial
            $accepted=Invoke-Router 'homensai-vpn' 'native_confirm' $proof
            if($accepted.accepted -ne $true){throw 'CLIENT-CONFIRM-NOT-ACCEPTED'}
            $null=$confirmedTx.Add([string]$native.tx)
            $lastTx=$native.tx
        }
        if($native.state -eq 'ARMED' -and $native.reason -eq 'TRIAL-PASSED') {
            $restored=Test-ClientInternet
            if($restored -ne $baseline){throw 'CLIENT-RESTORE-MISMATCH'}
            if(-not $trialPassed){Write-Output 'Trial passed and original client path restored. Continue client monitoring until the deadline.'}
            $trialPassed=$true
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
        try {$status=Invoke-Router 'homensai-vpn' 'status' @{};$native=$status.native_failover} catch {
            if(-not (Test-TransientNetworkError $_)){throw}
            Start-Sleep -Seconds 2;continue
        }
        if($native.state -eq 'STOPPED-ON-RESERVE') {
            if((Test-ClientInternet) -ne $native.expected_exit){throw 'CLIENT-RESERVE-NOT-VERIFIED'}
            Write-Output 'Stopped with verified reserve retained; original source not restored.';$verifiedStop=$true;$retainedReserve=$true;break
        }
        if($native.state -in @('STOPPED','EXPIRED','ROLLED-BACK')) {
            try {$restored=Test-ClientInternet} catch {
                if(-not (Test-TransientNetworkError $_)){throw}
                Start-Sleep -Seconds 2;continue
            }
            if($restored -ne $baseline){throw 'CLIENT-RESTORE-MISMATCH'}
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
