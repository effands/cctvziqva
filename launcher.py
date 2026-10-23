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
    root.geometry("440x210")
    root.resizable(False, False)
    icon = RESOURCE_DIR / "cctv_icon.ico"
    if icon.exists():
        root.iconbitmap(str(icon))
    # OS chooses a free loopback port; independent of an existing source instance.
    server = make_server("127.0.0.1", 0, app, threaded=True)
    url = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    tk.Label(root, text=f"CCTV ZIQVA v{APP_VERSION}", font=("Segoe UI", 18, "bold")).pack(pady=(18, 6))
    tk.Label(root, text="Dashboard berjalan di browser.\nBiarkan jendela ini terbuka selama merekam.").pack()
    tk.Button(root, text="Buka Dashboard", command=lambda: webbrowser.open(url), width=26).pack(pady=10)

    def close():
        if not messagebox.askyesno("Tutup CCTV ZIQVA", "Hentikan perekaman dan tutup aplikasi?", parent=root):
            return
        recorder.stop_all()
        server.shutdown()
        root.destroy()

    tk.Button(root, text="Hentikan dan Tutup", command=close, width=26).pack()
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
