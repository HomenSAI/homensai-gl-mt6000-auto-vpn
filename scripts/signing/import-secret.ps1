# Restore a release key secret from the password manager (or a scanned paper QR) into this PC's DPAPI store.
#   pwsh scripts/signing/import-secret.ps1 -Key main      paste HSAI-SK1:MAIN:... when asked (input is hidden)
# The line is refused when mistyped (checksum) or when it does not match a trusted public key of the repository.
# Guide: docs/architecture/SIGNING-2026-11-03.ru.md.
param([ValidateSet('main', 'reserve')][string]$Key = 'main', [switch]$Replace, [string]$Lab = '')
$ErrorActionPreference = 'Stop'
$arguments = @((Join-Path $PSScriptRoot 'keytool.py'), 'import', '--key', $Key)
if ($Replace) { $arguments += '--replace' }
if ($Lab) { $arguments += @('--lab', $Lab) }
& py -3.14 @arguments
exit $LASTEXITCODE
