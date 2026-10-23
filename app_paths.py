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
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(RESOURCE_DIR / "browsers")


initialize_data()
FFMPEG = str(RESOURCE_DIR / "bin" / "ffmpeg.exe") if FROZEN else "ffmpeg"
