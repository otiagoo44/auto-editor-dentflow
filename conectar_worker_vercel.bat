@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\prepare-vercel.ps1" -Connect
pause
