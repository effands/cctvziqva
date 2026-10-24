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
        "https://www.skylinewebcams.com/en/webcam.html",
        "https://www.mlit.go.jp/road/bosai/LIVEcamera.html",
        "https://highwaytraffic.go.th/DOHMobile/Modules/CCTV.aspx",
        "https://traffic.bangkok.go.th/",
        "https://transport.mos.ru/mostrans/cameras",
        "https://onemotoring.lta.gov.sg/content/onemotoring/home/driving/traffic_information.html",
        "https://nationalhighways.co.uk/roads-and-travel/live-travel-updates/",
        "https://www.livetraffic.com/",
        "https://www.fl511.com/",
        "https://opencam.live/",
        "https://liikennetilanne.fintraffic.fi/kartta/?lang=en",
        "https://www.asfinag.at/verkehr-sicherheit/verkehrsinformationen/webcams/",
        "https://www.kollatrafiken.se/vagkameror",
        "https://promet.si/sl/kamere",
        "https://www.hak.hr/en#traffic-cameras",
        "https://www.dars.si/Traffic_information/Web_cameras",
        "https://www.road.is/",
        "https://www.nzta.govt.nz/traffic-and-travel-information/traffic-cameras/",
        "https://klccc.dbkl.gov.my/",
        "https://www.llm.gov.my/awam/cctv1",
        "https://zatca.gov.sa/en/pages/live-camera.aspx",
        "https://www.i-traffic.co.za/map",
        "https://rodovias.grupoccr.com.br/riosp/cameras-ao-vivo/",
        "https://ledrium.live/",
        "https://traffic.com.gh/",
        "https://www.giaothong.hochiminhcity.gov.vn/",
        "https://mmda-redesign.vercel.app/",
        "https://ccc.rajasthan.gov.in/",
        "https://amanroads.gov.ae/",
        "https://trafficvision.live/map",
        "https://openwebcamdb.com/"
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
