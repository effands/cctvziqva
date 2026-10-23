import json
import pathlib
import sys

project_dir = pathlib.Path(__file__).parent.resolve()

settings_file = project_dir / "app_settings.json"

recordings_dir = pathlib.Path.home() / "Videos" / "CCTV Recordings"
backup_dir = pathlib.Path.home() / "Videos" / "CCTV Backup"

defaults = {
    "recordings_dir": str(recordings_dir),
    "backup_dir": str(backup_dir),
    "segment_duration_minutes": 60,
    "saved_website_urls": [
        "https://cctv.jogjaprov.go.id/",
        "https://cctv.malangkota.go.id/sebaran-cctv",
        "https://dishub.kedirikota.go.id/live-streaming-atcs/",
        "https://atcs.denpasarkota.go.id/",
        "https://www.skylinewebcams.com/en/webcam.html"
    ]
}

data = {}
if settings_file.exists():
    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)

# Pertahankan pilihan pengguna; isi hanya pengaturan yang belum ada.
for key, value in defaults.items():
    data.setdefault(key, value)

recordings_dir = pathlib.Path(data["recordings_dir"])
backup_dir = pathlib.Path(data["backup_dir"])
recordings_dir.mkdir(parents=True, exist_ok=True)
backup_dir.mkdir(parents=True, exist_ok=True)

with open(settings_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("[OK] Konfigurasi disimpan.")
print("     Rekaman  :", recordings_dir)
print("     Backup   :", backup_dir)
