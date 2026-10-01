param([switch]$Connect, [string]$Url, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$repoDir = Split-Path $PSScriptRoot -Parent
$privateDir = Join-Path $env:LOCALAPPDATA 'DentFlow\studio'
$configPath = Join-Path $privateDir 'worker.remote.json'
$envPath = Join-Path $privateDir 'vercel.env'
$pythonExe = Join-Path $env:LOCALAPPDATA 'DentFlow\venv\Scripts\python.exe'
function New-PrivateSecret {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}
function Write-PrivateUtf8($filePath, $content) {
    [IO.File]::WriteAllText($filePath, [string]$content, (New-Object System.Text.UTF8Encoding($false)))
}
New-Item -ItemType Directory -Force -Path $privateDir | Out-Null
if ($Connect) {
    if (-not (Test-Path -LiteralPath $configPath)) { throw 'Ejecuta preparar_vercel.bat primero.' }
    if (-not $Url) { $Url = Read-Host 'Pega la URL de produccion de tu Studio (https://...vercel.app)' }
    $studioUri = $null
    if (-not [Uri]::TryCreate($Url.Trim(), [UriKind]::Absolute, [ref]$studioUri) -or
        $studioUri.Scheme -ne 'https' -or $studioUri.UserInfo -or $studioUri.Query -or $studioUri.Fragment -or $studioUri.AbsolutePath -ne '/') {
        throw 'Usa solamente el origen HTTPS de Studio, sin rutas, usuario ni parametros.'
    }
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    $config.url = $studioUri.GetLeftPart([UriPartial]::Authority)
    Write-PrivateUtf8 $configPath ($config | ConvertTo-Json)
    $env:PYTHONUTF8 = '1'
    & $pythonExe (Join-Path $repoDir 'worker\agent.py') --config $configPath --check
    if ($LASTEXITCODE) { throw 'No se pudo conectar. Revisa variables, base de datos, Blob y proteccion de despliegue en web/README.md.' }
    Write-Host 'Conexion comprobada. Abri worker\start-remote-worker.bat y mantene la PC encendida.'
    exit 0
}
if (-not (Test-Path -LiteralPath $envPath)) {
    if (Test-Path -LiteralPath $configPath) { throw 'Existe una configuracion remota anterior. No se reemplazaron sus secretos.' }
    $workerSecret = New-PrivateSecret
    $ownerSecret = New-PrivateSecret
    $mediaSecret = New-PrivateSecret
    @{
        url = ''; token = $workerSecret; worker_id = 'pc-windows-remote'
        state_dir = (Join-Path $env:LOCALAPPDATA 'DentFlow\studio-worker-remote')
    } | ConvertTo-Json | ForEach-Object { Write-PrivateUtf8 $configPath $_ }
    $envContent = @"
STUDIO_MODE=REMOTE_STUDIO
APP_DISPLAY_NAME=DentFlow Studio
OWNER_USER=owner
OWNER_PASSWORD=$ownerSecret
WORKER_TOKEN=$workerSecret
MEDIA_SIGNING_SECRET=$mediaSecret
MAX_UPLOAD_MB=1024
MAX_DURATION_SECONDS=600
MAX_RENDERS_PER_DAY=50
"@
    Write-PrivateUtf8 $envPath $envContent
}
if (-not (Test-Path -LiteralPath $configPath)) { throw 'Falta la configuracion remota del worker. Recuperala antes de usar los secretos existentes.' }
$currentEnv = [IO.File]::ReadAllText($envPath)
Write-PrivateUtf8 $envPath $currentEnv.TrimStart([char]0xFEFF)
$currentConfig = [IO.File]::ReadAllText($configPath)
Write-PrivateUtf8 $configPath $currentConfig.TrimStart([char]0xFEFF)
$keys = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object { ($_ -split '=', 2)[0] }
foreach ($required in @('STUDIO_MODE','OWNER_PASSWORD','WORKER_TOKEN','MEDIA_SIGNING_SECRET')) {
    if ($required -notin $keys) { throw "Falta $required en el archivo privado." }
}
Write-Host 'Configuracion privada preparada, fuera del repositorio.'
Write-Host "En Vercel importa este archivo en Environment Variables: $envPath"
Write-Host 'Selecciona el repositorio, Root Directory: web, Node.js: 24.x.'
Write-Host 'Conecta Neon/Postgres (DATABASE_URL) y Blob PRIVADO (BLOB_READ_WRITE_TOKEN).'
Write-Host 'Tras publicar, ejecuta conectar_worker_vercel.bat.'
Write-Host 'Para entrar: usuario owner y el valor OWNER_PASSWORD del archivo privado.'
if (-not $CheckOnly) { Write-Host 'No compartas el archivo ni lo subas a Git.' }
