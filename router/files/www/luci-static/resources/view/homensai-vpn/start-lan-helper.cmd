@echo off
rem HomenS.AI LAN helper launcher: double-click. Needs PowerShell 7 (winget install Microsoft.PowerShell).
title HomenS.AI LAN helper
where pwsh >nul 2>nul
if errorlevel 1 (
  echo PowerShell 7 was not found. Install it with:  winget install Microsoft.PowerShell
  echo Then double-click this file again.
  pause
  exit /b 1
)
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-lan-helper.ps1"
pause
