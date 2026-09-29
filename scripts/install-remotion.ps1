$ErrorActionPreference = 'Stop'
$repoDir = Split-Path $PSScriptRoot -Parent
$env:Path += ';' + [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Instala Node.js LTS desde nodejs.org y repite instalar_remotion.bat.' }
    winget install --id OpenJS.NodeJS.LTS --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE) { throw 'No se pudo instalar Node.js LTS.' }
    $env:Path += ';' + [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
}
Push-Location (Join-Path $repoDir 'remotion')
try {
    & npm.cmd ci --no-audit --no-fund
    if ($LASTEXITCODE) { throw 'No se pudieron instalar dependencias Remotion fijadas por package-lock.json.' }
    & npm.cmd run typecheck
    if ($LASTEXITCODE) { throw 'Falló la comprobación TypeScript.' }
    & npm.cmd run browser
    if ($LASTEXITCODE) { throw 'Chromium no descargado. Repite con conexión.' }
    Write-Host 'Remotion instalado. Ya puedes renderizar localmente con --engine remotion.'
} finally { Pop-Location }
