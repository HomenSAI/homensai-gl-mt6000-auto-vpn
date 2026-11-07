[CmdletBinding()]
param([string]$Image='homensai-vpn-python311:local',
      [string]$RuntimeImage='homensai-vpn-python39:local', [switch]$InjectFailure, [string]$SourceCommit='',
      [string]$TlcImage='homensai-tlc:local', [switch]$SkipTlc, [switch]$TraceCheck)
$ErrorActionPreference='Stop'
$repoPath=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gitExe='C:\Program Files\Git\cmd\git.exe'
function Assert-Exit([string]$Operation){if($LASTEXITCODE -ne 0){throw "$Operation failed (exit $LASTEXITCODE). No successful CI receipt is issued."}}
$dirty=& $gitExe -C $repoPath status --porcelain;Assert-Exit 'Status'
if($dirty -and -not $SourceCommit){throw 'Commit the reviewed snapshot first. CI never tests a mixed working tree.'}
$requestedSource=if($SourceCommit){$SourceCommit}else{'HEAD'}
if($SourceCommit -and $SourceCommit -notmatch '^[a-f0-9]{40}$'){throw 'Explicit source must be a full commit SHA'}
$sourceSha=(& $gitExe -C $repoPath rev-parse "$requestedSource`^{commit}").Trim();Assert-Exit 'Source SHA'
if($sourceSha -notmatch '^[a-f0-9]{40}$'){throw 'Invalid source SHA'}
$commonGit=(& $gitExe -C $repoPath rev-parse --git-common-dir).Trim();Assert-Exit 'Private directory'
if(-not [IO.Path]::IsPathRooted($commonGit)){$commonGit=Join-Path $repoPath $commonGit}
$privateDir=Join-Path $commonGit 'handoff';New-Item -ItemType Directory -Force -Path $privateDir | Out-Null
$runId=[Guid]::NewGuid().ToString('N')
$archivePath=Join-Path $privateDir "ci-$sourceSha-$runId.tar"
$manifestPath=Join-Path $privateDir "ci-$sourceSha-$runId.manifest.json"
$entries=& $gitExe -C $repoPath ls-tree -r $sourceSha;Assert-Exit 'Tree entries'
if(@($entries|Where-Object {$_ -notmatch '^100(?:644|755) blob [a-f0-9]{40}\t'}).Count){throw 'CI refuses symlink/submodule tree entries'}
$names=@(& $gitExe -C $repoPath -c core.quotepath=false ls-tree -r --name-only $sourceSha);Assert-Exit 'Manifest'
if(@($names|Where-Object {$_ -match '[\r\n\x00]' -or $_ -match '^"'}).Count){throw 'CI manifest contains unsupported path encoding'}
[IO.File]::WriteAllText($manifestPath,(ConvertTo-Json -InputObject $names -Compress),(New-Object System.Text.UTF8Encoding($false)))
& $gitExe -C $repoPath archive --format=tar --output=$archivePath $sourceSha;Assert-Exit 'Immutable source archive'
# OPTIONAL check, run on the host (it needs docker for TLC, the isolated CI containers have none): TLC on tools/formal/tla against
# tools/formal/model.py for every profile of ci_check.py (tools/formal/tla/README.md; limit 1500 s inside tlc_check.py). A missing
# image or docker is SKIPPED, not failed; a difference is red. The result is mounted into the containers and lands in the receipt.
$tlcResultPath=Join-Path $privateDir "ci-$sourceSha-$runId.tlc.json"
$tlcSource=Join-Path ([IO.Path]::GetTempPath()) "homensai-tlc-ci-$runId"
function Write-TlcSkipped([string]$Reason){
    [IO.File]::WriteAllText($tlcResultPath,(ConvertTo-Json -InputObject ([ordered]@{status='SKIPPED';reason=$Reason;seconds=0;configs=@{};problems=@()}) -Depth 4),(New-Object System.Text.UTF8Encoding($false)))
}
if($SkipTlc){Write-TlcSkipped '-SkipTlc was given'}
else{
    $hostPython=@('python','python3')|ForEach-Object{Get-Command $_ -CommandType Application -ErrorAction SilentlyContinue}|Select-Object -First 1
    if(-not $hostPython){Write-TlcSkipped 'python was not found on the host'}
    else{
        New-Item -ItemType Directory -Force -Path $tlcSource | Out-Null
        try{
            $tlcZip="$tlcSource.zip"
            & $gitExe -C $repoPath archive --format=zip --output=$tlcZip $sourceSha tools/formal;Assert-Exit 'TLC source archive'
            Expand-Archive -LiteralPath $tlcZip -DestinationPath $tlcSource -Force
            & $hostPython.Source -I (Join-Path $tlcSource 'tools/formal/tla/tlc_check.py') --source $tlcSource --image $TlcImage --py-image $Image --timeout 1500 --result $tlcResultPath | Write-Host
            if($LASTEXITCODE -ne 0){throw "TLC cross-check failed (exit $LASTEXITCODE): Supervisor.tla and tools/formal/model.py disagree or the check could not run. See the lines above; the source archive is kept as evidence."}
        }finally{Remove-Item -LiteralPath $tlcSource,"$tlcSource.zip" -Recurse -Force -ErrorAction SilentlyContinue}
    }
}
$tlcResult=Get-Content -LiteralPath $tlcResultPath -Raw|ConvertFrom-Json
$receipts=@()
foreach($targetImage in @($Image,$RuntimeImage)){
    $imageId=(& docker image inspect $targetImage --format '{{.Id}}').Trim();Assert-Exit 'Local image availability'
    $runtimeOnly=if($targetImage -eq $RuntimeImage){' --runtime-only'}else{''}
    if($TraceCheck){$runtimeOnly+=' --trace-check'}  # optional: code-to-model trace conformance (tools/formal/trace_check.py)
    $command="set -eu; tar --no-same-owner --no-same-permissions -xf /input/source.tar -C /work; python3 qa/run_offline_ci.py --manifest /input/manifest.json --source $sourceSha --tlc-result /input/tlc.json$runtimeOnly"
    if($InjectFailure){$command='exit 17'}
    $dockerArgs=@('run','--rm','--pull=never','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user=65534:65534','--pids-limit=128','--memory=1g','--cpus=2',
      '--mount',"type=bind,source=$archivePath,target=/input/source.tar,readonly",'--mount',"type=bind,source=$manifestPath,target=/input/manifest.json,readonly",'--mount',"type=bind,source=$tlcResultPath,target=/input/tlc.json,readonly",
      '--tmpfs','/work:rw,nosuid,nodev,size=448m,mode=1777','--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777',
      '--workdir','/work','--env','PYTHONDONTWRITEBYTECODE=1','--entrypoint','sh',$targetImage,'-c',$command)
    $output=& docker @dockerArgs;Assert-Exit 'Isolated checks'
    $lines=@($output|Where-Object {$_ -like 'CI-RECEIPT *'})
    if($lines.Count -ne 1){throw 'Missing or ambiguous CI receipt'}
    $receipt=$lines[0].Substring(11)|ConvertFrom-Json
    if($receipt.result -ne 'PASS' -or $receipt.source -ne $sourceSha){throw 'CI source/result mismatch'}
    $receipt|Add-Member -NotePropertyName image -NotePropertyValue $targetImage
    $receipt|Add-Member -NotePropertyName image_id -NotePropertyValue $imageId
    $receipts+= $receipt
}
if($receipts[0].sha256 -ne $receipts[1].sha256){throw 'Package bytes differ between runtime matrices'}
$receiptPath=Join-Path $privateDir "ci-$sourceSha-$runId.receipt.json"
[IO.File]::WriteAllText($receiptPath,(ConvertTo-Json -InputObject $receipts -Depth 5),(New-Object System.Text.UTF8Encoding($false)))
# The archive is recreatable from the commit; after PASS only the receipt and manifest stay. A failed run keeps it as evidence.
Remove-Item -LiteralPath $archivePath -Force
[PSCustomObject]@{Result='PASS';Source=$sourceSha;PackageSHA256=$receipts[0].sha256;Receipt=$receiptPath;TlcCrosscheck=$tlcResult.status;RouterAccess=$false}
