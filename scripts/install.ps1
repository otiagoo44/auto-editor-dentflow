$ErrorActionPreference = 'Stop'
$repoDir = Split-Path $PSScriptRoot -Parent
$uvExe = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
if (-not (Test-Path -LiteralPath $uvExe)) {
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
}
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + $env:Path
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    winget install --id Gyan.FFmpeg --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE) { throw 'No se pudo instalar FFmpeg.' }
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + $env:Path
}
$envDir = Join-Path $env:LOCALAPPDATA 'DentFlow\venv'
$pythonExe = Join-Path $envDir 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    & $uvExe venv $envDir --python 3.12
    if ($LASTEXITCODE) { throw 'No se pudo crear Python 3.12.' }
}
& $uvExe pip install --python $pythonExe -r (Join-Path $repoDir 'requirements.txt')
if ($LASTEXITCODE) { throw 'No se pudieron instalar las dependencias.' }
& $pythonExe (Join-Path $repoDir 'src\editor.py') --warmup
if ($LASTEXITCODE) { throw 'Modelo no preparado. Reintenta install.bat con conexion.' }
& $pythonExe (Join-Path $repoDir 'src\editor.py') --diagnose
exit $LASTEXITCODE
