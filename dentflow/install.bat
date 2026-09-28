@echo off
setlocal
set "DF_UV=%USERPROFILE%\.local\bin\uv.exe"
if not exist "%DF_UV%" (
  echo Falta uv. Instala uv desde https://docs.astral.sh/uv/getting-started/installation/
  exit /b 1
)
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo Falta FFmpeg en PATH. Instala FFmpeg con ffprobe y libass.
  exit /b 1
)
where ffprobe >nul 2>&1
if errorlevel 1 exit /b 1
set "DF_ENV=%LOCALAPPDATA%\DentFlow\venv"
if not exist "%DF_ENV%\Scripts\python.exe" (
  "%DF_UV%" venv "%DF_ENV%" --python 3.12
  if errorlevel 1 exit /b 1
)
"%DF_UV%" pip install --python "%DF_ENV%\Scripts\python.exe" -r "%~dp0requirements.txt"
if errorlevel 1 exit /b 1
"%DF_ENV%\Scripts\python.exe" "%~dp0src\editor.py" --diagnose
exit /b %errorlevel%

