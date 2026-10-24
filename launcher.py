"""Windows launcher for the bundled browser dashboard."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import traceback
import webbrowser

from app_paths import DATA_DIR, RESOURCE_DIR, FFMPEG
from version import APP_VERSION


def self_test(output):
    """Exercise bundled resources without accessing public camera streams."""
    from web_server import app, recorder
    from playwright.sync_api import sync_playwright
    from recorder_engine import load_settings, save_settings
    result = {}
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"<html" in response.data.lower()
        result["dashboard"] = response.status_code
    settings = load_settings()
    save_settings(settings)
    assert json.loads((DATA_DIR / "app_settings.json").read_text(encoding="utf-8")) == settings
    result["settings_write"] = True
    result["cameras"] = len(recorder.configs) if hasattr(recorder, "configs") else len(json.loads((DATA_DIR / "cctv_streams.json").read_text(encoding="utf-8")))
    video = DATA_DIR / "self-test.mp4"
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=black:s=160x120:r=5", "-t", "1", str(video)],
                   check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert video.stat().st_size > 0
    result["ffmpeg_recording"] = True
    video.unlink()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("<title>CCTV test</title>")
        assert page.title() == "CCTV test"
        browser.close()
    result["scanner_browser"] = True
    result["data_dir"] = str(DATA_DIR)
    Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")


def main():
    import tkinter as tk
    from tkinter import messagebox
    from werkzeug.serving import make_server
    from web_server import app, recorder

    root = tk.Tk()
    root.title("CCTV ZIQVA")
    root.geometry("520x330")
    root.resizable(False, False)
    root.configure(bg="#0b1220")
    root.option_add("*Font", ("Segoe UI", 10))
    icon = RESOURCE_DIR / "cctv_icon.ico"
    if icon.exists():
        root.iconbitmap(str(icon))
    # OS chooses a free loopback port; independent of an existing source instance.
    server = make_server("127.0.0.1", 0, app, threaded=True)
    url = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    # Launcher bergaya dark agar konsisten dengan dashboard web.
    shell = tk.Frame(root, bg="#111b2e", highlightthickness=1, highlightbackground="#263653")
    shell.pack(fill="both", expand=True, padx=14, pady=14)

    header = tk.Frame(shell, bg="#111b2e")
    header.pack(fill="x", padx=24, pady=(22, 8))
    brand = tk.Frame(header, bg="#111b2e")
    brand.pack(side="left")
    tk.Label(brand, text="●", fg="#22d3ee", bg="#111b2e", font=("Segoe UI", 22, "bold")).pack(side="left", padx=(0, 9))
    title_box = tk.Frame(brand, bg="#111b2e")
    title_box.pack(side="left")
    tk.Label(title_box, text="CCTV ZIQVA", fg="#f8fafc", bg="#111b2e", font=("Segoe UI", 19, "bold")).pack(anchor="w")
    tk.Label(title_box, text=f"Multi-camera recording hub  •  v{APP_VERSION}", fg="#94a3b8", bg="#111b2e", font=("Segoe UI", 9)).pack(anchor="w")

    tk.Frame(shell, height=1, bg="#263653").pack(fill="x", padx=24, pady=(4, 14))

    body = tk.Frame(shell, bg="#111b2e")
    body.pack(fill="x", padx=24)
    tk.Label(body, text="Dashboard berjalan di browser", fg="#e2e8f0", bg="#111b2e", font=("Segoe UI", 12, "bold")).pack(anchor="w")
    tk.Label(body, text="Biarkan launcher ini terbuka selama proses perekaman.", fg="#94a3b8", bg="#111b2e", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 12))

    status = tk.Frame(body, bg="#0b2b2c", highlightthickness=1, highlightbackground="#155e63")
    status.pack(fill="x", pady=(0, 16))
    tk.Label(status, text="●  SERVER AKTIF", fg="#34d399", bg="#0b2b2c", font=("Segoe UI", 9, "bold")).pack(side="left", padx=12, pady=8)
    tk.Label(status, text=f"127.0.0.1:{server.server_port}", fg="#7dd3fc", bg="#0b2b2c", font=("Consolas", 9)).pack(side="right", padx=12, pady=8)

    actions = tk.Frame(body, bg="#111b2e")
    actions.pack(fill="x")
    tk.Button(actions, text="  Buka Dashboard  ", command=lambda: webbrowser.open(url), bg="#0ea5e9", activebackground="#0284c7", fg="white", activeforeground="white", relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 10, "bold"), padx=16, pady=9).pack(side="left", fill="x", expand=True)

    def close():
        if not messagebox.askyesno("Tutup CCTV ZIQVA", "Hentikan perekaman dan tutup aplikasi?", parent=root):
            return
        recorder.stop_all()
        server.shutdown()
        root.destroy()

    tk.Button(actions, text="Hentikan & Tutup", command=close, bg="#3b1d2a", activebackground="#7f1d35", fg="#fda4af", activeforeground="white", relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), padx=12, pady=9).pack(side="left", padx=(10, 0))
    tk.Label(shell, text="CCTV ZIQVA  •  Rekaman aman di perangkat Anda", fg="#64748b", bg="#111b2e", font=("Segoe UI", 8)).pack(side="bottom", pady=(18, 14))
    root.protocol("WM_DELETE_WINDOW", close)
    # Jangan membuka Chrome otomatis setiap kali launcher dijalankan.
    # Pengguna bisa membuka dashboard lewat tombol agar tidak muncul popup/tab
    # baru tanpa sengaja ketika aplikasi restart atau selesai update.
    root.mainloop()


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
            self_test(sys.argv[2])
        else:
            main()
    except Exception:
        error = traceback.format_exc()
        (DATA_DIR / "startup-error.log").write_text(error, encoding="utf-8")
        if "--self-test" not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Aplikasi gagal dibuka. Detail: {DATA_DIR / 'startup-error.log'}", "CCTV ZIQVA", 16)
        sys.exit(1)
