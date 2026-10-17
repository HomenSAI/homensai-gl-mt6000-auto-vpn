[CmdletBinding()]
param([ValidateRange(1,180)][int]$MaxMinutes=90)
$ErrorActionPreference='Stop'
$deadline=[DateTimeOffset]::UtcNow.AddMinutes($MaxMinutes)
$failures=0
while([DateTimeOffset]::UtcNow -lt $deadline){
    $lines=& docker exec homensai-vpn-qemu-alpha7 python3 /lab/protocol_ready_status.py
    if($LASTEXITCODE -ne 0){$failures++;Write-Output ('OBSERVATION-ERROR '+$failures);if($failures -ge 3){throw 'Repeated observation failure; no terminal result inferred.'};Start-Sleep -Seconds 30;continue}
    $failures=0;$row=($lines -join "`n")|ConvertFrom-Json
    Write-Output (([DateTimeOffset]::UtcNow.ToString('o'))+' SOAK '+($row|ConvertTo-Json -Compress -Depth 4))
    if($row.state -in @('PASS','FAIL','STOPPED')){if($row.state -ne 'PASS'){throw ('Producer terminal state '+$row.state)};exit 0}
    Start-Sleep -Seconds 60
}
throw 'Bounded observer ended before terminal evidence. Producer is not stopped or declared passed.'