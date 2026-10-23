"""
CCTV Multi Recorder - Modern Desktop GUI (CustomTkinter)
======================================================
Fitur:
- Dashboard status real-time untuk multi-CCTV
- Pemindaian otomatis & penambahan manual URL stream (.m3u8 / RTSP)
- Merekam semua CCTV sekaligus / kontrol per kamera
- Monitoring Disk Space & Folder Rekaman
- Manajemen daftar CCTV & Pengaturan interval rekaman
"""

import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk

from recorder_engine import CCTVRecorder, CONFIG_FILE, RECORDINGS_DIR, LOGS_DIR, load_settings, save_settings

# Set tema CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class CCTVApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("CCTV ZIQVA - Global Stream & Auto Recorder")
        self.geometry("1100 x 700")

        # Inisialisasi engine
        self.recorder = CCTVRecorder()
        self.recorder.on_status_update = self.schedule_ui_update

        # Data stream lokal
        self.cctv_configs = []
        self.card_widgets = {}

        self.load_cctv_configs()
        self.build_ui()
        self.start_status_loop()

    def load_cctv_configs(self):
        """Membaca daftar CCTV dari file JSON"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.cctv_configs = json.load(f)
            except Exception as e:
                self.cctv_configs = []
        else:
            self.cctv_configs = []

    def save_cctv_configs(self):
        """Menyimpan daftar CCTV ke file JSON"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cctv_configs, f, indent=2, ensure_ascii=False)
        self.recorder.reload_config()

    def build_ui(self):
        """Membangun komponen UI utama"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ================= SIDEBAR =================
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(9, weight=1)

        # Logo / Title
        logo_label = ctk.CTkLabel(self.sidebar, text="📹 CCTV ZIQVA", font=ctk.CTkFont(size=19, weight="bold"))
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 6))

        sub_logo = ctk.CTkLabel(self.sidebar, text="by team ziqva.com", font=ctk.CTkFont(size=11, slant="italic"), text_color="#ffc107")
        sub_logo.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Action Buttons
        self.btn_start_all = ctk.CTkButton(
            self.sidebar, text="▶ Start Record All", fg_color="#28a745", hover_color="#218838",
            font=ctk.CTkFont(weight="bold"), command=self.start_all_recording
        )
        self.btn_start_all.grid(row=2, column=0, padx=20, pady=8)

        self.btn_stop_all = ctk.CTkButton(
            self.sidebar, text="⏹ Stop Record All", fg_color="#dc3545", hover_color="#c82333",
            font=ctk.CTkFont(weight="bold"), command=self.stop_all_recording
        )
        self.btn_stop_all.grid(row=3, column=0, padx=20, pady=8)

        # Auto Record Button & Status
        self.btn_auto_record = ctk.CTkButton(
            self.sidebar, text="🔁 Start Auto Rekam", fg_color="#fd7e14", hover_color="#e8590c",
            font=ctk.CTkFont(weight="bold"), command=self.toggle_auto_record
        )
        self.btn_auto_record.grid(row=4, column=0, padx=20, pady=8)

        self.auto_status_label = ctk.CTkLabel(
            self.sidebar, text="Auto Rekam: IDLE", font=ctk.CTkFont(size=11), text_color="#aaa"
        )
        self.auto_status_label.grid(row=5, column=0, padx=15, pady=(0, 8))

        self.btn_add_cam = ctk.CTkButton(
            self.sidebar, text="➕ Tambah Kamera", fg_color="#6c757d", hover_color="#5a6268",
            command=self.open_add_camera_modal
        )
        self.btn_add_cam.grid(row=6, column=0, padx=20, pady=8)

        self.btn_settings = ctk.CTkButton(
            self.sidebar, text="⚙ Pengaturan", fg_color="#495057", hover_color="#343a40",
            command=self.open_settings_modal
        )
        self.btn_settings.grid(row=7, column=0, padx=20, pady=8)

        # Disk Space Status
        self.disk_label = ctk.CTkLabel(self.sidebar, text="Disk Free: Checking...", font=ctk.CTkFont(size=12))
        self.disk_label.grid(row=9, column=0, padx=20, pady=(20, 0))

        # Footer
        footer_label = ctk.CTkLabel(self.sidebar, text="v1.0.0 • Pemkot Jogja CCTV", font=ctk.CTkFont(size=10))
        footer_label.grid(row=11, column=0, padx=20, pady=10)

        # ================= MAIN CONTENT =================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Header Info
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.header_title = ctk.CTkLabel(header_frame, text="Daftar Kamera CCTV", font=ctk.CTkFont(size=18, weight="bold"))
        self.header_title.pack(side="left", padx=5)

        self.total_status_label = ctk.CTkLabel(header_frame, text="Total: 0 Kamera | 0 Merekam", font=ctk.CTkFont(size=13))
        self.total_status_label.pack(side="right", padx=5)

        # Scrollable Frame for CCTV Cards
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Kamera Aktif & Stream Status")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.scroll_frame.grid_columnconfigure((0, 1), weight=1)

        self.render_cctv_cards()

    def render_cctv_cards(self):
        """Merender seluruh list CCTV sebagai card grid"""
        # Clear existing
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.card_widgets.clear()

        if not self.cctv_configs:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame, 
                text="Belum ada kamera CCTV terdaftar.\nKlik 'Tambah Kamera' atau buat daftar di cctv_streams.json",
                font=ctk.CTkFont(size=14)
            )
            empty_lbl.grid(row=0, column=0, columnspan=2, pady=50)
            return

        for idx, cam in enumerate(self.cctv_configs):
            row = idx // 2
            col = idx % 2

            card = ctk.CTkFrame(self.scroll_frame, corner_radius=10, border_width=1, border_color="#343a40")
            card.grid(row=row, column=col, sticky="ew", padx=10, pady=10)
            card.grid_columnconfigure(1, weight=1)

            # Title & Location (Nama, Kota, Negara)
            title_lbl = ctk.CTkLabel(card, text=cam["name"], font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
            title_lbl.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 2))

            area_val = cam.get("location", "Area CCTV")
            city_val = cam.get("city", "Yogyakarta")
            country_val = cam.get("country", "Indonesia")
            if city_val.lower() in area_val.lower():
                full_loc = f"📍 {area_val} • {country_val}"
            else:
                full_loc = f"📍 {area_val}, {city_val} • {country_val}"

            loc_lbl = ctk.CTkLabel(card, text=full_loc, font=ctk.CTkFont(size=11), text_color="#17a2b8", anchor="w")
            loc_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 8))

            # Status Indicator
            status_indicator = ctk.CTkLabel(card, text="● OFF", font=ctk.CTkFont(weight="bold"), text_color="#6c757d", anchor="w")
            status_indicator.grid(row=2, column=0, sticky="w", padx=15, pady=2)

            info_lbl = ctk.CTkLabel(card, text="File: - | Size: 0 MB", font=ctk.CTkFont(size=11), text_color="#ccc", anchor="w")
            info_lbl.grid(row=3, column=0, columnspan=2, sticky="w", padx=15, pady=2)

            # Control Buttons per Card
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 15))

            btn_rec = ctk.CTkButton(
                btn_frame, text="Start", width=80, fg_color="#28a745", hover_color="#218838",
                command=lambda cid=cam["id"], url=cam["stream_url"]: self.toggle_record(cid, url)
            )
            btn_rec.pack(side="left", padx=(0, 5))

            btn_del = ctk.CTkButton(
                btn_frame, text="Hapus", width=60, fg_color="#dc3545", hover_color="#c82333",
                command=lambda cid=cam["id"]: self.delete_camera(cid)
            )
            btn_del.pack(side="right")

            # Store widget references for live updates
            self.card_widgets[cam["id"]] = {
                "card": card,
                "orig_idx": idx,
                "status_indicator": status_indicator,
                "info_lbl": info_lbl,
                "btn_rec": btn_rec,
                "config": cam
            }

    def toggle_record(self, cctv_id: str, stream_url: str):
        """Start/Stop perekaman per kamera"""
        statuses = self.recorder.get_all_status()
        status = statuses.get(cctv_id)

        if not stream_url:
            messagebox.showerror("Error", f"URL Stream untuk {cctv_id} kosong! Harap isi URL m3u8.")
            return

        if status and status.is_recording:
            self.recorder.stop_stream(cctv_id)
        else:
            self.recorder.start_stream(cctv_id, stream_url)

    def start_all_recording(self):
        """Memulai semua kamera yang valid"""
        if not self.cctv_configs:
            messagebox.showwarning("Peringatan", "Tidak ada kamera terdaftar.")
            return
        self.recorder.start_all(self.cctv_configs)

    def stop_all_recording(self):
        """Menghentikan seluruh perekaman"""
        self.recorder.stop_all()

    def open_add_camera_modal(self):
        """Dialog popup untuk menambah kamera baru"""
        dialog = ctk.CTkInputDialog(text="Masukkan Nama CCTV & URL m3u8 (Dipisahkan koma):\nContoh: Malioboro 1, https://domain.com/live.m3u8", title="Tambah Kamera CCTV")
        res = dialog.get_input()
        if res and "," in res:
            parts = res.split(",", 1)
            name = parts[0].strip()
            url = parts[1].strip()
            cid = f"cctv_{len(self.cctv_configs)+1:03d}"
            
            new_cam = {
                "id": cid,
                "name": name,
                "location": "Manual",
                "stream_url": url,
                "enabled": True
            }
            self.cctv_configs.append(new_cam)
            self.save_cctv_configs()
            self.render_cctv_cards()

    def delete_camera(self, cctv_id: str):
        """Menghapus kamera dari konfigurasi"""
        self.cctv_configs = [c for c in self.cctv_configs if c["id"] != cctv_id]
        self.save_cctv_configs()
        self.render_cctv_cards()

    def toggle_auto_record(self):
        """Mulai / Hentikan auto-record scheduler"""
        if self.recorder.auto_scheduler.is_running:
            self.recorder.auto_scheduler.stop()
            messagebox.showinfo("Auto Rekam", "Auto rekam dihentikan.")
        else:
            self.recorder.auto_scheduler.start()
            messagebox.showinfo("Auto Rekam", "Auto rekam dimulai sesuai pengaturan.")
        self.update_ui_state()

    def open_settings_modal(self):
        """Membuka dialog Pengaturan Penyimpanan File & Auto Rekam"""
        settings = load_settings()
        
        modal = ctk.CTkToplevel(self)
        modal.title("Pengaturan Penyimpanan File & Auto Rekam")
        modal.geometry("580 x 680")
        modal.transient(self)
        modal.grab_set()

        # Header Title
        title_lbl = ctk.CTkLabel(
            modal, text="⚙ Pengaturan Sistem & Auto Rekam",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_lbl.pack(anchor="w", padx=25, pady=(15, 10))

        # Scrollable container for settings
        scroll_modal = ctk.CTkScrollableFrame(modal, width=520, height=520)
        scroll_modal.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # ===== SECTION 1: AUTO RECORD SCHEDULE =====
        sec1_lbl = ctk.CTkLabel(
            scroll_modal, text="🔁 Jadwal & Siklus Auto Rekam (Auto Save & Restart)",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#fd7e14"
        )
        sec1_lbl.pack(anchor="w", pady=(5, 5))

        hint_auto = ctk.CTkLabel(
            scroll_modal,
            text="Merekam otomatis per sesi durasi tertentu, auto simpan, lalu otomatis\nstart sendiri lagi sebanyak N kali putaran.",
            font=ctk.CTkFont(size=11), text_color="#aaa", justify="left"
        )
        hint_auto.pack(anchor="w", pady=(0, 10))

        # Durasi per sesi (Menit)
        lbl_auto_dur = ctk.CTkLabel(
            scroll_modal, text="Durasi Rekam per Sesi (Menit) - Auto Simpan Setiap:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_auto_dur.pack(anchor="w", pady=(5, 2))

        entry_auto_dur = ctk.CTkEntry(scroll_modal, height=34)
        entry_auto_dur.pack(fill="x", pady=(0, 2))
        entry_auto_dur.insert(0, str(settings.get("auto_record_duration_minutes", 1)))

        hint_dur_exp = ctk.CTkLabel(
            scroll_modal, text="Contoh: 1 = rekam 1 menit lalu simpan file. Bisa desimal (misal 0.5 = 30 detik).",
            font=ctk.CTkFont(size=10), text_color="#888"
        )
        hint_dur_exp.pack(anchor="w", pady=(0, 10))

        # Jumlah Siklus / Putaran (Repeat Count)
        lbl_auto_rep = ctk.CTkLabel(
            scroll_modal, text="Jumlah Siklus / Putaran (Berapa Kali):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_auto_rep.pack(anchor="w", pady=(5, 2))

        entry_auto_rep = ctk.CTkEntry(scroll_modal, height=34)
        entry_auto_rep.pack(fill="x", pady=(0, 2))
        entry_auto_rep.insert(0, str(settings.get("auto_record_repeat_count", 5)))

        hint_rep = ctk.CTkLabel(
            scroll_modal, text="Contoh: 5 = ulangi 5x lalu berhenti. Masukkan 0 untuk rekam terus menerus tanpa batas.",
            font=ctk.CTkFont(size=10), text_color="#888"
        )
        hint_rep.pack(anchor="w", pady=(0, 10))

        # Jeda Antar Siklus (Detik)
        lbl_auto_int = ctk.CTkLabel(
            scroll_modal, text="Jeda Istirahat Antar Putaran (Detik):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_auto_int.pack(anchor="w", pady=(5, 2))

        entry_auto_int = ctk.CTkEntry(scroll_modal, height=34)
        entry_auto_int.pack(fill="x", pady=(0, 2))
        entry_auto_int.insert(0, str(settings.get("auto_record_interval_seconds", 0)))

        hint_int = ctk.CTkLabel(
            scroll_modal, text="Waktu jeda (detik) sebelum mulai putaran berikutnya. 0 = langsung start.",
            font=ctk.CTkFont(size=10), text_color="#888"
        )
        hint_int.pack(anchor="w", pady=(0, 10))

        # Mode Kamera & Berapa Kamera
        lbl_auto_mode = ctk.CTkLabel(
            scroll_modal, text="Opsi Kamera Target:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_auto_mode.pack(anchor="w", pady=(5, 2))

        mode_options = ["🎲 Random / Acak Kamera", "🔢 Jumlah Tertentu (N Kamera)", "🌐 Semua Kamera"]
        mode_keys = ["random", "count", "all"]
        cur_mode = settings.get("auto_record_camera_mode", "random")
        initial_mode_opt = mode_options[0]
        for opt, k in zip(mode_options, mode_keys):
            if k == cur_mode:
                initial_mode_opt = opt
                break

        combo_mode = ctk.CTkComboBox(scroll_modal, values=mode_options, height=34)
        combo_mode.pack(fill="x", pady=(0, 10))
        combo_mode.set(initial_mode_opt)

        lbl_auto_cnt = ctk.CTkLabel(
            scroll_modal, text="Berapa Kamera yang Direkam (Untuk Mode Random / Jumlah Tertentu):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_auto_cnt.pack(anchor="w", pady=(5, 2))

        entry_auto_cnt = ctk.CTkEntry(scroll_modal, height=34)
        entry_auto_cnt.pack(fill="x", pady=(0, 10))
        entry_auto_cnt.insert(0, str(settings.get("auto_record_camera_count", 3)))

        # Struktur Folder Penyimpanan
        lbl_folder_org = ctk.CTkLabel(
            scroll_modal, text="📁 Struktur Folder Penyimpanan Hasil Rekam:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_folder_org.pack(anchor="w", pady=(5, 2))

        folder_org_options = [
            "📂 Buat Per Folder per 1 Rekam / Sesi (Siklus_1_..., Siklus_2_...)",
            "📁 Utuh 1 Folder Default (Semua Video Digabung Jadi Satu)",
            "🏢 Per Folder Nama Kamera CCTV"
        ]
        folder_org_keys = ["per_session", "single", "per_camera"]
        cur_org = settings.get("folder_organization", "single")
        initial_org_opt = folder_org_options[1]
        for opt, k in zip(folder_org_options, folder_org_keys):
            if k == cur_org:
                initial_org_opt = opt
                break

        combo_folder_org = ctk.CTkComboBox(scroll_modal, values=folder_org_options, height=34)
        combo_folder_org.pack(fill="x", pady=(0, 5))
        combo_folder_org.set(initial_org_opt)

        # ===== SECTION 2: STORAGE =====
        sep_lbl = ctk.CTkLabel(
            scroll_modal, text="────────────────────────────────────────────────",
            font=ctk.CTkFont(size=12), text_color="#444"
        )
        sep_lbl.pack(pady=10)

        sec2_lbl = ctk.CTkLabel(
            scroll_modal, text="📁 Lokasi Penyimpanan Rekaman",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#17a2b8"
        )
        sec2_lbl.pack(anchor="w", pady=(5, 5))

        # 1. Folder Penyimpanan Rekaman
        lbl_rec_frame = ctk.CTkFrame(scroll_modal, fg_color="transparent")
        lbl_rec_frame.pack(fill="x", pady=(5, 2))
        
        lbl_rec = ctk.CTkLabel(
            lbl_rec_frame, text="Folder Penyimpanan Rekaman:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_rec.pack(side="left")

        btn_default_rec = ctk.CTkButton(
            lbl_rec_frame, text="Set Default", width=80, height=22,
            font=ctk.CTkFont(size=11), fg_color="#ffc107", text_color="#000", hover_color="#e0a800",
            command=lambda: entry_rec.delete(0, tk.END) or entry_rec.insert(0, str(RECORDINGS_DIR.resolve()))
        )
        btn_default_rec.pack(side="right")

        frame_rec = ctk.CTkFrame(scroll_modal, fg_color="transparent")
        frame_rec.pack(fill="x", pady=(0, 2))
        
        entry_rec = ctk.CTkEntry(frame_rec, height=34)
        entry_rec.pack(side="left", fill="x", expand=True, padx=(0, 8))
        entry_rec.insert(0, settings.get("recordings_dir", str(RECORDINGS_DIR)))

        def browse_rec():
            folder = filedialog.askdirectory(title="Pilih Folder Penyimpanan Rekaman")
            if folder:
                entry_rec.delete(0, tk.END)
                entry_rec.insert(0, folder)

        btn_browse_rec = ctk.CTkButton(
            frame_rec, text="Browse", width=75, height=34,
            fg_color="#343a40", hover_color="#495057", command=browse_rec
        )
        btn_browse_rec.pack(side="right")

        # 2. Durasi Potong Rekaman / Segment Standar
        lbl_dur = ctk.CTkLabel(
            scroll_modal, text="Durasi Potong File Rekaman Standar / Manual (Menit):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_dur.pack(anchor="w", pady=(10, 2))

        dur_options = ["1 Menit", "2 Menit", "3 Menit", "5 Menit", "15 Menit", "30 Menit", "60 Menit (1 Jam - Standar)", "120 Menit (2 Jam)", "1440 Menit (24 Jam)"]
        dur_values = [1, 2, 3, 5, 15, 30, 60, 120, 1440]
        cur_dur = settings.get("segment_duration_minutes", 60)
        
        initial_val = "60 Menit (1 Jam - Standar)"
        for opt, val in zip(dur_options, dur_values):
            if val == cur_dur:
                initial_val = opt
                break

        combo_dur = ctk.CTkComboBox(scroll_modal, values=dur_options, height=34)
        combo_dur.pack(fill="x", pady=(0, 10))
        combo_dur.set(initial_val)

        # ===== SECTION 3: TENTANG PENGEMBANG (ABOUT) =====
        sep_about = ctk.CTkLabel(
            scroll_modal, text="────────────────────────────────────────────────",
            font=ctk.CTkFont(size=12), text_color="#444"
        )
        sep_about.pack(pady=10)

        sec3_lbl = ctk.CTkLabel(
            scroll_modal, text="ℹ️ Tentang Pengembang",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffc107"
        )
        sec3_lbl.pack(anchor="w", pady=(5, 5))

        about_frame = ctk.CTkFrame(scroll_modal, corner_radius=10, border_width=1, border_color="#495057")
        about_frame.pack(fill="x", pady=(0, 10))

        lbl_app_about = ctk.CTkLabel(
            about_frame, text="CCTV ZIQVA\nby team ziqva.com",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#f8f9fa", justify="center"
        )
        lbl_app_about.pack(padx=15, pady=(12, 4))

        lbl_desc_about = ctk.CTkLabel(
            about_frame, text="Global Stream & Smart Auto Recorder • Multi-Camera Hub",
            font=ctk.CTkFont(size=11), text_color="#adb5bd", justify="center"
        )
        lbl_desc_about.pack(padx=15, pady=(0, 8))

        import webbrowser
        btn_ziqva = ctk.CTkButton(
            about_frame, text="🌐 Kunjungi Website: ziqva.com", height=32,
            fg_color="#fd7e14", hover_color="#e8590c", font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: webbrowser.open("https://ziqva.com")
        )
        btn_ziqva.pack(padx=15, pady=(0, 12))

        # Tombol Aksi Bawah
        btn_action_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=20, pady=(5, 15))

        def collect_and_save():
            rec_val = entry_rec.get().strip()
            if not rec_val:
                messagebox.showerror("Error", "Folder penyimpanan tidak boleh kosong!", parent=modal)
                return False

            sel_text = combo_dur.get()
            selected_minutes = 60
            for opt, val in zip(dur_options, dur_values):
                if opt in sel_text or str(val) in sel_text:
                    selected_minutes = val
                    break

            # Parse Auto Record values
            try:
                auto_dur = max(0.1, float(entry_auto_dur.get().strip()))
            except ValueError:
                auto_dur = 1.0
            try:
                auto_rep = max(0, int(entry_auto_rep.get().strip()))
            except ValueError:
                auto_rep = 5
            try:
                auto_int = max(0, int(entry_auto_int.get().strip()))
            except ValueError:
                auto_int = 0
            try:
                auto_cnt = max(1, int(entry_auto_cnt.get().strip()))
            except ValueError:
                auto_cnt = 3

            sel_mode_text = combo_mode.get()
            selected_mode = "random"
            for opt, k in zip(mode_options, mode_keys):
                if opt == sel_mode_text:
                    selected_mode = k
                    break

            sel_org_text = combo_folder_org.get()
            selected_org = "single"
            for opt, k in zip(folder_org_options, folder_org_keys):
                if opt == sel_org_text:
                    selected_org = k
                    break

            settings["recordings_dir"] = rec_val
            settings["folder_organization"] = selected_org
            settings["segment_duration_minutes"] = selected_minutes
            settings["auto_record_duration_minutes"] = auto_dur
            settings["auto_record_repeat_count"] = auto_rep
            settings["auto_record_interval_seconds"] = auto_int
            settings["auto_record_camera_mode"] = selected_mode
            settings["auto_record_camera_count"] = auto_cnt
            save_settings(settings)
            self.recorder.auto_scheduler.load_from_settings()
            return True

        def save_and_close():
            if collect_and_save():
                messagebox.showinfo("Berhasil", "Pengaturan berhasil disimpan!", parent=modal)
                modal.destroy()
                self.update_ui_state()

        def save_and_start_auto():
            if collect_and_save():
                modal.destroy()
                self.recorder.auto_scheduler.start()
                messagebox.showinfo("Auto Rekam", "Pengaturan disimpan dan Auto Rekam dimulai!")
                self.update_ui_state()

        btn_start_auto = ctk.CTkButton(
            btn_action_frame, text="▶ Simpan & Mulai Auto", fg_color="#28a745", hover_color="#218838",
            font=ctk.CTkFont(weight="bold"), height=36, command=save_and_start_auto
        )
        btn_start_auto.pack(side="right", padx=(8, 0))

        btn_save = ctk.CTkButton(
            btn_action_frame, text="Simpan Pengaturan", fg_color="#fd7e14", hover_color="#e8590c",
            font=ctk.CTkFont(weight="bold"), height=36, command=save_and_close
        )
        btn_save.pack(side="right", padx=(8, 0))

        btn_cancel = ctk.CTkButton(
            btn_action_frame, text="Batal", fg_color="#6c757d", hover_color="#5a6268",
            height=36, command=modal.destroy
        )
        btn_cancel.pack(side="right")

    def open_recordings_folder(self):
        """Membuka folder penyimpanan rekaman di Windows File Explorer"""
        st = load_settings()
        rec_path = Path(st.get("recordings_dir", str(RECORDINGS_DIR)))
        rec_path.mkdir(parents=True, exist_ok=True)
        os.startfile(rec_path)

    def schedule_ui_update(self):
        """Dipanggil dari engine saat ada update status (thread-safe)"""
        self.after(0, self.update_ui_state)

    def update_ui_state(self):
        """Update tampilan status real-time pada card & header"""
        statuses = self.recorder.get_all_status()
        active_count = 0
        recording_ids = []

        for cid, widgets in self.card_widgets.items():
            st = statuses.get(cid)
            card = widgets.get("card")
            status_ind = widgets["status_indicator"]
            info_lbl = widgets["info_lbl"]
            btn_rec = widgets["btn_rec"]

            if st and st.is_recording:
                active_count += 1
                recording_ids.append(cid)
                status_ind.configure(text="🔥 ● RECORDING (PINNED ATAS)", text_color="#28a745")
                btn_rec.configure(text="Stop", fg_color="#dc3545", hover_color="#c82333")
                size_str = CCTVRecorder.format_bytes(st.bytes_recorded)
                info_lbl.configure(text=f"File: {st.current_file}\nSize: {size_str}")
                if card:
                    card.configure(border_color="#28a745", border_width=2)
            elif st and st.is_error:
                status_ind.configure(text=f"● ERROR (Retry {st.retry_count})", text_color="#dc3545")
                btn_rec.configure(text="Start", fg_color="#28a745", hover_color="#218838")
                info_lbl.configure(text=f"Error: {st.error_msg}")
                if card:
                    card.configure(border_color="#dc3545", border_width=1)
            else:
                status_ind.configure(text="● IDLE", text_color="#6c757d")
                btn_rec.configure(text="Start", fg_color="#28a745", hover_color="#218838")
                info_lbl.configure(text="File: - | Size: 0 MB")
                if card:
                    card.configure(border_color="#343a40", border_width=1)

        # Dinamis urutkan kamera yang sedang merekam ke urutan paling atas
        rec_sig = ",".join(sorted(recording_ids))
        if getattr(self, "_last_rec_sig", None) != rec_sig:
            self._last_rec_sig = rec_sig
            rec_set = set(recording_ids)
            sorted_items = sorted(
                self.card_widgets.items(),
                key=lambda kv: (0 if kv[0] in rec_set else 1, kv[1].get("orig_idx", 0))
            )
            for new_idx, (_, w) in enumerate(sorted_items):
                c_frame = w.get("card")
                if c_frame:
                    c_frame.grid(row=new_idx // 2, column=new_idx % 2, sticky="ew", padx=10, pady=10)

        # Update Header
        self.total_status_label.configure(text=f"Total: {len(self.cctv_configs)} Kamera | {active_count} Merekam")

        # Update Auto Record status
        try:
            ar = self.recorder.auto_scheduler.get_status()
            if ar["is_running"]:
                self.btn_auto_record.configure(text="⏹ Stop Auto Rekam", fg_color="#dc3545", hover_color="#c82333")
                tot = ar['total_cycles'] if ar['total_cycles'] > 0 else '∞'
                rem_m = ar['remaining_seconds'] // 60
                rem_s = ar['remaining_seconds'] % 60
                state_txt = "Waiting" if ar["state"] == "waiting" else "Rec"
                self.auto_status_label.configure(
                    text=f"Auto [{state_txt}]: {ar['current_cycle']}/{tot} ({rem_m:02d}:{rem_s:02d})\n{ar['camera_mode'].title()} ({ar['camera_count']} Cam)",
                    text_color="#28a745"
                )
            else:
                self.btn_auto_record.configure(text="🔁 Start Auto Rekam", fg_color="#fd7e14", hover_color="#e8590c")
                self.auto_status_label.configure(text="Auto Rekam: IDLE", text_color="#aaa")
        except Exception:
            pass

        # Update Disk usage
        try:
            usage = CCTVRecorder.get_disk_usage()
            free_gb = usage["free"] / (1024 ** 3)
            self.disk_label.configure(text=f"Disk Free: {free_gb:.1f} GB")
        except Exception:
            pass

    def start_status_loop(self):
        """Loop refresh status setiap 3 detik"""
        self.update_ui_state()
        self.after(3000, self.start_status_loop)


if __name__ == "__main__":
    app = CCTVApp()
    app.mainloop()
