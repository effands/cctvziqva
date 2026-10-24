"""
CCTV Multi-Source Stream Scanner
================================
Secara otomatis mendeteksi dan mengambil stream URL (.m3u8, .mp4, rtsps, hls)
dari berbagai website CCTV publik (Pemkot/Pemprov Jogja, Malang, Kediri, Denpasar, SkylineWebcams, dll).
"""

import asyncio
import json
import re
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

from app_paths import DATA_DIR
BASE_DIR = DATA_DIR
OUTPUT_FILE = BASE_DIR / "cctv_streams.json"

async def fetch_jogjakota_api():
    """Mengambil 150+ CCTV resmi dari cctv.jogjakota.go.id"""
    url = "https://cctv.jogjakota.go.id/home/getdata"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://cctv.jogjakota.go.id/home"
        }
    )
    results = []
    try:
        raw_data = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        items = json.loads(raw_data)
        for i, item in enumerate(items):
            link = item.get("cctv_link", "").strip()
            if link:
                raw_id = item.get("cctv_id", i+1)
                try:
                    formatted_id = f"cctv_{int(raw_id):03d}"
                except ValueError:
                    formatted_id = f"cctv_{i+1:03d}"

                name = item.get("cctv_title") or f"CCTV {i+1}"
                location = item.get("kecamatan_nama") or "Yogyakarta"

                results.append({
                    "id": formatted_id,
                    "name": str(name).title(),
                    "location": str(location).title(),
                    "city": "Yogyakarta",
                    "country": "Indonesia",
                    "stream_url": link,
                    "enabled": True,
                    "source": "jogjakota"
                })
    except Exception as e:
        print(f"[ERROR] JogjaKota API fetch error: {e}")
    return results


async def fetch_surabaya_api():
    """Mengambil CCTV aktif (online) dari Dishub Surabaya (http://36.66.208.101:5000/)"""
    base_url = "http://36.66.208.101:5000"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"{base_url}/"
    }
    results = []
    try:
        req_cctvs = urllib.request.Request(f"{base_url}/cctvs", headers=headers)
        raw_cctvs = urllib.request.urlopen(req_cctvs, timeout=15).read().decode("utf-8")
        cctvs = json.loads(raw_cctvs)

        req_status = urllib.request.Request(f"{base_url}/api/cctv_statuses", headers=headers)
        raw_status = urllib.request.urlopen(req_status, timeout=15).read().decode("utf-8")
        statuses = json.loads(raw_status)

        for i, item in enumerate(cctvs):
            raw_id = str(item.get("id", "")).strip()
            if not raw_id:
                continue
            # Hanya ambil CCTV yang berstatus aktif / online
            if statuses.get(raw_id) != "online":
                continue

            db_id = item.get("db_id", raw_id.replace("cctv_", ""))
            cid = f"sby_{db_id}"
            raw_name = str(item.get("name") or f"CCTV Surabaya {db_id}").strip()
            raw_area = str(item.get("area") or "Surabaya").strip()

            results.append({
                "id": cid,
                "name": raw_name.title(),
                "location": f"{raw_area.title()} (Surabaya)",
                "city": "Surabaya",
                "country": "Indonesia",
                "stream_url": f"{base_url}/hls/{raw_id}/stream.m3u8",
                "enabled": True,
                "source": "surabaya"
            })
        print(f"[FOUND] Ditemukan {len(results)} CCTV aktif dari Dishub Surabaya ({base_url})!")
    except Exception as e:
        print(f"[ERROR] Surabaya API fetch error: {e}")
    return results


