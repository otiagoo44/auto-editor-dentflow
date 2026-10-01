@echo off
call "%~dp0..\install.bat"
if errorlevel 1 exit /b 1
call "%~dp0..\instalar_remotion.bat"
if errorlevel 1 exit /b 1
call "%~dp0..\instalar_studio.bat"
