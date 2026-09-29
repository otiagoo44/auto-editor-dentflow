@echo off
setlocal
set "PYTHONUTF8=1"
set "DF_PY=%LOCALAPPDATA%\DentFlow\venv\Scripts\python.exe"
if not exist "%DF_PY%" (
  echo Ejecuta install.bat primero.
  exit /b 1
)
if "%~1"=="" (
  echo Arrastra una carpeta de semana con carpetas Reel o pasala como argumento.
  exit /b 1
)
"%DF_PY%" "%~dp0src\editor.py" %* --week --config "%~dp0config.yaml"
exit /b %errorlevel%