def _verify_hls_sync(url: str, referer: str = "", timeout: int = 10) -> bool:
    """Memastikan URL .m3u8 benar-benar aktif/online dan memiliki segmen video."""
    import ssl
    import urllib.parse
    ctx_ssl = ssl._create_unverified_context()
    hdrs = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    if referer:
        hdrs["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx_ssl) as r:
            if r.status != 200:
                return False
            body = r.read().decode("utf-8", errors="ignore")
        if "#EXTM3U" not in body:
            return False
        if "#EXT-X-STREAM-INF" in body:
            lines = [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("#")]
            if not lines:
                return False
            sub_url = urllib.parse.urljoin(url, lines[0])
            req2 = urllib.request.Request(sub_url, headers=hdrs)
            with urllib.request.urlopen(req2, timeout=timeout, context=ctx_ssl) as r2:
                b2 = r2.read().decode("utf-8", errors="ignore")
                return r2.status == 200 and "#EXTINF" in b2
        return "#EXTINF" in body
    except Exception:
        return False


async def fetch_bandungkab_api():
    """Mengambil CCTV aktif dari Dishub Kabupaten Bandung (https://dishub.bandungkab.go.id/cctv/)"""
    import ssl
    ctx_ssl = ssl._create_unverified_context()
    url = "https://dishub.bandungkab.go.id/cctv/"
    results = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=12, context=ctx_ssl).read().decode("utf-8", errors="ignore")
        active_part = html.split("/*")[0]
        pat = re.compile(r'\{\s*id:\s*(\d+),\s*name:\s*"([^"]+)",\s*code:\s*"([^"]+)",\s*coordinates:\s*\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\],\s*streamUrl:\s*"([^"]+)"\s*\}')
        for cid, name, code, lat, lng, stream_url in pat.findall(active_part):
            if _verify_hls_sync(stream_url, referer=url):
                results.append({
                    "id": f"bdgkab_{int(cid):02d}",
                    "name": f"CCTV {name.title()}",
                    "location": "Kab. Bandung, Jawa Barat",
                    "city": "Kab. Bandung",
                    "country": "Indonesia",
                    "stream_url": stream_url,
                    "enabled": True,
                    "source": "bandungkab"
                })
        print(f"[FOUND] Ditemukan {len(results)} CCTV aktif dari Dishub Kab. Bandung!")
    except Exception as e:
        print(f"[ERROR] BandungKab fetch error: {e}")
    return results


async def fetch_bandungbarat_api():
    """Mengambil CCTV aktif dari ATCS Dishub Kab. Bandung Barat (https://atcs.bandungbaratkab.go.id/)"""
    import concurrent.futures
    import ssl
    ctx_ssl = ssl._create_unverified_context()
    url = "https://atcs.bandungbaratkab.go.id/get-cctv"
    results = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://atcs.bandungbaratkab.go.id/"})
        raw = json.loads(urllib.request.urlopen(req, timeout=12, context=ctx_ssl).read().decode("utf-8", errors="ignore"))
        items = raw.get("data", []) if isinstance(raw, dict) else raw

        def check_one(idx_item):
            idx, item = idx_item
            raw_name = re.sub(r"<[^>]*>", "", item.get("nama_cctv") or "").strip()
            link = item.get("link", "")
            m = re.search(r"/([0-9a-fA-F-]{36})\.html", link)
            if not m:
                return None
            m3u8 = f"https://atcs-dishubkbb.urbanaccess.net/memfs/{m.group(1)}.m3u8"
            if _verify_hls_sync(m3u8, referer="https://atcs-dishubkbb.urbanaccess.net/"):
                return {
                    "id": f"kbb_{idx:03d}",
                    "name": raw_name.title(),
                    "location": "Kab. Bandung Barat, Jawa Barat",
                    "city": "Bandung Barat",
                    "country": "Indonesia",
                    "stream_url": m3u8,
                    "enabled": True,
                    "source": "bandungbarat"
                }
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            for r in ex.map(check_one, enumerate(items, 1)):
                if r:
                    results.append(r)
        print(f"[FOUND] Ditemukan {len(results)} CCTV aktif dari ATCS Bandung Barat!")
    except Exception as e:
        print(f"[ERROR] BandungBarat fetch error: {e}")
    return results


