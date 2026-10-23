@echo off
title Jogja CCTV Recorder Launcher
cd /d "%~dp0"
echo ==================================================
echo   Memulai Jogja CCTV Recorder ^& Web Hub...
echo ==================================================
python --version >nul 2>&1
if %errorlevel%==0 (
    start "" http://localhost:8899
    python web_server.py
    goto selesai
)
py --version >nul 2>&1
if %errorlevel%==0 (
    start "" http://localhost:8899
    py web_server.py
    goto selesai
)
echo Python belum tersedia. Jalankan install.bat terlebih dahulu.
:selesai
pause
