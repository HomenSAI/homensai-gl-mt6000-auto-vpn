<#
 Builds the local docker image homensai-tlc:local used by the OPTIONAL TLA+ cross-check of the offline CI
 (tools/formal/tla/tlc_check.py, run by scripts/offline-ci.ps1). Run it once per machine; without the image the check
 reports SKIPPED. The jar (TLA+ Tools 1.7.4) is not stored in git: give it with -JarPath, let the script find a copy under
 the main checkout (private/math/formal-tlc/tools or private/tools), or pass -Download to fetch the official release once.
 The jar is verified against tools/formal/tla/TLA2TOOLS.sha256 here and again inside the docker build.
#>
[CmdletBinding()]
param([string]$JarPath='', [switch]$Download, [string]$Tag='homensai-tlc:local')
$ErrorActionPreference='Stop'
$repoPath=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$gitExe='C:\Program Files\Git\cmd\git.exe'
$tlaDir=Join-Path $repoPath 'tools/formal/tla'
function Assert-Exit([string]$Operation){if($LASTEXITCODE -ne 0){throw "$Operation failed (exit $LASTEXITCODE)."}}
$expected=([regex]::Match((Get-Content -LiteralPath (Join-Path $tlaDir 'TLA2TOOLS.sha256') -Raw),'\b[0-9a-f]{64}\b')).Value
if(-not $expected){throw 'TLA2TOOLS.sha256 holds no sha256'}
$work=Join-Path ([IO.Path]::GetTempPath()) ('homensai-tlc-build-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $work | Out-Null
try{
    $jar=Join-Path $work 'tla2tools.jar'
    if($JarPath){Copy-Item -LiteralPath $JarPath -Destination $jar}
    else{
        $common=(& $gitExe -C $repoPath rev-parse --git-common-dir).Trim();Assert-Exit 'git common dir'
        if(-not [IO.Path]::IsPathRooted($common)){$common=Join-Path $repoPath $common}
        $mainRoot=Split-Path -Parent (Resolve-Path -LiteralPath $common).Path
        $found=@('private/math/formal-tlc/tools/tla2tools.jar','private/tools/tla2tools.jar')|ForEach-Object{Join-Path $mainRoot $_}|Where-Object{Test-Path -LiteralPath $_}|Select-Object -First 1
        if($found){Copy-Item -LiteralPath $found -Destination $jar}
        elseif($Download){Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar' -OutFile $jar}
        else{throw 'tla2tools.jar not found: pass -JarPath <file> or -Download (official v1.7.4 release)'}
    }
    $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $jar).Hash.ToLowerInvariant()
    if($actual -ne $expected){throw "tla2tools.jar sha256 $actual does not match the pinned $expected. Nothing was built."}
    Copy-Item -LiteralPath (Join-Path $tlaDir 'Dockerfile') -Destination (Join-Path $work 'Dockerfile')
    & docker build --build-arg "JAR_SHA256=$expected" -t $Tag $work;Assert-Exit 'docker build'
    $label=(& docker image inspect $Tag --format '{{index .Config.Labels "org.homensai.tla2tools.sha256"}}').Trim();Assert-Exit 'image inspect'
    if($label -ne $expected){throw 'built image carries the wrong jar label'}
    [PSCustomObject]@{Image=$Tag;JarSHA256=$expected;ImageId=(& docker image inspect $Tag --format '{{.Id}}')}
}finally{Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue}