async def fetch_cimahi_api():
    """Mengambil CCTV aktif dari SmartCity Kota Cimahi (https://smartcity.cimahikota.go.id/cctv)"""
    import concurrent.futures
    channels = [
        (20, "Jl. Kebon Kopi (Simpang Kebon Kopi) 1"),
        (21, "Jl. Kebon Kopi (Simpang Kebon Kopi) 2"),
        (40, "Mahardika (Tugu Tangan baros) 40"),
        (41, "Mahardika (Tugu Tangan baros) 41"),
        (42, "Mahardika (Tugu Tangan baros) 42"),
        (46, "Jl. Jend. Amir Machmud (Simpang Cihanjuang Depan BJB)"),
        (47, "Cimahi Mall"),
        (50, "Sangkuriang"),
        (115, "Simpang Alun-Alun Gandawijaya 1"),
        (116, "Simpang Alun-Alun Gandawijaya 2"),
        (117, "Simpang Alun-Alun Gandawijaya 3"),
        (120, "Jl. Dra Hj Djulaeha (Pasar Atas)"),
        (122, "Jl Raden Demang Hardja Kusuma (Bunderan Pemkot) 2"),
        (123, "Jl Raden Demang Hardja Kusuma (Bunderan Pemkot) 1"),
        (133, "Jl. Kolonel Masturi (Simpang Citeureup)"),
        (135, "Armed 1"),
        (195, "Armed 2"),
    ]
    results = []

    def check_ch(item):
        cid, name = item
        m3u8 = f"https://demo-cctv.cimahikota.go.id/rtc/api/stream.m3u8?src={cid}"
        if _verify_hls_sync(m3u8, referer="https://smartcity.cimahikota.go.id/", timeout=12):
            return {
                "id": f"cimahi_{cid:03d}",
                "name": name,
                "location": "Kota Cimahi, Jawa Barat",
                "city": "Cimahi",
                "country": "Indonesia",
                "stream_url": m3u8,
                "enabled": True,
                "source": "cimahi"
            }
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(check_ch, channels):
            if r:
                results.append(r)
    print(f"[FOUND] Ditemukan {len(results)} CCTV aktif dari SmartCity Cimahi!")
    return results


async def fetch_malangkota_api():
    """
    Mengambil daftar CCTV resmi dari https://cctv.malangkota.go.id/
    dan memverifikasi hanya stream yang aktif (ONLINE) menggunakan cookie sesi resmi.
    """
    import concurrent.futures
    import requests
    import urllib3
    urllib3.disable_warnings()
    print("[SCAN] Mengambil & memverifikasi CCTV aktif dari cctv.malangkota.go.id...")
    results = []
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": ua,
            "Referer": "https://cctv.malangkota.go.id/",
        })
        s.get("https://cctv.malangkota.go.id/", verify=False, timeout=15)
        r1 = s.post(
            "https://cctv.malangkota.go.id/api/v2/get-cameras",
            files={"m_kecamatan_id": (None, "99")},
            headers={"X-Requested-With": "XMLHttpRequest"},
            verify=False,
            timeout=20,
        )
        list_data = r1.json().get("msg_detail", {}).get("list_data", [])
        cookie_header = "; ".join([f"{k}={v}" for k, v in s.cookies.get_dict().items()])

        def check_cam(item):
            stream_id = str(item.get("stream_id", "")).strip()
            if not stream_id:
                return None
            url = f"https://cctv.malangkota.go.id/cctv-stream/streams/{stream_id}.m3u8"
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": ua, "Referer": "https://cctv.malangkota.go.id/", "Cookie": cookie_header},
                    verify=False,
                    timeout=10,
                )
                if resp.status_code == 200 and "#EXTM3U" in resp.text[:300]:
                    return (item, url)
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            verified = [r for r in ex.map(check_cam, list_data) if r]

        for idx, (it, u) in enumerate(verified, 1):
            raw_name = str(it.get("name") or it.get("address") or f"Malang {idx}").strip()
            kec = str(it.get("nama_kecamatan") or "Kota Malang").strip().title()
            results.append({
                "id": f"cctv_malangkota_{idx:03d}",
                "name": raw_name,
                "location": f"{kec}, Kota Malang",
                "city": "Malang",
                "country": "Indonesia",
                "stream_url": u,
                "enabled": True,
                "source": "malangkota",
            })
        print(f"[FOUND] Ditemukan {len(results)} CCTV aktif dari Kota Malang (total terdaftar: {len(list_data)})!")
    except Exception as e:
        print(f"[WARNING] Gagal fetch Malang Kota API: {e}")
    return results


