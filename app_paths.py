"""Separate bundled resources from persistent, per-user application data."""
import json
import os
from pathlib import Path
import shutil
import sys

FROZEN = getattr(sys, "frozen", False)
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DATA_DIR = (Path(os.environ.get("CCTV_DATA_DIR") or
                 str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CCTV ZIQVA"))
            if FROZEN else Path(__file__).resolve().parent)


def initialize_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not FROZEN:
        return
    for name in ("cctv_streams.json", "cctv_offline.json", "app_settings.json"):
        destination = DATA_DIR / name
        source = RESOURCE_DIR / "defaults" / name
        if not destination.exists() and source.exists():
            if name == "app_settings.json":
                settings = json.loads(source.read_text(encoding="utf-8"))
                settings["recordings_dir"] = str(Path.home() / "Videos" / "CCTV Recordings")
                settings["backup_dir"] = str(Path.home() / "Videos" / "CCTV Backup")
                destination.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
            else:
                shutil.copy2(source, destination)
    # Tambahkan kamera baru dari installer ke daftar pengguna tanpa menimpa
    # kamera custom atau perubahan konfigurasi yang sudah ada.
    default_cameras = RESOURCE_DIR / "defaults" / "cctv_streams.json"
    user_cameras = DATA_DIR / "cctv_streams.json"
    if default_cameras.exists() and user_cameras.exists():
        try:
            defaults = json.loads(default_cameras.read_text(encoding="utf-8"))
            current = json.loads(user_cameras.read_text(encoding="utf-8"))
            known_ids = {str(cam.get("id")) for cam in current if cam.get("id")}
            additions = [cam for cam in defaults if cam.get("id") and str(cam["id"]) not in known_ids]
            if additions:
                current.extend(additions)
                user_cameras.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
        except (OSError, ValueError, TypeError):
            pass
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(RESOURCE_DIR / "browsers")


initialize_data()
FFMPEG = str(RESOURCE_DIR / "bin" / "ffmpeg.exe") if FROZEN else "ffmpeg"
