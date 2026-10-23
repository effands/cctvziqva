# CCTV Jogja Multi Recorder & Backup System

**Installer EXE Windows:** kirim `dist/CCTV_ZIQVA_Setup_1.0.0.exe` ke laptop lain,
lalu klik dua kali untuk memasang. Python, FFmpeg, dan browser pemindai sudah
disertakan. Petunjuk: [INSTALL_EXE.md](INSTALL_EXE.md).

Tool otomatis untuk memindai, merekam layar/stream HLS (`.m3u8`), dan melakukan backup otomatis untuk multi-CCTV dari portal [cctv.jogjakota.go.id](https://cctv.jogjakota.go.id/).

---

## 🚀 Fitur Utama
1. **Multi-Stream Recording Concurrent**: Merekam banyak CCTV sekaligus dalam 1 waktu menggunakan FFmpeg subprocess tanpa beban re-encoding CPU yang berat.
2. **Auto Stream Discoverer**: Menggunakan Playwright untuk secara otomatis memindai stream m3u8 dari peta interactive CCTV Jogja.
3. **Segmentation & Rotation**: Mengelompokkan dan memotong video per 60 menit secara otomatis.
4. **Auto-Retry & Resiliency**: Jika jaringan terputus/stream mati, recorder akan mencoba menghubungkan ulang secara otomatis.
5. **Instant Backup**: Tombol backup satu klik untuk mencadangkan seluruh rekaman ke folder backup khusus.
6. **Modern GUI**: Antarmuka desktop interaktif berbasis CustomTkinter.

---

## 📁 Struktur Project
- `dist/MULTI_CCTV_SIAP_KIRIM.zip` : Satu paket untuk dikirim ke laptop Windows lain
- `MULAI_DI_SINI.txt` : Petunjuk singkat instalasi di laptop tujuan
- `docs/preview/` : Gambar referensi dashboard
- `tools/` : Script bantu inspeksi website dan pembuatan ikon
- `buat_paket.ps1` : Membuat ulang paket distribusi dari folder ini
- `main_gui.py` : Aplikasi desktop utama (GUI)
- `recorder_engine.py` : Engine perekaman FFmpeg multi-thread & logika backup
- `discover_streams.py` : Script otomatis pencari URL stream m3u8 menggunakan Playwright
- `cctv_streams.json` : Konfigurasi daftar CCTV & URL stream
- `recordings/` : Folder output penyimpanan hasil rekaman video
- `backup/` : Folder penyimpanan hasil backup

Untuk membuat ulang paket: `powershell -ExecutionPolicy Bypass -File .\buat_paket.ps1 -NoPause`.
Paket menyertakan kode aplikasi, aset, daftar kamera, dan pilihan pengaturan.
Lokasi rekaman/backup dalam paket akan disesuaikan dengan akun Windows laptop tujuan
oleh installer. Log, cache, rekaman, dan backup lama tidak dikirim dan tetap ada di laptop asal.
Instalasi dependensi memerlukan internet; paket ini bukan EXE mandiri.

---

## 🛠️ Cara Penggunaan

### 1. Jalankan Stream Discoverer (Opsional)
Untuk memindai stream m3u8 terbaru dari website CCTV Jogja:
```bash
python discover_streams.py
```

### 2. Jalankan GUI Utama
Untuk membuka dashboard perekam CCTV:
```bash
python main_gui.py
```

---

## 💡 Tambah Stream Manual
Anda juga dapat menambah URL stream HLS (`.m3u8`) atau RTSP langsung melalui aplikasi GUI (tombol **Tambah Kamera**) atau mengedit file `cctv_streams.json`.

## Dashboard Kamera

Dashboard menampilkan kamera tersimpan dan kontrol perekaman. Gunakan **Tambah Manual** untuk memasukkan nama kamera, lokasi, dan URL stream HLS/RTSP. Gunakan **Scan Website** untuk memindai URL website yang Anda masukkan. Filter **Negara kamera tersimpan** menyediakan pilihan negara yang tersedia dan **All**. Panel embed sumber eksternal telah dihapus.
