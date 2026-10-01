param([switch]$Install,[switch]$WorkerOnly,[switch]$Remote)
$ErrorActionPreference='Stop'
$repoDir=Split-Path $PSScriptRoot -Parent
$env:Path += ';' + [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
$pythonExe=Join-Path $env:LOCALAPPDATA 'DentFlow\venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Ejecuta install.bat primero para preparar Python/FFmpeg/Whisper.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Ejecuta instalar_remotion.bat para preparar Node.js.' }
$env:PYTHONUTF8='1'
$configDir=Join-Path $env:LOCALAPPDATA 'DentFlow\studio'
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
$configFile=Join-Path $configDir 'worker.local.json'
if ($Remote) {
    if (-not $WorkerOnly) { throw 'El modo remoto inicia solamente el worker.' }
    $remoteFile=Join-Path $configDir 'worker.remote.json'
    if (-not (Test-Path -LiteralPath $remoteFile)) { throw 'Ejecuta preparar_vercel.bat y conectar_worker_vercel.bat primero.' }
    $remoteConfig=Get-Content -LiteralPath $remoteFile -Raw | ConvertFrom-Json
    if (-not $remoteConfig.url) { throw 'Ejecuta conectar_worker_vercel.bat primero.' }
    & $pythonExe (Join-Path $repoDir 'worker\agent.py') --config $remoteFile
    exit $LASTEXITCODE
}
$envFile=Join-Path $repoDir 'web\.env.local'
if (-not (Test-Path -LiteralPath $configFile)) {
    $bytes=New-Object byte[] 32
    $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $rng.Dispose()
    $workerSecret=[Convert]::ToBase64String($bytes)
    @{url='http://127.0.0.1:3000';token=$workerSecret;worker_id='pc-windows'} | ConvertTo-Json | Set-Content -LiteralPath $configFile -Encoding UTF8
    if (Test-Path -LiteralPath $envFile) { throw 'Ya existe web/.env.local. Vincula WORKER_TOKEN con worker.local.json sin reemplazar tu configuración.' }
    "STUDIO_MODE=LOCAL_STUDIO`nWORKER_TOKEN=$workerSecret`n" | Set-Content -LiteralPath $envFile -Encoding UTF8
}
if ($Install) {
    Push-Location (Join-Path $repoDir 'web')
    try {
        & npm.cmd ci --no-fund
        if ($LASTEXITCODE) { throw 'No se pudieron instalar dependencias web.' }
        & npm.cmd run build
        if ($LASTEXITCODE) { throw 'No se pudo compilar Studio.' }
    } finally { Pop-Location }
    Write-Host 'Studio instalado. Abrí iniciar_studio.bat.'
    exit 0
}
if ($WorkerOnly) { & $pythonExe (Join-Path $repoDir 'worker\agent.py') --config $configFile; exit $LASTEXITCODE }
if (-not (Test-Path -LiteralPath (Join-Path $repoDir 'web\.next\BUILD_ID'))) { throw 'Primero ejecuta instalar_studio.bat.' }
$nodeExe=(Get-Command node -ErrorAction Stop).Source
$nextCli=Join-Path $repoDir 'web\node_modules\next\dist\bin\next'
$serverLog=Join-Path $configDir 'web.log'
$serverError=Join-Path $configDir 'web.error.log'
$workerLog=Join-Path $configDir 'worker.log'
$workerError=Join-Path $configDir 'worker.error.log'
Write-Host 'Iniciando Studio local. Mantené esta ventana abierta. Ctrl+C detiene los procesos.'
$server=$null
$worker=$null
try {
    $server=Start-Process -FilePath $nodeExe -ArgumentList @(('"'+$nextCli+'"'),'start','--hostname','127.0.0.1','--port','3000') -WorkingDirectory (Join-Path $repoDir 'web') -WindowStyle Hidden -PassThru -RedirectStandardOutput $serverLog -RedirectStandardError $serverError
    $worker=Start-Process -FilePath $pythonExe -ArgumentList @('-u',('"'+(Join-Path $repoDir 'worker\agent.py')+'"'),'--config',('"'+$configFile+'"')) -WorkingDirectory $repoDir -WindowStyle Hidden -PassThru -RedirectStandardOutput $workerLog -RedirectStandardError $workerError
    $ready=$false
    for ($attempt=0;$attempt -lt 30;$attempt++) {
        if ($server.HasExited) { throw 'Studio no arrancó. Revisa web.error.log; puede haber otra instancia abierta.' }
        try { $result=Invoke-WebRequest -Uri 'http://127.0.0.1:3000/api/status' -UseBasicParsing; if ($result.StatusCode -eq 200) { $ready=$true;break } } catch {}
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Studio no respondió al inicio. Revisa los logs locales.' }
    Start-Process 'http://127.0.0.1:3000'
    while (-not $server.HasExited -and -not $worker.HasExited) { Start-Sleep -Seconds 2 }
    throw 'Un proceso terminó. Revisá los logs locales en %LOCALAPPDATA%\DentFlow\studio.'
} finally {
    foreach ($process in @($worker,$server)) {
        if ($null -ne $process -and -not $process.HasExited) { & taskkill.exe /PID $process.Id /T /F | Out-Null }
    }
}
