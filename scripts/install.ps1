$ErrorActionPreference = 'Stop'
$repoDir = Split-Path $PSScriptRoot -Parent
function Refresh-ToolPath {
    $env:Path = $env:Path + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
}
Refresh-ToolPath
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Falta winget: instala App Installer y vuelve a ejecutar install.bat.' }
    # Paquete del gestor; nunca ejecutar texto de scripts remotos con Invoke-Expression.
    winget install --id astral-sh.uv --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE) { throw 'No se pudo instalar uv mediante winget.' }
    Refresh-ToolPath
}
$uvCommand = Get-Command uv -ErrorAction Stop
$uvExe = $uvCommand.Source
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Falta winget: instala App Installer o FFmpeg con ffprobe y libass, y repite install.bat.' }
    winget install --id Gyan.FFmpeg --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE) { throw 'No se pudo instalar FFmpeg.' }
    Refresh-ToolPath
}
Get-Command ffmpeg, ffprobe -ErrorAction Stop | Out-Null
$env:PYTHONUTF8 = '1'
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
