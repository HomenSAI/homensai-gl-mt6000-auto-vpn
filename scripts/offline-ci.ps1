[CmdletBinding()]
param([string]$Image='local-dev-tools:installed',
      [string]$RuntimeImage='homensai-vpn-python39:local', [switch]$InjectFailure)
$ErrorActionPreference='Stop'
$repoPath=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gitExe='C:\Program Files\Git\cmd\git.exe'
function Assert-Exit([string]$Operation){if($LASTEXITCODE -ne 0){throw "$Operation failed (exit $LASTEXITCODE). No successful CI receipt is issued."}}
$dirty=& $gitExe -C $repoPath status --porcelain;Assert-Exit 'Status'
if($dirty){throw 'Commit the reviewed snapshot first. CI never tests a mixed working tree.'}
$sourceSha=(& $gitExe -C $repoPath rev-parse HEAD).Trim();Assert-Exit 'Source SHA'
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
$receipts=@()
foreach($targetImage in @($Image,$RuntimeImage)){
    $imageId=(& docker image inspect $targetImage --format '{{.Id}}').Trim();Assert-Exit 'Local image availability'
    $runtimeOnly=if($targetImage -eq $RuntimeImage){' --runtime-only'}else{''}
    $command="set -eu; tar --no-same-owner --no-same-permissions -xf /input/source.tar -C /work; python3 qa/run_offline_ci.py --manifest /input/manifest.json --source $sourceSha$runtimeOnly"
    if($InjectFailure){$command='exit 17'}
    $dockerArgs=@('run','--rm','--pull=never','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user=65534:65534','--pids-limit=128','--memory=512m','--cpus=2',
      '--mount',"type=bind,source=$archivePath,target=/input/source.tar,readonly",'--mount',"type=bind,source=$manifestPath,target=/input/manifest.json,readonly",
      '--tmpfs','/work:rw,nosuid,nodev,size=256m,mode=1777','--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777',
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
[PSCustomObject]@{Result='PASS';Source=$sourceSha;PackageSHA256=$receipts[0].sha256;Receipt=$receiptPath;RouterAccess=$false}
