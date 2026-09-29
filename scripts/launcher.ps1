param([string]$Folder)
$ErrorActionPreference = 'Stop'
$repoDir = Split-Path $PSScriptRoot -Parent
$pythonExe = Join-Path $env:LOCALAPPDATA 'DentFlow\venv\Scripts\python.exe'
$env:PYTHONUTF8 = '1'
try {
    if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Ejecuta install.bat primero. Para animaciones, tambien instalar_remotion.bat.' }
    Write-Host "`nDentFlow AutoEditor 2.1`n"
    if (-not $Folder) {
        Add-Type -AssemblyName System.Windows.Forms
        $picker = New-Object System.Windows.Forms.FolderBrowserDialog
        $picker.Description = 'Elige tu carpeta Reel (raw.mp4) o la semana completa'
        $picker.SelectedPath = Join-Path $repoDir 'contenido-dentflow'
        if ($picker.ShowDialog() -ne 'OK') { exit 0 }
        $Folder = $picker.SelectedPath
        $picker.Dispose()
    }
    $Folder = (Resolve-Path -LiteralPath $Folder).Path
    Write-Host "Carpeta: $Folder"
    Write-Host '1. Vista previa (rapida, 360 x 640)'
    Write-Host '2. Exportar borrador (1080 x 1920)'
    Write-Host '3. Preparar transcripcion y plan'
    $action = Read-Host 'Elegir [1]'
    if (-not $action) { $action = '1' }
    if ($action -notin @('1','2','3')) { throw 'Opcion invalida.' }
    Write-Host '1. Usar motor del plan (FFmpeg si no hay plan)'
    Write-Host '2. Remotion (animaciones y graficos; requiere instalar_remotion.bat)'
    Write-Host '3. FFmpeg (motor sencillo)'
    $engineChoice = Read-Host 'Elegir [1]'
    if (-not $engineChoice) { $engineChoice = '1' }
    if ($engineChoice -notin @('1','2','3')) { throw 'Opcion invalida.' }
    $jobArgs = @((Join-Path $repoDir 'src\editor.py'), $Folder, '--auto', '--config', (Join-Path $repoDir 'config.yaml'))
    $hasReels = @(Get-ChildItem -LiteralPath $Folder -Directory | Where-Object { $_.Name -match '^Reel' }).Count -gt 0
    if ($hasReels) { $jobArgs += '--week' }
    if ($action -eq '1') { $jobArgs += '--preview' }
    if ($action -eq '3') { $jobArgs += '--plan-only' }
    if ($engineChoice -eq '2') { $jobArgs += @('--engine','remotion') }
    if ($engineChoice -eq '3') { $jobArgs += @('--engine','ffmpeg') }
    & $pythonExe @jobArgs
    if ($LASTEXITCODE) { throw 'Hubo errores. Revisa el reporte en OUTPUT; las salidas anteriores se conservan.' }
    Write-Host "`nListo. Revisa OUTPUT en la carpeta del Reel."
    Write-Host 'Preview: VIDEO_PREVIEW.mp4 | Borrador: VIDEO_BORRADOR.mp4'
    Write-Host 'Antes de publicar: revisa voz, subtitulos, rostro y lectura en tu telefono.'
} catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host 'Enter para cerrar'
    exit 1
}
Read-Host 'Enter para cerrar'
