# Test the exact Help recipe with synthetic Telegram responses. No network calls.
$ErrorActionPreference='Stop'
$taskHelpText=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot '../docs/BUILTIN-HELP.en.md')
$taskRecipe=[regex]::Match($taskHelpText,'(?s)\$privateKey = Read-Host.*?finally \{ Remove-Variable privateKey,botKey,updates,ids -ErrorAction SilentlyContinue \}')
if(-not $taskRecipe.Success){throw 'CHAT-ID-RECIPE-MISSING'}
$taskTokens=$null;$taskParseErrors=$null
[void][Management.Automation.Language.Parser]::ParseInput($taskRecipe.Value,[ref]$taskTokens,[ref]$taskParseErrors)
if($taskParseErrors.Count){throw 'CHAT-ID-RECIPE-PARSE'}
$global:RecipeFailure=$false;$global:RecipeCalls=0
function Read-Host {param($Prompt,[switch]$AsSecureString) if(-not $AsSecureString){throw 'TOKEN-NOT-SECURE-INPUT'};ConvertTo-SecureString 'synthetic-only-key' -AsPlainText -Force}
function Invoke-RestMethod {
 param($Uri,$TimeoutSec,$ErrorAction)
 $global:RecipeCalls++
 if($Uri -ne 'https://api.telegram.org/botsynthetic-only-key/getUpdates' -or $TimeoutSec -ne 15){throw 'WRONG-API-REQUEST'}
 if($global:RecipeFailure){throw ('Simulated HTTP failure '+$Uri)}
 @{result=@(@{message=@{chat=@{id=123}}},@{channel_post=@{chat=@{id=-456}}},@{edited_message=@{chat=@{id=123}}})}
}
$taskBlock=[scriptblock]::Create($taskRecipe.Value)
$taskOutput=@(& $taskBlock)
if(($taskOutput -join ',') -ne '-456,123'){throw 'CHAT-ID-RECIPE-OUTPUT'}
$global:RecipeFailure=$true
$taskOutput=@(& $taskBlock)
if(($taskOutput -join ' ') -notmatch '^CHAT-ID-NOT-READ:' -or ($taskOutput -join ' ') -match 'synthetic-only-key|https://'){throw 'CHAT-ID-ERROR-DISCLOSES-TOKEN'}
if($global:RecipeCalls -ne 2){throw 'UNEXPECTED-CALL-COUNT'}
Write-Output 'PASS: exact Help recipe parses, selects/deduplicates chat IDs, suppresses token-bearing HTTP errors; mocked API only.'
