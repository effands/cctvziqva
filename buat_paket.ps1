# Buat ZIP distribusi tanpa rekaman, backup, log, dan cache.
param([switch]$NoPause)
$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
$zipPath = Join-Path $projectDir 'CCTV_ZIQVA_SIAP_KIRIM.zip'
$stageDir = Join-Path ([IO.Path]::GetTempPath()) ('MultiCCTV-Package-' + [guid]::NewGuid())
$innerDir = Join-Path $stageDir 'CCTV ZIQVA'
$requiredFiles = @(
    'install.bat', 'run_cctv_recorder.bat', 'setup_config.py',
    'create_shortcut.py', 'requirements.txt', 'cctv_icon.ico',
    'main_gui.py', 'web_server.py', 'recorder_engine.py', 'discover_streams.py', 'app_paths.py',
    'cctv_streams.json', 'cctv_offline.json', 'denpasar_cctv.json', 'app_settings.json',
    'README.md', 'CARA_INSTALL.md', 'MULAI_DI_SINI.txt', 'buat_paket.ps1'
)
try {
    New-Item -ItemType Directory -Path $innerDir -Force | Out-Null
    foreach ($relative in $requiredFiles) {
        $source = Join-Path $projectDir $relative
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
            throw "File wajib tidak ditemukan: $relative"
        }
        Copy-Item -LiteralPath $source -Destination (Join-Path $innerDir $relative)
    }
    foreach ($folder in @('static', 'templates', 'docs', 'tools', 'tests')) {
        $source = Join-Path $projectDir $folder
        if (Test-Path -LiteralPath $source -PathType Container) {
            New-Item -ItemType Directory -Path (Join-Path $innerDir $folder) -Force | Out-Null
            Get-ChildItem -LiteralPath $source -Recurse -File |
                Where-Object { $_.Extension -ne '.pyc' -and $_.FullName -notmatch '[\\/]__pycache__[\\/]' } |
                ForEach-Object {
                    $relative = $_.FullName.Substring($projectDir.Length + 1)
                    $destination = Join-Path $innerDir $relative
                    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
                    Copy-Item -LiteralPath $_.FullName -Destination $destination
                }
        }
    }
    # Sesuaikan hanya salinan paket; konfigurasi laptop asal tetap utuh.
    # Installer mengisi kedua path sesuai akun Windows di laptop tujuan.
    $settingsPath = Join-Path $innerDir 'app_settings.json'
    $settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
    $settings.PSObject.Properties.Remove('recordings_dir')
    $settings.PSObject.Properties.Remove('backup_dir')
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($settingsPath, ($settings | ConvertTo-Json -Depth 100), $utf8)
    $manifest = Get-ChildItem -LiteralPath $innerDir -Recurse -File | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($innerDir.Length + 1).Replace('\', '/')
        '{0}  {1}' -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower(), $relative
    }
    [IO.File]::WriteAllLines((Join-Path $innerDir 'SHA256SUMS.txt'), [string[]]$manifest, $utf8)
    Compress-Archive -LiteralPath $innerDir -DestinationPath $zipPath -Force
    Write-Host "Selesai: $zipPath"
    Write-Host ('Ukuran: {0:N2} MB' -f ((Get-Item -LiteralPath $zipPath).Length / 1MB))
} finally {
    # Verifikasi bahwa staging berada di TEMP sebelum menghapusnya.
    $resolvedStage = [IO.Path]::GetFullPath($stageDir)
    $resolvedTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resolvedStage.StartsWith($resolvedTemp, [StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path -Leaf $resolvedStage) -like 'MultiCCTV-Package-*' -and
        (Test-Path -LiteralPath $resolvedStage)) {
        Remove-Item -LiteralPath $resolvedStage -Recurse -Force
    }
}
if (-not $NoPause) { Read-Host 'Tekan Enter untuk menutup' }
