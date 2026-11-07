# Show the backup age identity ONCE for the password manager or a paper backup (owner only; asks for the authenticator code).
#   pwsh scripts/backupcrypt/reveal-age-identity.ps1             QR in this console (black on white) + the text line
#   pwsh scripts/backupcrypt/reveal-age-identity.ps1 -Qr html    printable page in %TEMP%, wiped after you press Enter
# Guide: docs/architecture/AGE-TOFU-2026-11-04.ru.md. Never paste the identity into chats, tickets or the repository.
param([ValidateSet('console', 'html', 'none')][string]$Qr = 'console', [string]$Lab = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$arguments = @((Join-Path $PSScriptRoot 'agetool.py'), 'reveal', '--qr', $Qr)
if ($Lab) { $arguments += @('--lab', $Lab) }
& py -3.14 @arguments
exit $LASTEXITCODE
