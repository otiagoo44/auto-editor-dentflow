@echo off
setlocal
set "PYTHONUTF8=1"
set "DF_PY=%LOCALAPPDATA%\DentFlow\venv\Scripts\python.exe"
if not exist "%DF_PY%" (
  echo Ejecuta install.bat primero.
  exit /b 1
)
if "%~1"=="" (
  echo Arrastra una carpeta Reel sobre este archivo o pasala como argumento.
  exit /b 1
)
"%DF_PY%" "%~dp0src\editor.py" %* --config "%~dp0config.yaml"
exit /b %errorlevel%

