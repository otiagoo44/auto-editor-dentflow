@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\studio.ps1" -Install
if errorlevel 1 pause
