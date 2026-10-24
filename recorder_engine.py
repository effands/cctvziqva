"""
CCTV Multi-Stream Recorder
============================
Core recording engine menggunakan FFmpeg untuk merekam
multiple HLS/RTSP stream secara paralel dengan fitur:
- Multi-stream recording (concurrent)
- Auto-segmentasi per jam
- Backup otomatis
- Retry on failure
- Progress logging
"""

import subprocess
import threading
import time
import os
import json
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field


# === Konfigurasi ===
from app_paths import DATA_DIR, FFMPEG
BASE_DIR = DATA_DIR
RECORDINGS_DIR = BASE_DIR / "recordings"
BACKUP_DIR = BASE_DIR / "backup"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "cctv_streams.json"
OFFLINE_CONFIG_FILE = BASE_DIR / "cctv_offline.json"
SETTINGS_FILE = BASE_DIR / "app_settings.json"

SEGMENT_DURATION_MINUTES = 60   # potong setiap 60 menit
import random

MAX_RETRY_COUNT = 5              # max retry per stream
RETRY_DELAY_SECONDS = 10        # jeda sebelum retry
FFMPEG_TIMEOUT_SECONDS = 30     # timeout koneksi FFmpeg

# Buat direktori jika belum ada
for d in [RECORDINGS_DIR, BACKUP_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def load_settings() -> dict:
    default_settings = {
        "recordings_dir": str(RECORDINGS_DIR),
        "backup_dir": str(BACKUP_DIR),
        "segment_duration_minutes": 60,  # Default segment durasi rekam (menit)
        "folder_organization": "single", # 'single' (gabung jadi 1 folder) atau 'per_session' (buat subfolder per sesi/putaran rekam) atau 'per_camera' (per nama CCTV)
        "auto_record_enabled": False,
        "auto_record_duration_minutes": 1,   # Durasi per sesi rekam (menit)
        "auto_record_repeat_count": 5,       # Berapa kali putaran rekam, misal 5x
        "auto_record_interval_seconds": 0,   # Jeda antar putaran (detik)
        "auto_record_camera_mode": "random", # 'all', 'random', 'count', 'selected'
        "auto_record_camera_count": 3,       # Berapa kamera yang direkam jika mode random/count
        "auto_record_area": "all",          # 'all', 'malang', 'surabaya', 'yogyakarta', 'india'
        "auto_record_selected_cams": [],     # Daftar ID kamera jika mode selected
        "auto_record_geo_scope": "world",   # world, region, country, city
        "auto_record_geo_value": "",
        "saved_website_urls": [
            "http://36.66.208.101:5000/",
            "https://cctvsurabaya.24hour.id/",
            "https://dishub.bandungkab.go.id/cctv/",
            "https://atcs.bandungbaratkab.go.id/",
            "https://smartcity.cimahikota.go.id/cctv",
            "https://cctv.jogjaprov.go.id/",
            "https://cctv.malangkota.go.id/sebaran-cctv",
            "https://dishub.kedirikota.go.id/live-streaming-atcs/",
            "https://atcs.denpasarkota.go.id/",
            "https://www.skylinewebcams.com/en/webcam.html",
            "https://www.aqi.in/live-camera/india/tamil-nadu/tiruppur/kuppuchipalayam",
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
            "https://openwebcamdb.com/",
            "https://live.traffictw.com/",
            "https://focustaiwan.net/roads/national",
            "https://data.gov.hk/en-data/dataset/hk-td-tis_2-traffic-snapshot-images",
            "https://www.td.gov.hk/en/transport_in_hong_kong/its/its_achievements/closed_circuit_television_images_on_the_internet/index.html",
            "https://www.c5.cdmx.gob.mx/",
            "https://ameq.live/",
            "https://codigoqro.mx/trafico",
            "https://www.bayerninfo.de/en/",
            "https://www.verkehrsinfo-bw.de/verkehrskameras",
            "https://www.bison-fute.gouv.fr/maintenant.html",
            "https://www.vinci-autoroutes.com/fr/autoroutes-temps-reel/?filter=webcams",
            "https://www.autostrade.it/it/webcam",
            "https://www.muoversintoscana.it/telecamere",
              "https://webcams.venetostrade.it/",
              "https://www.dgt.es/conoce-el-estado-del-trafico/camaras-de-trafico/",
              "https://servicos.infraestruturasdeportugal.pt/pt-pt/viajar-na-estrada/transito-em-tempo-real",
              "https://www.viaverde.pt/ferramentas/informacao-de-transito",
              "https://511on.ca/",
              "https://topis.seoul.go.kr/map/openCctvMap.do",
              "https://www.utic.go.kr/main/main.do",
              "https://www.rwsverkeersinfo.nl/cameras/",
              "https://trafiroutes.wallonie.be/",
              "https://drogi.gddkia.gov.pl/",
              "https://vif.lu.ch/webcams",
              "https://ibb.istanbul/tum-hizmetler/e-belediye-hizmetleri/e-bilgi/kameralar/",
              "https://argosatlas.com/camaras/argentina/",
              "https://www.alertaperu.org.pe/",
              "https://orbisviews.com/",
              "https://www.bkom.cz/traffic-cameras",
              "https://www.doprava-brno.cz/",
              "https://www.trafficthess.imet.gr/",
              "https://www.iroads.no/",
              "https://veikamera.no/",
              "https://trafikkort.vejdirektoratet.dk/prototype/index.html",
              "https://www.gov.ie/en/department-of-transport/services/view-maps-and-gis-content-from-transport-infrastructure-ireland/",
              "https://www.sba.bg/cctv",
              "https://www.amss.org.rs/na-putu/stanje-na-putu/strana/policijske-kamere",
              "https://www.infobuz.ro/en/traffic-romania/"
        ]
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    return default_settings

def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / f"recorder_{datetime.now():%Y%m%d}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CCTVRecorder")


@dataclass
class StreamStatus:
    """Status real-time setiap stream"""
    cctv_id: str
    name: str
    is_recording: bool = False
    is_error: bool = False
    error_msg: str = ""
    retry_count: int = 0
    start_time: Optional[datetime] = None
    current_file: str = ""
    total_files: int = 0
    bytes_recorded: int = 0
    process: Optional[subprocess.Popen] = None


class AutoRecordScheduler:
    """
    Scheduler untuk perekaman otomatis bersiklus (auto-save & restart cycle).
    Fitur:
    - Merekam dengan durasi tertentu (misal 1 menit, 5 menit)
    - Otomatis menyimpan file setelah durasi tercapai
    - Otomatis restart sesi berikutnya sesuai jumlah siklus (misal 5x, atau tak terbatas)
    - Opsi kamera: Semua kamera, N kamera tertentu, atau N kamera random / acak
    - Jeda antar siklus (istirahat)
    - Thread-safe dengan status real-time untuk Web Dashboard & Desktop GUI
    """
    def __init__(self, recorder: 'CCTVRecorder'):
        self.recorder = recorder
        self.is_running = False
        self.state = "idle"  # idle, recording, waiting, completed, stopped, error
        self.current_cycle = 0
        self.total_cycles = 5
        self.duration_minutes = 1.0
        self.interval_seconds = 0
        self.camera_mode = "random"  # 'all', 'random', 'count', 'selected'
        self.camera_count = 3
        self.selected_cams = []
        self.active_camera_ids = []
        self.cycle_start_time: Optional[datetime] = None
        self.cycle_end_time: Optional[datetime] = None

        self._sys_rng = random.SystemRandom()
        self._used_random_ids = set()
        self._last_cycle_ids = set()
        self._strata_queue = []

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.load_from_settings()

    def load_from_settings(self):
        """Memuat konfigurasi dari app_settings.json"""
        st = load_settings()
        try:
            self.duration_minutes = max(0.1, float(st.get("auto_record_duration_minutes", 1)))
        except (ValueError, TypeError):
            self.duration_minutes = 1.0
        try:
            self.total_cycles = max(0, int(st.get("auto_record_repeat_count", 5)))
        except (ValueError, TypeError):
            self.total_cycles = 5
        try:
            self.interval_seconds = max(0, int(st.get("auto_record_interval_seconds", 0)))
        except (ValueError, TypeError):
            self.interval_seconds = 0
        self.camera_mode = str(st.get("auto_record_camera_mode", "random"))
        try:
            self.camera_count = max(1, int(st.get("auto_record_camera_count", 3)))
        except (ValueError, TypeError):
            self.camera_count = 3
        self.selected_cams = list(st.get("auto_record_selected_cams", []))
        self.area_filter = str(st.get("auto_record_area", "all")).strip().lower() or "all"
        self.geo_scope = str(st.get("auto_record_geo_scope", "world")).strip().lower() or "world"
        self.geo_value = str(st.get("auto_record_geo_value", "")).strip()

    def start(self, config_override: Optional[dict] = None):
        """Memulai auto record scheduler"""
        with self._lock:
            if self.is_running:
                logger.warning("AutoRecordScheduler sudah aktif.")
                return

            self.load_from_settings()
            if config_override:
                if "duration_minutes" in config_override:
                    try:
                        self.duration_minutes = max(0.1, float(config_override["duration_minutes"]))
                    except (ValueError, TypeError):
                        pass
                if "repeat_count" in config_override:
                    try:
                        self.total_cycles = max(0, int(config_override["repeat_count"]))
                    except (ValueError, TypeError):
                        pass
                if "interval_seconds" in config_override:
                    try:
                        self.interval_seconds = max(0, int(config_override["interval_seconds"]))
                    except (ValueError, TypeError):
                        pass
                if "camera_mode" in config_override:
                    self.camera_mode = str(config_override["camera_mode"])
                if "camera_count" in config_override:
                    try:
                        self.camera_count = max(1, int(config_override["camera_count"]))
                    except (ValueError, TypeError):
                        pass
                if "selected_cams" in config_override:
                    self.selected_cams = list(config_override["selected_cams"])
                if "area_filter" in config_override:
                    self.area_filter = str(config_override["area_filter"]).strip().lower() or "all"

            self.is_running = True
            self.state = "starting"
            self.current_cycle = 0
            self._stop_event.clear()

            self._thread = threading.Thread(
                target=self._run_loop,
                name="AutoRecordSchedulerThread",
                daemon=True
            )
            self._thread.start()
            logger.info(f"AutoRecordScheduler aktif: {self.total_cycles}x @ {self.duration_minutes}m (Mode: {self.camera_mode}, {self.camera_count} cam)")

    def stop(self):
        """Menghentikan auto record scheduler"""
        self._stop_event.set()
        with self._lock:
            self.is_running = False
            self.state = "stopped"
            active_ids = list(self.active_camera_ids)
            self.active_camera_ids = []

        for cid in active_ids:
            try:
                self.recorder.stop_stream(cid)
            except Exception:
                pass

        self.recorder._notify_update()
        logger.info("AutoRecordScheduler dinonaktifkan.")

    def _pick_random_full_range(self, valid_cams: list, k: int) -> list:
        """
        Memilih k kamera secara acak merata (Stratified + OS Entropy Non-Repeating Deck)
        dari halaman pertama (indeks 0) hingga halaman paling akhir (indeks N-1),
        sehingga tidak pernah berkutat di kamera/halaman yang sama.
        """
        total = len(valid_cams)
        if k >= total:
            shuffled = list(valid_cams)
            self._sys_rng.shuffle(shuffled)
            return shuffled

        # Reset deck jika sisa kamera yang belum pernah dipilih < k
        remaining_unused = [c for c in valid_cams if c.get("id") not in self._used_random_ids]
        if len(remaining_unused) < k:
            self._used_random_ids = set(self._last_cycle_ids) if total > k else set()

        # Bagi seluruh daftar dari indeks 0 sampai indeks terakhir menjadi segmen/strata
        # agar pemilihan selalu menjangkau halaman awal, tengah, hingga halaman paling akhir
        num_strata = min(total, max(k * 3, 12))
        strata_buckets = [[] for _ in range(num_strata)]
        for idx, cam in enumerate(valid_cams):
            s_idx = min(num_strata - 1, int(idx * num_strata / total))
            strata_buckets[s_idx].append((idx, cam))

        picked = []
        picked_ids = set()

        while len(picked) < k:
            # Bersihkan indeks strata lama yang melebihi num_strata saat ini (mencegah IndexError saat k berubah dari N ke 1)
            self._strata_queue = [idx for idx in self._strata_queue if 0 <= idx < num_strata]
            if not self._strata_queue:
                self._strata_queue = list(range(num_strata))
                self._sys_rng.shuffle(self._strata_queue)

            # Ambil segmen berikutnya dari antrean segmen acak
            s_idx = self._strata_queue.pop(0) % num_strata
            bucket = strata_buckets[s_idx]
            candidates = [
                (idx, c) for (idx, c) in bucket
                if c.get("id") not in self._used_random_ids and c.get("id") not in picked_ids
            ]
            if not candidates:
                # Fallback ke seluruh daftar yang belum dipilih
                candidates = [
                    (idx, c) for idx, c in enumerate(valid_cams)
                    if c.get("id") not in self._used_random_ids and c.get("id") not in picked_ids
                ]
            if not candidates:
                candidates = [
                    (idx, c) for idx, c in enumerate(valid_cams)
                    if c.get("id") not in picked_ids
                ]
            if not candidates:
                break

            chosen_idx, chosen_cam = self._sys_rng.choice(candidates)
            cid = chosen_cam.get("id")
            picked.append(chosen_cam)
            picked_ids.add(cid)
            self._used_random_ids.add(cid)

            page_no = (chosen_idx // 12) + 1
            total_pages = (total + 11) // 12
            logger.info(
                f"[RandomPick] Terpilih: {chosen_cam.get('name')} ({chosen_cam.get('city', chosen_cam.get('location', ''))}) "
                f"- Indeks #{chosen_idx + 1}/{total} (Hal {page_no}/{total_pages})"
            )

        self._last_cycle_ids = picked_ids
        return picked

    def _ensure_verified_online_batch(self, valid_cams: list, initial_picks: list, target_count: int) -> list:
        """
        Memastikan seluruh kamera yang akan direkam benar-benar AKTIF (ONLINE) sebelum mulai rekam.
        Jika ada kamera kandidat yang OFFLINE, langsung dialihkan ke kamera lain yang ONLINE
        sampai jumlah kamera aktif mencapai target_count (misal: minta 5 tetap dapat 5 kamera online).
        """
        verified = []
        tried_ids = set()

        for cam in initial_picks:
            if self._stop_event.is_set():
                break
            cid = cam.get("id")
            tried_ids.add(cid)
            url = cam.get("stream_url", "")
            if self.recorder.is_stream_online(url, timeout=6):
                verified.append(cam)
            else:
                logger.warning(
                    f"[AutoRecord-Failover] Kamera '{cam.get('name')}' ({cid}) terdeteksi OFFLINE saat pre-check "
                    f"-> dipindahkan ke Menu CCTV OFF & dialihkan ke kamera lain yang ONLINE..."
                )
                self.recorder.move_to_offline(cid, reason="Offline saat pre-check perekaman")

        # Jika ada yang offline sehingga jumlah < target_count, cari pengganti yang ONLINE
        max_attempts = min(len(valid_cams), max(target_count * 8, 40))
        attempts = 0
        while len(verified) < target_count and attempts < max_attempts and not self._stop_event.is_set():
            attempts += 1
            remaining_pool = [c for c in valid_cams if c.get("id") not in tried_ids]
            if not remaining_pool:
                break
            replacement_list = self._pick_random_full_range(remaining_pool, 1)
            if not replacement_list:
                break
            cand = replacement_list[0]
            cid = cand.get("id")
            tried_ids.add(cid)
            if self.recorder.is_stream_online(cand.get("stream_url", ""), timeout=6):
                verified.append(cand)
                logger.info(
                    f"[AutoRecord-Failover] Berhasil dialihkan ke CCTV ONLINE: '{cand.get('name')}' ({cand.get('city', '')}) "
                    f"[{len(verified)}/{target_count}]"
                )
            else:
                logger.warning(
                    f"[AutoRecord-Failover] Kandidat pengganti '{cand.get('name')}' juga OFFLINE -> dipindahkan ke Menu CCTV OFF..."
                )
                self.recorder.move_to_offline(cid, reason="Offline saat pre-check perekaman")

        return verified

    def _pick_single_online_replacement(self, valid_cams: list, exclude_ids: set, deadline: Optional[datetime] = None) -> Optional[dict]:
        """Cari 1 kamera pengganti yang terverifikasi ONLINE saat ada kamera yang putus di tengah perekaman."""
        pool = [c for c in valid_cams if c.get("id") not in exclude_ids]
        if not pool:
            return None
        for _ in range(min(len(pool), 12)):
            if self._stop_event.is_set():
                return None
            if deadline and (deadline - datetime.now()).total_seconds() <= 6:
                return None
            cands = self._pick_random_full_range(pool, 1)
            if not cands:
                break
            cand = cands[0]
            cid = cand.get("id")
            exclude_ids.add(cid)
            pool = [c for c in pool if c.get("id") != cid]
            if self.recorder.is_stream_online(cand.get("stream_url", ""), timeout=4):
                return cand
            else:
                self.recorder.move_to_offline(cid, reason="Offline saat pencarian pengganti")
        return None

    def _load_valid_cams(self) -> list:
        all_cams = []
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    all_cams = json.load(f)
            except Exception:
                all_cams = []
        return [c for c in all_cams if c.get("enabled", True) and c.get("stream_url")]

    def _pick_cameras(self) -> list:
        valid_cams = self._load_valid_cams()
        if not valid_cams:
            return []

        # Filter vóór random/count/all zodat ook failover binnen dezelfde regio blijft.
        area = self.area_filter
        area_aliases = {
            "malang": ("malang", "malangkota"),
            "surabaya": ("surabaya", "suroboyo"),
            "yogyakarta": ("yogyakarta", "jogja", "jogjakarta"),
            "india": ("india", "tiruppur", "tamil nadu", "tamil-nadu"),
        }
        if area in area_aliases:
            tokens = area_aliases[area]
            scoped = []
            for cam in valid_cams:
                haystack = " ".join(str(cam.get(k, "")) for k in ("name", "location", "city", "country", "source")).lower()
                if any(token in haystack for token in tokens):
                    scoped.append(cam)
            valid_cams = scoped
            if not valid_cams:
                logger.warning(f"Area auto-rekam '{area}' tidak memiliki kamera aktif; tidak ada kamera dipilih.")
                return []

        scope = self.geo_scope
        value = self.geo_value.casefold()
        if scope != "world" and value:
            region_map = {
                "asia": ("india", "indonesia", "japan", "china", "singapore", "malaysia", "thailand"),
                "europe": ("germany", "france", "italy", "spain", "united kingdom", "uk"),
                "americas": ("usa", "united states", "canada", "brazil", "mexico"),
                "africa": ("south africa", "nigeria", "kenya"),
                "oceania": ("australia", "new zealand"),
            }
            filtered = []
            for cam in valid_cams:
                country = str(cam.get("country", "")).casefold()
                city = str(cam.get("city", cam.get("location", ""))).casefold()
                haystack = " ".join(str(cam.get(k, "")) for k in ("name", "location", "city", "country", "source")).casefold()
                if scope == "country" and value in country:
                    filtered.append(cam)
                elif scope == "city" and value in city:
                    filtered.append(cam)
                elif scope == "region" and any(token in haystack for token in region_map.get(value, (value,))):
                    filtered.append(cam)
            valid_cams = filtered
            if not valid_cams:
                logger.warning(f"Geo filter '{scope}:{self.geo_value}' tidak memiliki kamera aktif.")
                return []

        mode = self.camera_mode
        if mode == "all":
            return valid_cams
        elif mode == "random":
            k = max(1, min(self.camera_count, len(valid_cams)))
            raw_picks = self._pick_random_full_range(valid_cams, k)
            return self._ensure_verified_online_batch(valid_cams, raw_picks, k)
        elif mode == "count":
            k = max(1, min(self.camera_count, len(valid_cams)))
            raw_picks = valid_cams[:k]
            return self._ensure_verified_online_batch(valid_cams, raw_picks, k)
        elif mode == "selected":
            sel = [c for c in valid_cams if c.get("id") in self.selected_cams]
            if not sel:
                k = max(1, min(self.camera_count, len(valid_cams)))
                raw_picks = valid_cams[:k]
                return self._ensure_verified_online_batch(valid_cams, raw_picks, k)
            return self._ensure_verified_online_batch(valid_cams, sel, len(sel))
        else:
            k = max(1, min(self.camera_count, len(valid_cams)))
            raw_picks = self._pick_random_full_range(valid_cams, k)
            return self._ensure_verified_online_batch(valid_cams, raw_picks, k)

    def _run_loop(self):
        self.current_cycle = 0

        # Jika masih ada stream lain berjalan saat awal mulai, hentikan dahulu agar bersih
        self.recorder.stop_all(stop_auto_scheduler=False)
        time.sleep(0.5)

        try:
            while not self._stop_event.is_set():
                if self.total_cycles > 0 and self.current_cycle >= self.total_cycles:
                    logger.info("AutoRecordScheduler: Target siklus selesai dicapai.")
                    with self._lock:
                        self.state = "completed"
                        self.is_running = False
                        self.active_camera_ids = []
                    self.recorder._notify_update()
                    break

                self.current_cycle += 1
                cams = self._pick_cameras()
                if not cams:
                    logger.warning("AutoRecordScheduler: Tidak ada CCTV aktif untuk direkam.")
                    with self._lock:
                        self.state = "error"
                        self.is_running = False
                        self.active_camera_ids = []
                    self.recorder._notify_update()
                    break

                cam_ids = [c["id"] for c in cams]
                tried_in_cycle = set(cam_ids)
                duration_sec = max(5, int(float(self.duration_minutes) * 60))

                with self._lock:
                    self.state = "recording"
                    self.active_camera_ids = list(cam_ids)
                    self.cycle_start_time = datetime.now()
                    self.cycle_end_time = self.cycle_start_time + timedelta(seconds=duration_sec)

                # Buat nama folder per siklus/sesi jika menggunakan mode per_session
                st_cfg = load_settings()
                fold_mode = st_cfg.get("folder_organization", "single")
                cycle_folder_name = None
                if fold_mode == "per_session":
                    now_str = CCTVRecorder.format_compact_timestamp(self.cycle_start_time)
                    tot_lbl = f"{self.total_cycles}" if self.total_cycles > 0 else "Loop"
                    cycle_folder_name = f"Siklus_{self.current_cycle}_dari_{tot_lbl}_{now_str}"

                logger.info(f"[AutoRecord] Memulai Siklus {self.current_cycle}/{self.total_cycles} ({len(cams)} kamera ONLINE terverifikasi, durasi {self.duration_minutes}m ({duration_sec}s), folder: {cycle_folder_name or 'Default'})")

                # Mulai rekaman untuk kamera yang terpilih dengan batas waktu keras (max_duration_seconds)
                for cam in cams:
                    if self._stop_event.is_set():
                        break
                    rem_for_cam = max(5, int((self.cycle_end_time - datetime.now()).total_seconds()))
                    self.recorder.start_stream(
                        cam["id"],
                        cam["stream_url"],
                        session_folder=cycle_folder_name,
                        skip_precheck=True,
                        max_duration_seconds=rem_for_cam
                    )
                    time.sleep(0.2)

                self.recorder._notify_update()

                # Tunggu selama durasi rekam + pantau jika ada kamera yang tiba-tiba offline/mati di tengah jalan
                while not self._stop_event.is_set():
                    now = datetime.now()
                    if now >= self.cycle_end_time:
                        break

                    # Cek kesehatan stream yang sedang direkam (jika sisa waktu siklus > 15 detik)
                    rem_sec = (self.cycle_end_time - now).total_seconds()
                    if self.camera_mode != "all" and rem_sec > 15:
                        for idx_slot, cid in enumerate(list(cam_ids)):
                            if self._stop_event.is_set() or datetime.now() >= self.cycle_end_time:
                                break
                            try:
                                st = self.recorder.streams.get(cid)
                                t_worker = self.recorder.threads.get(cid)
                                is_dead = False
                                if st:
                                    elapsed_cam = (datetime.now() - st.start_time).total_seconds() if st.start_time else 0
                                    if st.is_error and st.retry_count >= 1:
                                        is_dead = True
                                    elif not st.is_recording and (t_worker is None or not t_worker.is_alive()) and elapsed_cam > 5:
                                        is_dead = True
                                    elif st.is_recording and elapsed_cam >= 20 and st.bytes_recorded == 0:
                                        is_dead = True

                                if is_dead:
                                    dead_name = st.name if st else cid
                                    logger.warning(
                                        f"[AutoRecord-Failover] Kamera '{dead_name}' ({cid}) offline/0-byte saat merekam "
                                        f"-> dipindahkan ke Menu CCTV OFF & dialihkan ke kamera lain yang ONLINE..."
                                    )
                                    self.recorder.stop_stream(cid)
                                    self.recorder.move_to_offline(cid, reason="Terputus / 0-byte saat perekaman")
                                    valid_cams = self._load_valid_cams()
                                    replacement = self._pick_single_online_replacement(
                                        valid_cams,
                                        tried_in_cycle,
                                        deadline=self.cycle_end_time
                                    )
                                    rem_after = int((self.cycle_end_time - datetime.now()).total_seconds())
                                    if replacement and rem_after > 5:
                                        new_cid = replacement["id"]
                                        tried_in_cycle.add(new_cid)
                                        cam_ids[idx_slot] = new_cid
                                        with self._lock:
                                            self.active_camera_ids = list(cam_ids)
                                        self.recorder.start_stream(
                                            new_cid,
                                            replacement["stream_url"],
                                            session_folder=cycle_folder_name,
                                            skip_precheck=True,
                                            max_duration_seconds=rem_after
                                        )
                                        logger.info(
                                            f"[AutoRecord-Failover] Pengganti aktif: '{replacement.get('name')}' ({new_cid}) "
                                            f"sisa durasi {rem_after}s -> jumlah rekaman aktif tetap {len(cam_ids)} kamera!"
                                        )
                            except Exception as failover_err:
                                logger.error(f"[AutoRecord-Failover] Error saat failover {cid}: {failover_err}")

                    time.sleep(1)
                    self.recorder._notify_update()

                # Selesai 1 siklus rekam -> Stop SEMUA kamera yang sedang merekam di siklus ini
                logger.info(f"[AutoRecord] Siklus {self.current_cycle} selesai tepat waktu. Menghentikan & menyimpan file rekaman...")
                for cid in list(cam_ids):
                    try:
                        self.recorder.stop_stream(cid)
                    except Exception:
                        pass
                # Pastikan tidak ada stream lain yang tertinggal
                self.recorder.stop_all(stop_auto_scheduler=False)
                time.sleep(0.5)

                if self._stop_event.is_set():
                    break

                with self._lock:
                    self.active_camera_ids = []
                self.recorder._notify_update()

                # Cek apakah ini siklus terakhir
                if self.total_cycles > 0 and self.current_cycle >= self.total_cycles:
                    logger.info(f"[AutoRecord] Sukses! Selesai seluruh {self.total_cycles} siklus rekaman.")
                    with self._lock:
                        self.state = "completed"
                        self.is_running = False
                    self.recorder._notify_update()
                    break

                # Jika ada jeda istirahat antar siklus
                if self.interval_seconds > 0:
                    with self._lock:
                        self.state = "waiting"
                        self.cycle_start_time = datetime.now()
                        self.cycle_end_time = self.cycle_start_time + timedelta(seconds=self.interval_seconds)
                    logger.info(f"[AutoRecord] Istirahat {self.interval_seconds}s sebelum siklus {self.current_cycle+1}...")
                    self.recorder._notify_update()

                    while not self._stop_event.is_set():
                        if datetime.now() >= self.cycle_end_time:
                            break
                        time.sleep(1)
                        self.recorder._notify_update()

                    if self._stop_event.is_set():
                        break
        except Exception as loop_err:
            logger.error(f"[AutoRecord] Fatal error di _run_loop: {loop_err}")
        finally:
            # Pastikan semua kamera berhenti saat loop selesai atau dihentikan
            self.recorder.stop_all(stop_auto_scheduler=False)
            with self._lock:
                if self._stop_event.is_set():
                    self.state = "stopped"
                elif self.state not in ("completed", "error"):
                    self.state = "stopped"
                self.is_running = False
                self.active_camera_ids = []
            self.recorder._notify_update()

    def get_status(self) -> dict:
        with self._lock:
            now = datetime.now()
            remaining_sec = 0
            if self.cycle_end_time and self.state in ("recording", "waiting"):
                remaining_sec = max(0, int((self.cycle_end_time - now).total_seconds()))

            active_cam_names = []
            all_status = self.recorder.streams
            for cid in self.active_camera_ids:
                if cid in all_status:
                    active_cam_names.append(all_status[cid].name)
                else:
                    active_cam_names.append(cid)

            return {
                "is_running": self.is_running,
                "state": self.state,
                "current_cycle": self.current_cycle,
                "total_cycles": self.total_cycles,
                "duration_minutes": self.duration_minutes,
                "interval_seconds": self.interval_seconds,
                "camera_mode": self.camera_mode,
                "camera_count": self.camera_count,
                "active_camera_ids": list(self.active_camera_ids),
                "active_camera_names": active_cam_names,
                "remaining_seconds": remaining_sec,
                "cycle_start_time": self.cycle_start_time.isoformat() if self.cycle_start_time else None,
                "cycle_end_time": self.cycle_end_time.isoformat() if self.cycle_end_time else None
            }


class CCTVRecorder:
    """
    Engine utama perekaman multi-CCTV.
    Jalankan dengan memanggil start_all() / stop_all()
    atau kelola stream individual dengan start_stream() / stop_stream()
    """
    CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

    def __init__(self):
        self.streams: Dict[str, StreamStatus] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._malang_cookie_lock = threading.Lock()
        self._malang_cookie: str = ""
        self._malang_cookie_time: float = 0.0
        self.on_status_update: Optional[Callable] = None  # callback untuk GUI
        self.auto_scheduler = AutoRecordScheduler(self)
        self._load_config()

    def _get_malang_cookie(self, force_refresh: bool = False) -> str:
        """Ambil & cache cookie otentikasi nancy_auth_v1c dari cctv.malangkota.go.id."""
        with self._malang_cookie_lock:
            now_ts = time.time()
            if not force_refresh and self._malang_cookie and (now_ts - self._malang_cookie_time) < 1800:
                return self._malang_cookie
            try:
                import requests
                import urllib3
                urllib3.disable_warnings()
                s = requests.Session()
                s.headers.update({
                    "User-Agent": self.CHROME_UA,
                    "Referer": "https://cctv.malangkota.go.id/",
                })
                s.get("https://cctv.malangkota.go.id/", verify=False, timeout=10)
                cookie_str = "; ".join([f"{k}={v}" for k, v in s.cookies.get_dict().items()])
                if cookie_str:
                    self._malang_cookie = cookie_str
                    self._malang_cookie_time = now_ts
            except Exception as e:
                logger.warning(f"Gagal mengambil cookie Malang CCTV: {e}")
            return self._malang_cookie

    @staticmethod
    def _get_referer_for_url(stream_url: str) -> str:
        import urllib.parse
        parsed = urllib.parse.urlparse(stream_url)
        referer = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme and parsed.netloc else "https://cctv.jogjakota.go.id/"
        if "demo-cctv.cimahikota.go.id" in stream_url:
            referer = "https://smartcity.cimahikota.go.id/"
        elif "cctv.bandungkab.go.id" in stream_url:
            referer = "https://dishub.bandungkab.go.id/"
        elif "cctv.malangkota.go.id" in stream_url:
            referer = "https://cctv.malangkota.go.id/"
        return referer

    def is_stream_online(self, stream_url: str, timeout: int = 8) -> bool:
        """
        Memastikan stream CCTV benar-benar AKTIF (ONLINE) dan menyajikan playlist HLS (#EXTM3U)
        sebelum perekaman dimulai agar tidak menghasilkan rekaman 0-byte / tidak bisa diputar.
        """
        if not stream_url:
            return False
        if stream_url.lower().startswith(("rtsp://", "rtsps://")):
            return True

        # YouTube live webcam: URL halaman/channel bersifat stabil, sedangkan
        # URL media HLS-nya ditandatangani dan berubah-ubah. Resolve saat cek.
        if self._is_youtube_url(stream_url):
            return bool(self._resolve_youtube_url(stream_url))

        try:
            self._ensure_on_demand_stream(stream_url)
            import requests
            import urllib3
            urllib3.disable_warnings()

            referer = self._get_referer_for_url(stream_url)
            headers = {
                "User-Agent": self.CHROME_UA,
                "Referer": referer,
            }
            if "cctv.malangkota.go.id" in stream_url:
                ck = self._get_malang_cookie(force_refresh=False)
                if ck:
                    headers["Cookie"] = ck

            resp = requests.get(stream_url, headers=headers, verify=False, timeout=timeout)
            if resp.status_code == 403 and "cctv.malangkota.go.id" in stream_url:
                ck = self._get_malang_cookie(force_refresh=True)
                if ck:
                    headers["Cookie"] = ck
                    resp = requests.get(stream_url, headers=headers, verify=False, timeout=timeout)

            if resp.status_code == 200 and "#EXTM3U" in resp.text[:400]:
                lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
                return len(lines) > 0
            return False
        except Exception:
            return False

    @staticmethod
    def _is_youtube_url(stream_url: str) -> bool:
        value = (stream_url or "").lower()
        return "youtube.com/" in value or "youtu.be/" in value

    @staticmethod
    def _resolve_youtube_url(stream_url: str) -> Optional[str]:
        """Resolve URL YouTube live menjadi URL media sementara untuk FFmpeg."""
        try:
            import yt_dlp
            opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(stream_url, download=False)
            if info:
                formats = [f for f in info.get("formats", []) if f.get("url")]
                # Prefer a combined video+audio HLS rendition; otherwise use
                # the highest available video rendition FFmpeg can copy.
                formats.sort(key=lambda f: (
                    f.get("protocol", "") in ("m3u8", "m3u8_native"),
                    f.get("vcodec", "none") != "none",
                    f.get("acodec", "none") != "none",
                    f.get("height") or 0,
                ), reverse=True)
                if formats:
                    return str(formats[0]["url"])
                if info.get("url"):
                    return str(info["url"])
        except Exception as exc:
            logger.warning(f"Gagal resolve YouTube live {stream_url}: {exc}")
        return None

    def load_offline_configs(self) -> list:
        """Membaca daftar kamera yang sedang OFFLINE / Mati dari cctv_offline.json"""
        if not OFFLINE_CONFIG_FILE.exists():
            return []
        try:
            with open(OFFLINE_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def save_offline_configs(self, off_list: list):
        """Menyimpan daftar kamera OFFLINE ke cctv_offline.json"""
        with open(OFFLINE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(off_list, f, indent=2, ensure_ascii=False)

    def move_to_offline(self, cctv_id: str, reason: str = "Stream Offline") -> Optional[dict]:
        """
        Memindahkan kamera dari daftar ON (cctv_streams.json) ke daftar OFF (cctv_offline.json)
        secara otomatis agar tidak mengganggu proses perekaman.
        """
        with self._lock:
            on_list = []
            if CONFIG_FILE.exists():
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        on_list = json.load(f)
                except Exception:
                    on_list = []

            target_cam = None
            new_on_list = []
            for c in on_list:
                if c.get("id") == cctv_id:
                    target_cam = c
                else:
                    new_on_list.append(c)

            if not target_cam:
                return None

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            target_cam["status_health"] = "offline"
            target_cam["offline_reason"] = reason
            target_cam["last_checked"] = now_str
            target_cam["fail_count"] = int(target_cam.get("fail_count", 0)) + 1

            off_list = self.load_offline_configs()
            off_map = {c.get("id"): c for c in off_list if c.get("id")}
            if cctv_id in off_map:
                target_cam["fail_count"] = int(off_map[cctv_id].get("fail_count", 1)) + 1
            off_map[cctv_id] = target_cam

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_on_list, f, indent=2, ensure_ascii=False)
            self.save_offline_configs(list(off_map.values()))
            return target_cam

    def move_to_online(self, cctv_id: str) -> Optional[dict]:
        """
        Memindahkan kembali kamera yang sudah aktif (ON) dari daftar OFF (cctv_offline.json)
        ke daftar ON (cctv_streams.json).
        """
        with self._lock:
            off_list = self.load_offline_configs()
            target_cam = None
            new_off_list = []
            for c in off_list:
                if c.get("id") == cctv_id:
                    target_cam = c
                else:
                    new_off_list.append(c)

            if not target_cam:
                return None

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            target_cam["status_health"] = "online"
            target_cam["offline_reason"] = ""
            target_cam["last_checked"] = now_str
            target_cam["fail_count"] = 0
            target_cam["enabled"] = True

            on_list = []
            if CONFIG_FILE.exists():
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        on_list = json.load(f)
                except Exception:
                    on_list = []

            if not any(c.get("id") == cctv_id for c in on_list):
                on_list.append(target_cam)

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(on_list, f, indent=2, ensure_ascii=False)
            self.save_offline_configs(new_off_list)

            self.streams[cctv_id] = StreamStatus(
                cctv_id=cctv_id,
                name=target_cam.get("name", cctv_id)
            )
            return target_cam

    def run_health_scan(self, mode: str = "all") -> dict:
        """
        Auto-scanning kesehatan CCTV:
        - mode='all': cek daftar ON & OFF (yang mati pindah ke OFF, yang hidup kembali pindah ke ON)
        - mode='offline_only': cek ulang daftar OFF saja (jika sudah ON otomatis masuk ke daftar ON lagi)
        - mode='online_only': cek daftar ON saja (jika OFF langsung pindah ke daftar OFF)
        """
        import concurrent.futures

        on_list = []
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    on_list = json.load(f)
            except Exception:
                on_list = []
        off_list = self.load_offline_configs()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Pre-warm Malang cookie before parallel checks
        self._get_malang_cookie(force_refresh=False)

        def check_one(cam):
            url = str(cam.get("stream_url", "")).strip()
            if not url:
                return (False, cam, "URL Kosong")
            # Stream on-demand Surabaya SITS tidak di-flood serentak agar server tidak menolak koneksi
            if "36.66.208.101:5000" in url and cam.get("status_health") == "online":
                return (True, cam, "OK")
            ok = self.is_stream_online(url, timeout=7)
            return (ok, cam, "OK" if ok else "Stream Tidak Merespons / Offline")

        moved_to_off = 0
        moved_to_on = 0
        still_on = []
        still_off = []

        if mode in ("all", "online_only"):
            with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
                for ok, cam, reason in ex.map(check_one, on_list):
                    cam["last_checked"] = now_str
                    if ok:
                        cam["status_health"] = "online"
                        cam["offline_reason"] = ""
                        still_on.append(cam)
                    else:
                        cam["status_health"] = "offline"
                        cam["offline_reason"] = reason
                        cam["fail_count"] = int(cam.get("fail_count", 0)) + 1
                        still_off.append(cam)
                        moved_to_off += 1
        else:
            still_on = list(on_list)

        if mode in ("all", "offline_only"):
            with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
                for ok, cam, reason in ex.map(check_one, off_list):
                    cam["last_checked"] = now_str
                    if ok:
                        cam["status_health"] = "online"
                        cam["offline_reason"] = ""
                        cam["fail_count"] = 0
                        cam["enabled"] = True
                        still_on.append(cam)
                        moved_to_on += 1
                    else:
                        cam["status_health"] = "offline"
                        cam["offline_reason"] = reason
                        cam["fail_count"] = int(cam.get("fail_count", 1)) + 1
                        still_off.append(cam)
        else:
            # Gabungkan off_list lama dengan still_off baru dari hasil cek online_only
            off_map = {c.get("id"): c for c in off_list if c.get("id")}
            for c in still_off:
                cid = c.get("id")
                if cid in off_map:
                    c["fail_count"] = int(off_map[cid].get("fail_count", 1)) + 1
                off_map[cid] = c
            still_off = list(off_map.values())

        # Deduplicate still_on & still_off by id
        seen_on = {}
        for c in still_on:
            seen_on[c.get("id")] = c
        final_on = list(seen_on.values())

        seen_off = {}
        for c in still_off:
            if c.get("id") not in seen_on:
                seen_off[c.get("id")] = c
        final_off = list(seen_off.values())

        with self._lock:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(final_on, f, indent=2, ensure_ascii=False)
            self.save_offline_configs(final_off)
            self._load_config()

        return {
            "online_total": len(final_on),
            "offline_total": len(final_off),
            "moved_to_off": moved_to_off,
            "moved_to_on": moved_to_on,
        }

    def _load_config(self):
        """Load konfigurasi stream dari JSON tanpa menghapus status stream yang sedang merekam"""
        if not CONFIG_FILE.exists():
            logger.warning(f"Config tidak ditemukan: {CONFIG_FILE}")
            return

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        with self._lock:
            existing_active = {
                cid: st for cid, st in self.streams.items()
                if st.is_recording or (st.process is not None and st.process.poll() is None)
            }
            new_streams: Dict[str, StreamStatus] = {}
            for cam in config:
                if cam.get("enabled", True):
                    cid = cam["id"]
                    if cid in existing_active:
                        existing_active[cid].name = cam.get("name", cid)
                        new_streams[cid] = existing_active[cid]
                    else:
                        new_streams[cid] = StreamStatus(
                            cctv_id=cid,
                            name=cam.get("name", cid)
                        )
            for cid, st in existing_active.items():
                if cid not in new_streams:
                    new_streams[cid] = st
            self.streams = new_streams

        logger.info(f"Loaded {len(self.streams)} CCTV streams dari config")

    def reload_config(self):
        """Reload config tanpa menghentikan stream yang sedang berjalan"""
        old_ids = set(self.streams.keys())
        self._load_config()
        new_ids = set(self.streams.keys())
        added = new_ids - old_ids
        if added:
            logger.info(f"Stream baru ditemukan: {added}")

    def get_ffmpeg_command(
        self,
        stream_url: str,
        output_path: str,
        max_duration_seconds: Optional[int] = None
    ) -> list:
        """
        Build FFmpeg command teruji untuk merekam HLS CCTV secara sempurna.
        Jika max_duration_seconds diberikan, FFmpeg dibatasi durasi maksimalnya (-t)
        agar proses otomatis berhenti tepat waktu meskipun scheduler sibuk.
        """
        referer = self._get_referer_for_url(stream_url)
        header_lines = [f"Referer: {referer}"]
        if "cctv.malangkota.go.id" in stream_url:
            ck = self._get_malang_cookie(force_refresh=False)
            if ck:
                header_lines.append(f"Cookie: {ck}")
        headers_arg = "\r\n".join(header_lines) + "\r\n"

        cmd = [
            FFMPEG, "-y",
            "-loglevel", "error",
            "-rw_timeout", "10000000",
            "-user_agent", self.CHROME_UA,
            "-headers", headers_arg,
            "-i", stream_url,
        ]
        if max_duration_seconds and max_duration_seconds > 0:
            cmd.extend(["-t", str(int(max_duration_seconds))])
        cmd.extend([
            "-c", "copy",
            output_path
        ])
        return cmd

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Sanitize name to make it safe for Windows filenames"""
        # Ganti karakter ilegal windows dengan underscore / strip
        safe = "".join(c if c.isalnum() or c in (" ", "-", "_", "(", ")") else "_" for c in name)
        safe = safe.strip().replace(" ", "_")
        while "__" in safe:
            safe = safe.replace("__", "_")
        return safe or "CCTV"

    @staticmethod
    def format_compact_timestamp(dt: Optional[datetime] = None) -> str:
        """
        Format tanggal dan jam ringkas & informatif:
        Contoh: Okt11_06-48 (Bulan 3 huruf + tanggal + jam:menit)
        """
        if dt is None:
            dt = datetime.now()
        month_names = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
            7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"
        }
        m_name = month_names.get(dt.month, dt.strftime("%b"))
        return f"{m_name}{dt.day:02d}_{dt.strftime('%H-%M')}"

    def _get_output_path(self, cctv_id: str, cam_name: str, session_folder: Optional[str] = None) -> Path:
        """
        Generate path output file sesuai preferensi struktur folder user:
        - 'single': Semua video digabung ke 1 folder utama
        - 'per_session': Disimpan dalam subfolder per sesi/putaran (misal: Sesi_Okt11_06-48 atau Siklus_1_Okt11_06-48)
        - 'per_camera': Disimpan dalam subfolder khusus per nama kamera CCTV
        """
        now = datetime.now()
        safe_area_name = self.sanitize_filename(cam_name)
        # Ambil folder recording & folder organization dari settings
        st = load_settings()
        rec_dir_str = st.get("recordings_dir") or str(RECORDINGS_DIR)
        rec_dir = Path(rec_dir_str)
        try:
            rec_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            rec_dir = RECORDINGS_DIR
            rec_dir.mkdir(parents=True, exist_ok=True)

        fold_mode = st.get("folder_organization", "single")
        target_dir = rec_dir
        time_tag = self.format_compact_timestamp(now)

        if fold_mode == "per_session":
            sub_name = session_folder or f"Sesi_{time_tag}"
            target_dir = rec_dir / self.sanitize_filename(sub_name)
        elif fold_mode == "per_camera":
            target_dir = rec_dir / safe_area_name

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            target_dir = rec_dir

        # Nama file ringkas: [Nama_Area]_[BulanTanggal]_[Jam-Menit].ts
        # Contoh: Simpang_Apmd_Okt11_06-48.ts
        filename = f"{safe_area_name}_{time_tag}.ts"
        return target_dir / filename

    @staticmethod
    def _ensure_on_demand_stream(stream_url: str):
        """
        Jika stream berasal dari server on-demand Dishub Surabaya (36.66.208.101:5000),
        panggil POST /api/start_stream/<cctv_id> terlebih dahulu agar file .m3u8 aktif.
        """
        import re
        import urllib.request
        m = re.search(r"http://36\.66\.208\.101:5000/hls/(cctv_\d+)/stream\.m3u8", stream_url)
        if not m:
            return
        sby_id = m.group(1)
        start_url = f"http://36.66.208.101:5000/api/start_stream/{sby_id}"
        try:
            req = urllib.request.Request(
                start_url,
                method="POST",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            urllib.request.urlopen(req, timeout=15).read()
            # Tunggu hingga manifest stream.m3u8 benar-benar siap diakses
            for _ in range(6):
                try:
                    check_req = urllib.request.Request(stream_url, headers={"User-Agent": "Mozilla/5.0"})
                    urllib.request.urlopen(check_req, timeout=5).read()
                    break
                except Exception:
                    time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Gagal memicu on-demand stream {sby_id}: {e}")

    @staticmethod
    def _terminate_process_safely(proc: Optional[subprocess.Popen], wait_timeout: float = 3.0):
        """Hentikan proses FFmpeg dengan terminate() lalu paksa kill() jika masih membandel"""
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=wait_timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        proc.wait(timeout=2.0)
                    except Exception:
                        pass
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _record_stream(
        self,
        cctv_id: str,
        stream_url: str,
        session_folder: Optional[str] = None,
        skip_precheck: bool = False,
        max_duration_seconds: Optional[int] = None
    ):
        """
        Thread utama perekaman untuk satu CCTV.
        Loop otomatis dengan segmentasi dan retry, serta batas waktu keras (max_duration_seconds) jika disetel.
        """
        stop_event = self._stop_events[cctv_id]
        status = self.streams[cctv_id]
        cam_name = status.name

        logger.info(f"[{cctv_id}] Mulai merekam: {cam_name}" + (f" (maks {max_duration_seconds} dtk)" if max_duration_seconds else ""))
        logger.info(f"[{cctv_id}] URL: {stream_url}")

        first_Check = not skip_precheck
        stream_deadline = (
            datetime.now() + timedelta(seconds=max_duration_seconds)
            if (max_duration_seconds and max_duration_seconds > 0)
            else None
        )

        while not stop_event.is_set():
            if stream_deadline and datetime.now() >= stream_deadline:
                logger.info(f"[{cctv_id}] Batas durasi rekaman ({max_duration_seconds} dtk) tercapai, menghentikan stream.")
                break

            output_path = None
            proc = None
            try:
                # Resolve ulang setiap percobaan/segmen karena URL YouTube
                # memiliki token sementara dan tidak boleh disimpan ke JSON.
                media_url = stream_url
                if self._is_youtube_url(stream_url):
                    media_url = self._resolve_youtube_url(stream_url)
                    if not media_url:
                        raise RuntimeError("YouTube live sedang offline atau gagal di-resolve")
                if first_Check:
                    if not self.is_stream_online(stream_url):
                        raise RuntimeError("Stream CCTV sedang offline atau tidak merespons playlist HLS")
                else:
                    self._ensure_on_demand_stream(stream_url)
                first_Check = True

                if stop_event.is_set():
                    break

                # Hitung sisa durasi jika menggunakan batas waktu keras (misal dari Auto-Record)
                rem_seconds: Optional[int] = None
                if stream_deadline:
                    rem_float = (stream_deadline - datetime.now()).total_seconds()
                    if rem_float <= 1:
                        break
                    rem_seconds = max(1, int(rem_float))

                output_path = self._get_output_path(cctv_id, cam_name, session_folder=session_folder)
                cmd = self.ffmpeg_command = self.get_ffmpeg_command(
                    media_url,
                    str(output_path),
                    max_duration_seconds=rem_seconds
                )

                logger.info(f"[{cctv_id}] File: {output_path.name}")

                # Jalankan FFmpeg sebagai subprocess
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )

                with self._lock:
                    status.is_recording = True
                    status.is_error = False
                    status.error_msg = ""
                    status.start_time = datetime.now()
                    status.current_file = output_path.name
                    status.process = proc

                # Jika stop_event disetel tepat saat Popen baru dibuat, langsung hentikan
                if stop_event.is_set():
                    self._terminate_process_safely(proc, wait_timeout=2.0)
                    break

                self._notify_update()

                # Hitung kapan segment berikutnya berdasarkan settings atau stream_deadline
                st_cfg = load_settings()
                dur_min = int(st_cfg.get("segment_duration_minutes", SEGMENT_DURATION_MINUTES))
                segment_end = datetime.now() + timedelta(minutes=dur_min)
                if stream_deadline and stream_deadline < segment_end:
                    segment_end = stream_deadline

                while not stop_event.is_set():
                    # Cek apakah FFmpeg masih berjalan
                    ret = proc.poll()
                    if ret is not None:
                        if stop_event.is_set():
                            break
                        # Jika FFmpeg selesai dengan normal (ret == 0) karena batas -t tercapai
                        if ret == 0 and stream_deadline:
                            if output_path.exists() and output_path.stat().st_size >= 1024:
                                with self._lock:
                                    status.total_files += 1
                                    status.bytes_recorded = output_path.stat().st_size
                            stop_event.set()
                            break
                        if ret != 0:
                            logger.warning(f"[{cctv_id}] FFmpeg exit code {ret}")
                            raise subprocess.CalledProcessError(ret, cmd)
                        break

                    # Cek apakah waktunya potong segment atau batas durasi tercapai
                    now_ts = datetime.now()
                    if stream_deadline and now_ts >= stream_deadline:
                        logger.info(f"[{cctv_id}] Durasi target selesai ({max_duration_seconds} dtk), menghentikan FFmpeg...")
                        self._terminate_process_safely(proc, wait_timeout=4.0)
                        if output_path.exists() and output_path.stat().st_size >= 1024:
                            with self._lock:
                                status.total_files += 1
                                status.bytes_recorded = output_path.stat().st_size
                        stop_event.set()
                        break

                    if now_ts >= segment_end:
                        logger.info(f"[{cctv_id}] Segment selesai, mulai file baru...")
                        self._terminate_process_safely(proc, wait_timeout=5.0)
                        
                        # Update stats
                        if output_path.exists() and output_path.stat().st_size >= 1024:
                            with self._lock:
                                status.total_files += 1
                                status.bytes_recorded += output_path.stat().st_size
                        break

                    # Update ukuran file saat ini
                    if output_path.exists():
                        with self._lock:
                            status.bytes_recorded = output_path.stat().st_size

                    self._notify_update()
                    stop_event.wait(timeout=1)  # cek setiap 1 detik agar presisi

                # Reset retry counter setelah sukses satu segment
                with self._lock:
                    status.retry_count = 0

                if stream_deadline and datetime.now() >= stream_deadline:
                    break

            except Exception as e:
                if stop_event.is_set():
                    break
                if stream_deadline and datetime.now() >= stream_deadline:
                    break
                with self._lock:
                    status.is_error = True
                    status.error_msg = str(e)[:100]
                    status.retry_count += 1
                    retry = status.retry_count

                logger.error(f"[{cctv_id}] Error (attempt {retry}/{MAX_RETRY_COUNT}): {e}")
                self._notify_update()

                if retry >= MAX_RETRY_COUNT:
                    logger.critical(f"[{cctv_id}] Max retry tercapai, berhenti.")
                    break

                # Tunggu sebelum retry
                stop_event.wait(timeout=RETRY_DELAY_SECONDS)

            finally:
                # Pastikan proses FFmpeg ditutup sepenuhnya (terminate + kill fallback)
                self._terminate_process_safely(proc or status.process, wait_timeout=3.0)
                if output_path and output_path.exists():
                    try:
                        fsize = output_path.stat().st_size
                        if fsize < 1024:
                            # Hapus file 0-byte / korup akibat stream offline agar tidak menyampah
                            output_path.unlink(missing_ok=True)
                            logger.info(f"[{cctv_id}] Menghapus file kosong/tidak valid ({fsize} B): {output_path.name}")
                        else:
                            with self._lock:
                                status.bytes_recorded = fsize
                    except Exception:
                        pass

        with self._lock:
            status.is_recording = False
            status.process = None

        logger.info(f"[{cctv_id}] Recording dihentikan.")
        self._notify_update()

    def start_stream(
        self,
        cctv_id: str,
        stream_url: str,
        session_folder: Optional[str] = None,
        skip_precheck: bool = False,
        max_duration_seconds: Optional[int] = None
    ):
        """Mulai merekam satu stream"""
        if cctv_id in self.threads and self.threads[cctv_id].is_alive():
            logger.warning(f"[{cctv_id}] Sudah berjalan.")
            return

        # Update URL jika berubah
        if cctv_id not in self.streams:
            self.streams[cctv_id] = StreamStatus(cctv_id=cctv_id, name=cctv_id)

        stop_event = threading.Event()
        self._stop_events[cctv_id] = stop_event

        thread = threading.Thread(
            target=self._record_stream,
            args=(cctv_id, stream_url, session_folder, skip_precheck, max_duration_seconds),
            name=f"recorder_{cctv_id}",
            daemon=True
        )
        self.threads[cctv_id] = thread
        thread.start()

    def stop_stream(self, cctv_id: str):
        """Hentikan satu stream secara paksa dan pastikan proses FFmpeg mati"""
        if cctv_id in self._stop_events:
            self._stop_events[cctv_id].set()

        status = self.streams.get(cctv_id)
        if status and status.process:
            self._terminate_process_safely(status.process, wait_timeout=2.0)

        if cctv_id in self.threads:
            t = self.threads[cctv_id]
            if t.is_alive() and t != threading.current_thread():
                t.join(timeout=3)

        if status:
            with self._lock:
                if status.process and status.process.poll() is None:
                    self._terminate_process_safely(status.process, wait_timeout=1.0)
                status.is_recording = False
                status.process = None

        logger.info(f"[{cctv_id}] Stop requested.")

    def start_all(self, streams_config: list, session_folder: Optional[str] = None):
        """Mulai semua stream sekaligus"""
        logger.info(f"Memulai {len(streams_config)} stream...")
        # Jika mode per_session dan session_folder belum diberikan, buat 1 session timestamp untuk batch ini
        if not session_folder:
            st = load_settings()
            if st.get("folder_organization") == "per_session":
                session_folder = f"Sesi_Manual_{self.format_compact_timestamp()}"

        for cam in streams_config:
            if cam.get("enabled", True) and cam.get("stream_url"):
                self.start_stream(cam["id"], cam["stream_url"], session_folder=session_folder)
                time.sleep(0.5)  # jeda kecil agar tidak flood server

    def stop_all(self, stop_auto_scheduler: bool = True):
        """Hentikan semua stream dan auto-record scheduler jika aktif"""
        logger.info("Menghentikan semua stream...")
        if stop_auto_scheduler and hasattr(self, 'auto_scheduler') and self.auto_scheduler.is_running:
            self.auto_scheduler.stop()
        target_ids = set(self._stop_events.keys()) | {
            cid for cid, st in self.streams.items()
            if st.is_recording or (st.process is not None and st.process.poll() is None)
        }
        for cctv_id in list(target_ids):
            self.stop_stream(cctv_id)

    def get_all_status(self) -> Dict[str, StreamStatus]:
        """Ambil status semua stream (thread-safe)"""
        with self._lock:
            return dict(self.streams)

    def _notify_update(self):
        """Panggil callback GUI jika ada"""
        if self.on_status_update:
            try:
                self.on_status_update()
            except Exception:
                pass

    def backup_recordings(self, source_dir: Optional[Path] = None, dest_dir: Optional[Path] = None):
        """
        Backup semua file rekaman ke folder backup.
        Bisa diatur source dan destination.
        """
        st = load_settings()
        src = source_dir or Path(st.get("recordings_dir", str(RECORDINGS_DIR)))
        dst = dest_dir or Path(st.get("backup_dir", str(BACKUP_DIR)))

        if not src.exists():
            logger.warning(f"Folder recordings tidak ditemukan: {src}")
            return 0

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_target = dst / f"backup_{timestamp}"
        backup_target.mkdir(parents=True, exist_ok=True)

        count = 0
        total_size = 0
        for ext in ["*.ts", "*.mp4", "*.mkv"]:
            for rec_file in src.rglob(ext):
                try:
                    rel = rec_file.relative_to(src)
                    dest_file = backup_target / rel
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(rec_file), str(dest_file))
                    count += 1
                    total_size += rec_file.stat().st_size
                    logger.info(f"Backup: {rel}")
                except Exception as e:
                    logger.error(f"Error copying {rec_file}: {e}")

        logger.info(f"Backup selesai: {count} file, {total_size/1024/1024:.1f} MB -> {backup_target}")
        return count

    @staticmethod
    def format_bytes(size_bytes: int) -> str:
        """Format bytes ke human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def get_disk_usage() -> dict:
        """Cek penggunaan disk dengan fallback aman jika terjadi PermissionError"""
        st = load_settings()
        rec_dir_str = st.get("recordings_dir") or str(RECORDINGS_DIR)
        rec_dir = Path(rec_dir_str)
        try:
            rec_dir.mkdir(parents=True, exist_ok=True)
            usage = shutil.disk_usage(str(rec_dir))
        except (PermissionError, OSError):
            rec_dir = RECORDINGS_DIR
            rec_dir.mkdir(parents=True, exist_ok=True)
            usage = shutil.disk_usage(str(rec_dir))

        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": (usage.used / usage.total) * 100
        }


if __name__ == "__main__":
    # Test mode - rekam 1 stream dummy
    print("CCTV Recorder Engine - Test Mode")
    print("Jalankan main_gui.py untuk tampilan penuh")
