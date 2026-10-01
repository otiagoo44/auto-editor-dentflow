@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\studio.ps1" -WorkerOnly -Remote
if errorlevel 1 pause