async def fetch_jogjaprov_api(browser=None):
    """
    Mengambil 600+ CCTV resmi dari cctv.jogjaprov.go.id via location-pins API
    """
    print("[SCAN] Mengambil 600+ CCTV dari cctv.jogjaprov.go.id...")
    results = []
    own_browser = False
    p_instance = None
    try:
        if browser is None:
            p_instance = await async_playwright().start()
            browser = await p_instance.chromium.launch(headless=True)
            own_browser = True

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            await page.goto("https://cctv.jogjaprov.go.id/", wait_until="domcontentloaded", timeout=20000)
            res = await page.evaluate('''async () => {
                const r = await fetch('https://cctv.jogjaprov.go.id/api/v1/location-pins?include=categories&fields%5Blocation-pins%5D=slug,name,alias_name,group_name,stream_url,connected,active,lat,lng', {
                    headers: { 'Accept': 'application/vnd.api+json' }
                });
                return await r.json();
            }''')
            data_items = res.get("data", []) if isinstance(res, dict) else []
            for item in data_items:
                attr = item.get("attributes") or {}
                raw_stream = attr.get("stream_url")
                if not raw_stream or not isinstance(raw_stream, str):
                    continue
                stream_url = raw_stream.strip()
                if stream_url and stream_url.startswith("http"):
                    alias = attr.get("alias_name")
                    name = attr.get("name")
                    raw_name = str(alias or name or "CCTV DIY").strip()
                    group_val = attr.get("group_name")
                    group_name = str(group_val or "Daerah Istimewa Yogyakarta").strip()
                    cid = f"prov_{item.get('id', len(results)+1)}"
                    results.append({
                        "id": cid,
                        "name": raw_name.title(),
                        "location": group_name,
                        "city": "Yogyakarta",
                        "country": "Indonesia",
                        "stream_url": stream_url,
                        "enabled": True,
                        "source": "jogjaprov"
                    })
            print(f"[FOUND] Ditemukan {len(results)} CCTV resmi dari cctv.jogjaprov.go.id!")
        except Exception as ex:
            print(f"[WARNING] Gagal fetch jogjaprov API: {ex}")
        finally:
            await context.close()
            if own_browser:
                await browser.close()
                if p_instance:
                    await p_instance.stop()
    except Exception as e:
        print(f"[ERROR] fetch_jogjaprov_api error: {e}")
    return results


