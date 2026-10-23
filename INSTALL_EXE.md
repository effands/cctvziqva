# Installer Windows CCTV ZIQVA

Kirim **`dist/CCTV_ZIQVA_Setup_1.0.0.exe`** ke laptop Windows 10/11 64-bit.

1. Klik dua kali installer, lalu ikuti tombol Next / Install.
2. Buka **CCTV ZIQVA** lewat shortcut Desktop atau Start Menu.
3. Dashboard terbuka di browser. Biarkan jendela kecil CCTV ZIQVA tetap terbuka selama merekam.
4. Untuk keluar, klik **Hentikan dan Tutup** di jendela kecil tersebut.

Python, FFmpeg, dan Chromium untuk pemindaian sudah disertakan. Instalasi tidak
memerlukan unduhan tambahan. Internet tetap diperlukan untuk kamera live,
pemindaian website, serta aset dashboard yang diambil dari CDN.

Daftar kamera dari laptop pembuat ikut disertakan. Rekaman, backup, log lama,
dan lokasi folder pribadi laptop pembuat tidak disertakan.

- Rekaman awal: `%USERPROFILE%\Videos\CCTV Recordings`
- Backup awal: `%USERPROFILE%\Videos\CCTV Backup`
- Pengaturan, daftar kamera, dan log: `%LOCALAPPDATA%\CCTV ZIQVA`
- Aplikasi: `%LOCALAPPDATA%\Programs\CCTV ZIQVA`

Folder rekaman dan backup bisa diganti melalui Pengaturan. Pembaruan installer
tidak menimpa data kamera atau pengaturan yang sudah ada. Uninstall tersedia
melalui Settings Windows dan mempertahankan data serta rekaman pengguna.

## Membuat ulang installer

Di komputer pengembang yang memiliki Python, dependensi `requirements.txt`,
PyInstaller, FFmpeg di PATH, dan Inno Setup 6:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_installer.ps1
```

Build pertama mengunduh Chromium yang cocok dengan versi Playwright terpasang.
Gunakan `-SkipBrowserDownload` untuk menggunakan kembali browser build yang sama.
