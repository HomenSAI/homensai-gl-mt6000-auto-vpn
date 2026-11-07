# Restore the backup age identity from the password manager (or a scanned paper QR) into this PC's DPAPI store.
#   pwsh scripts/backupcrypt/import-age-identity.ps1     paste AGE-SECRET-KEY-1... when asked (input is hidden)
# Refused when the identity does not belong to a recipient of scripts/backupcrypt/recipients.txt (or the pinned copy).
# Guide: docs/architecture/AGE-TOFU-2026-11-04.ru.md.
param([switch]$Replace, [string]$Lab = '')
$ErrorActionPreference = 'Stop'
$arguments = @((Join-Path $PSScriptRoot 'agetool.py'), 'import')
if ($Replace) { $arguments += '--replace' }
if ($Lab) { $arguments += @('--lab', $Lab) }
& py -3.14 @arguments
exit $LASTEXITCODE
