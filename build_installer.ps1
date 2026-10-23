param([switch]$SkipBrowserDownload)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$stage = Join-Path $PSScriptRoot 'build\installer-assets'
New-Item -ItemType Directory -Path "$stage\defaults", "$stage\bin", "$stage\browsers", "$stage\licenses" -Force | Out-Null
foreach ($name in @('cctv_streams.json', 'cctv_offline.json')) {
    Copy-Item -LiteralPath $name -Destination "$stage\defaults\$name" -Force
}
$settings = Get-Content app_settings.json -Raw | ConvertFrom-Json
$settings.PSObject.Properties.Remove('recordings_dir')
$settings.PSObject.Properties.Remove('backup_dir')
$settings.auto_record_enabled = $false
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText("$stage\defaults\app_settings.json", ($settings | ConvertTo-Json -Depth 100), $utf8)
$ffmpeg = (Get-Command ffmpeg.exe -ErrorAction Stop).Source
Copy-Item -LiteralPath $ffmpeg -Destination "$stage\bin\ffmpeg.exe" -Force
$ffmpegItem = Get-Item -LiteralPath $ffmpeg
$ffmpegReal = if ($ffmpegItem.Target) { $ffmpegItem.Target } else { $ffmpeg }
$ffmpegRoot = Split-Path -Parent (Split-Path -Parent $ffmpegReal)
foreach ($name in @('LICENSE', 'README.txt')) {
    $source = Join-Path $ffmpegRoot $name
    if (-not (Test-Path -LiteralPath $source)) { throw "Dokumen distribusi FFmpeg tidak ditemukan: $source" }
    Copy-Item -LiteralPath $source -Destination "$stage\licenses\FFmpeg-$name" -Force
}
$env:PLAYWRIGHT_BROWSERS_PATH = "$stage\browsers"
if (-not $SkipBrowserDownload) {
    python -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Unduh Chromium gagal' }
}
python -m PyInstaller --noconfirm --clean --onedir --windowed --name 'CCTV ZIQVA' --icon cctv_icon.ico --add-data 'templates;templates' --add-data 'static;static' --add-data 'cctv_icon.ico;.' --add-data "$stage\defaults;defaults" --add-data "$stage\browsers;browsers" --add-binary "$stage\bin\ffmpeg.exe;bin" --hidden-import discover_streams launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Build EXE gagal' }
$compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
& $compiler installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Build installer gagal' }
Get-Item 'dist\CCTV_ZIQVA_Setup_1.0.21.exe' | Select-Object FullName, Length
