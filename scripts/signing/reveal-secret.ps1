# Show a release key secret ONCE for the password manager or a paper backup (owner only; asks for the authenticator code or a recovery code).
#   pwsh scripts/signing/reveal-secret.ps1 -Key main            QR in this console (black on white) + the text line
#   pwsh scripts/signing/reveal-secret.ps1 -Key reserve -Qr html  printable page in %TEMP%, wiped after you press Enter
#   pwsh scripts/signing/reveal-secret.ps1 -Key main -Lab <dir>  the same on a test lab (test keys only)
# Guide: docs/architecture/SIGNING-2026-11-03.ru.md. Never paste the secret into chats, tickets or the repository.
param([ValidateSet('main', 'reserve')][string]$Key = 'main', [ValidateSet('console', 'html', 'none')][string]$Qr = 'console', [string]$Lab = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$arguments = @((Join-Path $PSScriptRoot 'keytool.py'), 'reveal', '--key', $Key, '--qr', $Qr)
if ($Lab) { $arguments += @('--lab', $Lab) }
& py -3.14 @arguments
exit $LASTEXITCODE
