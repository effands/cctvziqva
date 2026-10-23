# 🎥 CCTV Recorder Jogja — Panduan Instalasi

**Cara paling mudah:** gunakan `dist/CCTV_ZIQVA_Setup_1.0.0.exe`.
Klik dua kali, pasang, lalu buka shortcut CCTV ZIQVA. Tidak perlu memasang
Python atau FFmpeg. Panduan lengkap: [INSTALL_EXE.md](INSTALL_EXE.md).
Langkah di bawah berlaku untuk paket ZIP kode sumber lama.

Aplikasi untuk merekam multi-stream CCTV (HLS/RTSP) secara otomatis dan paralel, lengkap dengan web dashboard.

---

## ⚙️ Syarat Sistem

| Kebutuhan | Minimal |
|-----------|---------|
| OS | Windows 10 / 11 (64-bit) |
| RAM | 4 GB (disarankan 8 GB+) |
| Penyimpanan | Bebas, sesuai durasi rekaman |
| Koneksi | Internet (untuk stream live CCTV) |

---

## 🚀 Cara Install (Otomatis)

> **Hanya perlu dilakukan sekali saat pertama kali.**

1. Ekstrak seluruh `MULTI_CCTV_SIAP_KIRIM.zip` ke lokasi yang diinginkan (misalnya `D:\CCTV Recorder` atau `C:\Users\NamaKamu\Documents\CCTV`)
2. Klik kanan file **`install.bat`** → pilih **"Run as administrator"**
3. Tunggu proses instalasi selesai (butuh koneksi internet, ±5–10 menit)
4. Setelah selesai, shortcut **"CCTV Recorder Jogja"** akan muncul di Desktop

> ⚠️ **Jangan pindahkan folder ini setelah instalasi**, karena shortcut Desktop menunjuk ke lokasi folder ini.

---

## ▶️ Cara Menjalankan Aplikasi

Setelah instalasi, ada dua cara:

- **Klik shortcut** "CCTV Recorder Jogja" di Desktop
- **Double-click** file `run_cctv_recorder.bat`

Browser akan otomatis terbuka ke: **http://localhost:8899**

---

## 📁 Lokasi File Rekaman (Default)

| Folder | Path |
|--------|------|
| Rekaman | `C:\Users\<NamaKamu>\Videos\CCTV Recordings\` |
| Backup  | `C:\Users\<NamaKamu>\Videos\CCTV Backup\` |

> Lokasi ini bisa diubah di dalam aplikasi melalui menu **Pengaturan**.

Daftar kamera, URL website tersimpan, dan pilihan perekaman dari laptop asal
tetap disertakan. Installer mengisi lokasi rekaman/backup sesuai akun laptop tujuan
tanpa menimpa pilihan lainnya. Rekaman, backup, log, dan cache dari laptop asal
tidak disertakan. Paket ini memerlukan internet untuk instalasi dependensi.

---

## 📦 Isi Paket Ini

| File | Fungsi |
|------|--------|
| `install.bat` | Script instalasi otomatis (jalankan ini pertama kali) |
| `run_cctv_recorder.bat` | Jalankan aplikasi setelah instalasi |
| `web_server.py` | Server web dashboard utama |
| `recorder_engine.py` | Engine perekaman FFmpeg multi-thread |
| `main_gui.py` | GUI desktop (alternatif web dashboard) |
| `discover_streams.py` | Scanner otomatis URL stream CCTV |
| `cctv_streams.json` | Seluruh daftar kamera yang tersimpan dari laptop asal |
| `create_shortcut.py` | Script pembuat shortcut Desktop |
| `requirements.txt` | Daftar library Python yang dibutuhkan |

---

## ❓ Troubleshooting

### "Python tidak ditemukan" saat install
→ Download Python manual di https://www.python.org/downloads/  
→ **Centang "Add Python to PATH"** saat instalasi  
→ Restart laptop, lalu jalankan `install.bat` lagi

### "ffmpeg tidak ditemukan" / rekaman tidak berjalan
→ Pastikan FFmpeg terinstall dan masuk PATH  
→ Bisa install manual via: `winget install Gyan.FFmpeg`  
→ Atau download di https://www.gyan.dev/ffmpeg/builds/

### Error saat membuka dashboard (port bentrok)
→ Port 8899 mungkin dipakai aplikasi lain  
→ Tutup aplikasi lain yang memakai port tersebut, atau edit `web_server.py` baris terakhir ganti `8899` ke port lain (mis. `8080`)

### Fitur "Scan Otomatis" tidak bekerja
→ Playwright Chromium belum terinstall  
→ Buka terminal di folder ini, jalankan: `python -m playwright install chromium`
