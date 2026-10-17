[CmdletBinding()]
param([string]$Image = 'local-dev-tools:installed', [string]$CheckCommand = '')
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
& docker image inspect $Image --format '{{.Id}}'
if ($LASTEXITCODE -ne 0) { throw 'The approved local test image is unavailable. No image was downloaded.' }
$checks = 'set -eu; python3 -m unittest discover -s router/tests -q; python3 -m unittest discover -s qa -q; for test in router/tests/test_*ui*.js; do node "$test" || exit 1; done; python3 qa/privacy_audit.py'
if ($CheckCommand) { $checks = $CheckCommand }
$dockerArgs = @('run','--rm','--pull=never','--network','none','--mount',"type=bind,source=$repoPath,target=/work,readonly",'--workdir','/work','--env','PYTHONDONTWRITEBYTECODE=1','--env','GIT_CONFIG_COUNT=1','--env','GIT_CONFIG_KEY_0=safe.directory','--env','GIT_CONFIG_VALUE_0=/work','--entrypoint','sh',$Image,'-c',$checks)
& docker @dockerArgs
if ($LASTEXITCODE -ne 0) { throw "Local Linux checks failed with exit code $LASTEXITCODE. Review the output; no router was accessed." }