async def scan_website_url(page_url: str, browser=None):
    """
    Menggunakan Playwright Headless Browser & Network Interception untuk
    mengendus (sniff) stream URL (.m3u8, .mp4, HLS, RTSP) dari URL website manapun!
    """
    print(f"[SCAN] Scanning website stream URL: {page_url}")
    found_streams = []
    own_browser = False
    p_instance = None
    
    try:
        if browser is None:
            p_instance = await async_playwright().start()
            browser = await p_instance.chromium.launch(headless=True)
            own_browser = True

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        def handle_request(req):
            url = req.url
            # Filter hanya URL media; kata "live"/"stream" saja sering cocok
            # dengan halaman HTML, font, atau telemetry dan bukan video.
            if any(ext in url.lower() for ext in [".m3u8", ".mp4", ".webm", ".ts", ".mkv", ".flv", "chunklist", ".ism/manifest"]):
                if not any(ignored in url.lower() for ignored in ["analytics", "google", "facebook", "css", "js", "png", "jpg", "svg", "ico"]):
                    if url not in found_streams:
                        found_streams.append(url)

        page.on("request", handle_request)
        page.on("response", lambda res: handle_request(res.request))

        try:
            await page.goto(page_url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(4)  # Beri waktu video player memuat stream
            
            # Coba cari tag <video> atau <iframe> jika ada video tersembunyi
            videos = await page.query_selector_all("video, iframe, source")
            for v in videos:
                src = await v.get_attribute("src")
                if src and ("http" in src or "rtsp" in src):
                    if src not in found_streams and any(ext in src.lower() for ext in [".m3u8", ".mp4", ".webm", ".ts", ".mkv", ".flv", ".ism/manifest"]):
                        found_streams.append(src)
        except Exception as e:
            print(f"[WARNING] Gagal memuat {page_url}: {e}")
        finally:
            await context.close()
            if own_browser:
                await browser.close()
                if p_instance:
                    await p_instance.stop()
    except Exception as e:
        print(f"[ERROR] scan_website_url error: {e}")

    print(f"[FOUND] Ditemukan {len(found_streams)} stream URL dari {page_url}")
    return found_streams


async def discover_streams(custom_urls: list = None):
    print("=" * 60)
    print("  OmniCCTV - Multi-Source Stream Discoverer")
    print("=" * 60)

    # Inisialisasi browser reusable sekali saja agar scan cepat & efisien
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)

    all_streams = []
    stream_urls_seen = set()

    # 1. Fetch 150+ CCTV Jogjakota API
    kota_streams = await fetch_jogjakota_api()
    for s in kota_streams:
        u = s.get("stream_url")
        if u and u not in stream_urls_seen:
            stream_urls_seen.add(u)
            all_streams.append(s)

    # 2. Fetch 600+ CCTV Jogjaprov API (otomatis include jika custom_urls kosong atau berisi jogjaprov)
    prov_streams = await fetch_jogjaprov_api(browser=browser)
    for s in prov_streams:
        u = s.get("stream_url")
        if u and u not in stream_urls_seen:
            stream_urls_seen.add(u)
            all_streams.append(s)

    # 2b. Fetch 250+ CCTV Aktif Surabaya API (http://36.66.208.101:5000/)
    sby_streams = await fetch_surabaya_api()
    for s in sby_streams:
        u = s.get("stream_url")
        if u and u not in stream_urls_seen:
            stream_urls_seen.add(u)
            all_streams.append(s)

    # 2c. Fetch CCTV Aktif Bandung Kab, Bandung Barat (KBB), Cimahi, dan Kota Malang
    for fetcher in (fetch_bandungkab_api, fetch_bandungbarat_api, fetch_cimahi_api, fetch_malangkota_api):
        extra_streams = await fetcher()
        for s in extra_streams:
            u = s.get("stream_url")
            if u and u not in stream_urls_seen:
                stream_urls_seen.add(u)
                all_streams.append(s)

    # 3. Append existing manual / custom CCTV dari file config lama
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                old_list = json.load(f)
                for item in old_list:
                    u = item.get("stream_url")
                    if u and u not in stream_urls_seen:
                        stream_urls_seen.add(u)
                        all_streams.append(item)
        except Exception:
            pass

    newly_found = 0
    if custom_urls:
        for idx, url in enumerate(custom_urls, 1):
            url = url.strip()
            if not url or not url.startswith("http"):
                continue

            # Jika sudah di-handle oleh API resmi, lewati agar tidak dobel scan
            if any(d in url for d in [
                "cctv.jogjaprov.go.id",
                "36.66.208.101:5000",
                "dishub.bandungkab.go.id",
                "atcs.bandungbaratkab.go.id",
                "smartcity.cimahikota.go.id",
                "cctvsurabaya.24hour.id",
                "cctv.malangkota.go.id",
            ]):
                continue

            # Jika langsung berupa URL stream (.m3u8 / .mp4 / rtsp)
            if any(ext in url.lower() for ext in [".m3u8", ".mp4", ".ts", ".mkv", "rtsp://"]):
                if url not in stream_urls_seen:
                    cid = f"custom_{len(all_streams)+1:03d}"
                    all_streams.append({
                        "id": cid,
                        "name": f"Custom Stream {idx}",
                        "location": "Online / Custom",
                        "city": "Global",
                        "country": "Live Stream",
                        "stream_url": url,
                        "enabled": True,
                        "source": "custom_link"
                    })
                    stream_urls_seen.add(url)
                    newly_found += 1
            else:
                # Scan website HTML & network packets via browser
                streams = await scan_website_url(url, browser=browser)
                domain = url.split("/")[2].replace("www.", "")
                source_meta = {
                    "dishub.kedirikota.go.id": ("Indonesia", "Kediri", "Kota Kediri"),
                    "www.mlit.go.jp": ("Japan", "Japan", "Japan Road Camera"),
                    "highwaytraffic.go.th": ("Thailand", "Thailand", "Thailand Highway"),
                    "traffic.bangkok.go.th": ("Thailand", "Bangkok", "Bangkok"),
                    "transport.mos.ru": ("Russia", "Moscow", "Moscow"),
                    "onemotoring.lta.gov.sg": ("Singapore", "Singapore", "Singapore"),
                    "nationalhighways.co.uk": ("United Kingdom", "England", "National Highways"),
                    "www.livetraffic.com": ("Australia", "New South Wales", "Live Traffic NSW"),
                    "www.fl511.com": ("United States", "Florida", "Florida 511"),
                }
                country, city, location = source_meta.get(domain, ("Live Webcams", "Global", domain.title()))
                for s_idx, stream_url in enumerate(streams, 1):
                    if stream_url not in stream_urls_seen:
                        cid = f"custom_{len(all_streams)+1:03d}"
                        all_streams.append({
                            "id": cid,
                            "name": f"CCTV {domain} #{s_idx}",
                            "location": location,
                            "city": city,
                            "country": country,
                            "stream_url": stream_url,
                            "enabled": True,
                            "source": domain
                        })
                        stream_urls_seen.add(stream_url)
                        newly_found += 1

    try:
        await browser.close()
        await p.stop()
    except Exception:
        pass

    initial_count = 0
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                initial_count = len(json.load(f))
        except Exception:
            pass

    # Simpan ke config file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_streams, f, indent=2, ensure_ascii=False)

    final_count = len(all_streams)
    newly_added = max(0, final_count - initial_count)
    print(f"[OK] Total {final_count} CCTV tersimpan di {OUTPUT_FILE} (Baru ditambahkan: {newly_added})")
    return {"total": final_count, "newly_found": newly_added}


if __name__ == "__main__":
    test_urls = [
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
        # Sumber resmi internasional: scanner hanya menyimpan feed yang benar-benar
        # terlihat di jaringan browser. Portal snapshot tetap disimpan sebagai sumber
        # rujukan, tetapi tidak dipaksa menjadi video stream.
        "https://www.mlit.go.jp/road/bosai/LIVEcamera.html",
        "https://highwaytraffic.go.th/DOHMobile/Modules/CCTV.aspx",
        "https://traffic.bangkok.go.th/",
        "https://transport.mos.ru/mostrans/cameras",
        "https://onemotoring.lta.gov.sg/content/onemotoring/home/driving/traffic_information.html",
        "https://nationalhighways.co.uk/roads-and-travel/live-travel-updates/",
        "https://www.livetraffic.com/",
        "https://www.fl511.com/"
    ]
    asyncio.run(discover_streams(test_urls))

