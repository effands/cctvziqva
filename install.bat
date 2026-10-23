@echo off
title CCTV Recorder Jogja - Installer
cd /d "%~dp0"

echo.
echo ==================================================
echo   CCTV Recorder Jogja - Auto Installer
echo ==================================================
echo.

rem -------------------------------------------------------
rem [1/6] Cek Python - coba "python" lalu "py" launcher
rem -------------------------------------------------------
echo [1/6] Memeriksa Python...

set PYTHON_CMD=

python --version >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python
    goto python_found
)

py --version >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
    goto python_found
)

rem Python belum ada - install via winget
echo      Python belum ditemukan. Mencoba install via Winget...
winget install --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Gagal install Python otomatis.
    echo.
    echo  Silakan download Python manual:
    echo  https://www.python.org/downloads/
    echo.
    echo  PENTING: Centang "Add Python to PATH" saat install!
    echo  Setelah itu jalankan install.bat lagi.
    echo.
    pause
    exit /b 1
)

rem Cek lagi setelah install
python --version >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python
    goto python_found
)
py --version >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
    goto python_found
)

echo.
echo  Python sudah diinstall. Mohon RESTART laptop ini,
echo  lalu jalankan install.bat lagi agar PATH terupdate.
echo.
pause
exit /b 0

:python_found
for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do echo      Ditemukan: %%v

rem -------------------------------------------------------
rem [2/6] Upgrade pip
rem -------------------------------------------------------
echo.
echo [2/6] Memperbarui pip...
%PYTHON_CMD% -m pip install --upgrade pip --quiet
echo      pip siap.

rem -------------------------------------------------------
rem [3/6] Install library Python
rem -------------------------------------------------------
echo.
echo [3/6] Menginstall library Python (Flask, CustomTkinter, dll)...
%PYTHON_CMD% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Gagal install library Python.
    echo  Pastikan laptop terhubung internet lalu coba lagi.
    pause
    exit /b 1
)
echo      Semua library berhasil diinstall.

rem -------------------------------------------------------
rem [4/6] Install Playwright Chromium
rem -------------------------------------------------------
echo.
echo [4/6] Menginstall Playwright Chromium (stream scanner)...
%PYTHON_CMD% -m playwright install chromium
if %errorlevel% neq 0 (
    echo      [PERINGATAN] Playwright gagal. Fitur Auto-Scan tidak aktif.
    echo      Rekaman manual tetap bisa digunakan.
)

rem -------------------------------------------------------
rem [5/6] Cek dan install FFmpeg
rem -------------------------------------------------------
echo.
echo [5/6] Memeriksa FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel%==0 (
    echo      FFmpeg sudah tersedia.
    goto ffmpeg_done
)

echo      FFmpeg belum ada. Mencoba install via Winget...
winget install --id Gyan.FFmpeg --silent --accept-source-agreements --accept-package-agreements
if %errorlevel% neq 0 (
    echo.
    echo  [PERINGATAN] FFmpeg gagal install otomatis.
    echo  Download manual: https://www.gyan.dev/ffmpeg/builds/
    echo  Ekstrak lalu tambahkan folder bin ke PATH Windows.
    echo.
) else (
    echo      FFmpeg berhasil diinstall.
)

:ffmpeg_done

rem -------------------------------------------------------
rem [6/6] Setup konfigurasi dan shortcut Desktop
rem -------------------------------------------------------
echo.
echo [6/6] Menyiapkan konfigurasi dan shortcut Desktop...

%PYTHON_CMD% setup_config.py
if %errorlevel% neq 0 (
    echo      [PERINGATAN] Konfigurasi gagal - akan pakai default.
)

%PYTHON_CMD% create_shortcut.py
if %errorlevel% neq 0 (
    echo      [PERINGATAN] Shortcut gagal dibuat.
    echo      Jalankan manual via run_cctv_recorder.bat
)

rem -------------------------------------------------------
rem Selesai
rem -------------------------------------------------------
echo.
echo ==================================================
echo   Instalasi Selesai!
echo.
echo   Cara menjalankan:
echo   - Klik shortcut CCTV Recorder Jogja di Desktop
echo   - ATAU double-click run_cctv_recorder.bat
echo.
echo   Dashboard: http://localhost:8899
echo ==================================================
echo.
echo   Rekaman : %USERPROFILE%\Videos\CCTV Recordings
echo   Backup  : %USERPROFILE%\Videos\CCTV Backup
echo.
pause
