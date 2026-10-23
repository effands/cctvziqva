"""
Flask Web Server API & Video Streaming Gateway
=============================================
Menyediakan REST API & Interface Web Dashboard yang super user-friendly
untuk mengontrol OmniCCTV - Global Stream & Auto Recorder, memutar live preview, serta memutar rekaman.
"""

import json
import os
import shutil
import threading
import tempfile
import urllib.request
import subprocess
import sys
import re
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request, send_from_directory
from version import APP_VERSION, GITHUB_RELEASES_API, UPDATE_ASSET_NAME
try:
    from flask_cors import CORS
except ImportError:
    CORS = None

from recorder_engine import CCTVRecorder, CONFIG_FILE, RECORDINGS_DIR, BACKUP_DIR, LOGS_DIR

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
if CORS:
    CORS(app)
else:
    @app.after_request
    def add_cors_headers(response):
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        return response

recorder = CCTVRecorder()

# HTML & Modern Dashboard Template (Single Page Application - Glassmorphism UI)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OmniCCTV - Global Stream & Auto Recorder</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <!-- HLS.js Video Player -->
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .glow-green { box-shadow: 0 0 15px rgba(34, 197, 94, 0.4); }
        .glow-red { box-shadow: 0 0 15px rgba(239, 68, 68, 0.4); }
    </style>
</head>
<body class="min-h-screen flex flex-col">

    <!-- Navbar Header -->
    <header class="glass sticky top-0 z-50 px-6 py-4 flex flex-wrap justify-between items-center border-b border-slate-700">
        <div class="flex items-center space-x-3">
            <div class="bg-gradient-to-tr from-red-600 to-amber-500 p-2.5 rounded-xl text-white shadow-lg animate-pulse">
                <i class="fa-solid fa-video text-xl"></i>
            </div>
            <div>
                <h1 class="text-xl font-bold bg-gradient-to-r from-red-400 via-orange-300 to-yellow-400 bg-clip-text text-transparent">
                    OmniCCTV
                </h1>
                <p class="text-xs text-slate-400">Global Stream & Auto Recorder • Multi-Camera Hub</p>
            </div>
        </div>

        <div class="flex items-center space-x-3 mt-3 sm:mt-0">
            <!-- Global Controls -->
            <button onclick="scanStreams()" id="btn-scan" class="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 transition shadow-md">
                <i class="fa-solid fa-radar"></i> <span>Auto Scan URL</span>
            </button>
            <button onclick="startAll()" class="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 transition shadow-md">
                <i class="fa-solid fa-play"></i> <span>Mulai Semua</span>
            </button>
            <button onclick="stopAll()" class="bg-rose-600 hover:bg-rose-500 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 transition shadow-md">
                <i class="fa-solid fa-stop"></i> <span>Hentikan Semua</span>
            </button>
            <button onclick="openAddModal()" title="Tambah Manual" class="bg-slate-700 hover:bg-slate-600 text-white px-3 py-2 rounded-lg text-sm font-medium transition">
                <i class="fa-solid fa-plus"></i>
            </button>
        </div>
    </header>

    <!-- System Stats Bar -->
    <div class="bg-slate-900 border-b border-slate-800 px-6 py-2.5 flex flex-wrap justify-between items-center text-xs text-slate-400">
        <div class="flex space-x-6">
            <span><i class="fa-solid fa-layer-group text-slate-500 mr-1.5"></i> Total CCTV: <strong id="stat-total" class="text-white">0</strong></span>
            <span><i class="fa-solid fa-record-vinyl text-red-500 mr-1.5 animate-spin"></i> Aktif Merekam: <strong id="stat-active" class="text-emerald-400">0</strong></span>
        </div>
        <div class="flex space-x-6 mt-1 sm:mt-0">
            <span><i class="fa-solid fa-hard-drive text-slate-500 mr-1.5"></i> Disk Free: <strong id="stat-disk" class="text-sky-400">-</strong></span>
            <span><i class="fa-solid fa-circle text-emerald-500 mr-1 text-[10px]"></i> Server Status: <strong class="text-slate-200">Online</strong></span>
        </div>
    </div>

    <!-- Main Grid Content -->
    <main class="flex-1 p-6 max-w-7xl mx-auto w-full">
        <!-- Section Header -->
        <div class="flex justify-between items-center mb-6">
            <h2 class="text-lg font-semibold text-slate-200 flex items-center">
                <i class="fa-solid fa-tv text-slate-400 mr-2"></i> Monitor Stream & Kontrol Live
            </h2>
            <div class="text-xs text-slate-400">
                Refresh otomatis setiap 3 detik
            </div>
        </div>

        <!-- Grid Cards CCTV -->
        <div id="cctv-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <!-- Loading placeholder -->
            <div class="col-span-full text-center py-20 text-slate-500">
                <i class="fa-solid fa-circle-notch fa-spin text-3xl mb-3 text-red-500"></i>
                <p>Memuat daftar kamera CCTV...</p>
            </div>
        </div>
    </main>

    <!-- Modal Video Player / Live Preview -->
    <div id="video-modal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
        <div class="glass w-full max-w-3xl rounded-2xl overflow-hidden shadow-2xl border border-slate-700">
            <div class="px-5 py-3 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
                <h3 id="modal-title" class="font-bold text-slate-200">Live Preview</h3>
                <button onclick="closeModal()" class="text-slate-400 hover:text-white text-lg"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="relative aspect-video bg-black flex items-center justify-center">
                <video id="player" class="w-full h-full" controls autoplay muted></video>
            </div>
        </div>
    </div>

    <!-- Modal Tambah CCTV -->
    <div id="add-modal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
        <div class="glass w-full max-w-md rounded-2xl p-6 shadow-2xl border border-slate-700">
            <h3 class="text-lg font-bold text-slate-200 mb-4">Tambah Stream Kamera CCTV</h3>
            <div class="space-y-4">
                <div>
                    <label class="text-xs font-semibold text-slate-400 block mb-1">Nama Kamera / Lokasi</label>
                    <input type="text" id="add-name" placeholder="Contoh: Simpang Tugu Jogja" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-red-500">
                </div>
                <div>
                    <label class="text-xs font-semibold text-slate-400 block mb-1">URL Stream (.m3u8 / RTSP)</label>
                    <input type="text" id="add-url" placeholder="https://domain.com/hls/live.m3u8" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-red-500">
                </div>
            </div>
            <div class="flex justify-end space-x-3 mt-6">
                <button onclick="closeAddModal()" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">Batal</button>
                <button onclick="saveNewCamera()" class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-semibold rounded-lg text-sm">Simpan Kamera</button>
            </div>
        </div>
    </div>

    <!-- Toast Notifications Container -->
    <div id="toast-container" class="fixed bottom-5 right-5 z-50 space-y-2"></div>

    <script>
        let hlsPlayer = null;

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                renderCards(data.cctvs, data.statuses);

                document.getElementById('stat-total').innerText = data.cctvs.length;
                document.getElementById('stat-active').innerText = data.active_count;
                document.getElementById('stat-disk').innerText = data.disk_free;
            } catch (err) {
                console.error("Error fetching status:", err);
            }
        }

        let currentPage = 1;
        const pageSize = 12;
        let cachedCctvs = [];
        let cachedStatuses = {};

        function renderCards(cctvs, statuses) {
            cachedCctvs = cctvs;
            cachedStatuses = statuses;
            drawPage();
        }

        function drawPage() {
            const grid = document.getElementById('cctv-grid');
            if (!cachedCctvs || cachedCctvs.length === 0) {
                grid.innerHTML = `
                    <div class="col-span-full text-center py-20 glass rounded-2xl">
                        <i class="fa-solid fa-video-slash text-4xl text-slate-600 mb-3"></i>
                        <p class="text-slate-400">Belum ada CCTV terdaftar.</p>
                        <button onclick="openAddModal()" class="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm">Tambah Kamera Pertama</button>
                    </div>`;
                return;
            }

            const totalPages = Math.ceil(cachedCctvs.length / pageSize);
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;

            const startIdx = (currentPage - 1) * pageSize;
            const endIdx = startIdx + pageSize;
            const pageItems = cachedCctvs.slice(startIdx, endIdx);

            let html = pageItems.map(cam => {
                const st = cachedStatuses[cam.id] || { is_recording: false, bytes_recorded: 0, current_file: '' };
                const isRec = st.is_recording;
                const sizeMb = (st.bytes_recorded / 1024 / 1024).toFixed(1);

                return `
                <div class="glass rounded-2xl overflow-hidden flex flex-col justify-between transition hover:border-slate-500 ${isRec ? 'glow-green border-emerald-500/50' : ''}">
                    <div class="p-5">
                        <div class="flex justify-between items-start mb-2">
                            <div>
                                <h3 class="font-bold text-slate-100 text-base flex items-center">
                                    ${cam.name}
                                </h3>
                                <p class="text-xs text-slate-400 mt-0.5"><i class="fa-solid fa-location-dot mr-1"></i> ${cam.location || 'Yogyakarta'}</p>
                            </div>
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wide uppercase flex items-center space-x-1 ${isRec ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30 animate-pulse' : 'bg-slate-800 text-slate-400'}">
                                <i class="fa-solid fa-circle text-[8px] mr-1 ${isRec ? 'text-emerald-400' : 'text-slate-500'}"></i>
                                ${isRec ? 'REC' : 'IDLE'}
                            </span>
                        </div>

                        <!-- Stats Box -->
                        <div class="bg-slate-900/60 rounded-xl p-3 my-3 text-xs space-y-1.5 border border-slate-800">
                            <div class="flex justify-between">
                                <span class="text-slate-500">File Output:</span>
                                <span class="text-slate-300 font-mono truncate max-w-[180px]">${st.current_file || '-'}</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-slate-500">Ukuran Terrekam:</span>
                                <span class="text-emerald-400 font-semibold">${sizeMb} MB</span>
                            </div>
                        </div>
                    </div>

                    <!-- Action Controls -->
                    <div class="px-5 py-3 bg-slate-800/40 border-t border-slate-700/50 flex justify-between items-center">
                        <div class="flex space-x-2">
                            ${isRec ? 
                                `<button onclick="stopStream('${cam.id}')" class="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1">
                                    <i class="fa-solid fa-square text-[10px]"></i> <span>Stop</span>
                                 </button>` :
                                `<button onclick="startStream('${cam.id}')" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1">
                                    <i class="fa-solid fa-play text-[10px]"></i> <span>Record</span>
                                 </button>`
                            }
                            <button onclick="previewStream('${cam.name}', '${cam.stream_url}')" class="px-3.5 h-8 bg-gradient-to-r from-rose-600 via-red-600 to-rose-700 hover:from-rose-500 hover:to-red-500 text-white font-semibold rounded-lg text-xs inline-flex items-center justify-center gap-1.5 transition shadow-md shadow-rose-950/40">
                                <i class="fa-solid fa-play text-[10px] leading-none translate-y-[0.5px]"></i> <span class="leading-none">Stream</span>
                            </button>
                        </div>
                        <button onclick="deleteCam('${cam.id}')" class="text-slate-500 hover:text-rose-400 text-xs p-1.5">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>`;
            }).join('');

            // Add Pagination Bar at bottom
            html += `
            <div class="col-span-full flex justify-between items-center bg-slate-900/80 p-4 rounded-xl border border-slate-800 mt-4">
                <span class="text-xs text-slate-400">Menampilkan ${startIdx + 1} - ${Math.min(endIdx, cachedCctvs.length)} dari ${cachedCctvs.length} CCTV</span>
                <div class="flex space-x-2">
                    <button onclick="changePage(-1)" ${currentPage === 1 ? 'disabled' : ''} class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs rounded-lg font-medium">← Prev</button>
                    <span class="px-3 py-1.5 text-xs text-slate-300 font-semibold">Hal ${currentPage} / ${totalPages}</span>
                    <button onclick="changePage(1)" ${currentPage === totalPages ? 'disabled' : ''} class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs rounded-lg font-medium">Next →</button>
                </div>
            </div>`;

            grid.innerHTML = html;
        }

        function changePage(delta) {
            currentPage += delta;
            drawPage();
        }

        async function startStream(id) {
            await fetch(`/api/stream/start/${id}`, { method: 'POST' });
            showToast("Memulai perekaman stream...");
            fetchStatus();
        }

        async function stopStream(id) {
            await fetch(`/api/stream/stop/${id}`, { method: 'POST' });
            showToast("Perekaman dihentikan.");
            fetchStatus();
        }

        async function startAll() {
            await fetch('/api/stream/start_all', { method: 'POST' });
            showToast("Semua perekaman CCTV dimulai!");
            fetchStatus();
        }

        async function stopAll() {
            await fetch('/api/stream/stop_all', { method: 'POST' });
            showToast("Semua perekaman CCTV dihentikan.");
            fetchStatus();
        }

        function previewStream(name, url) {
            if (!url) {
                alert("URL Stream belum dikonfigurasi.");
                return;
            }
            document.getElementById('modal-title').innerText = "Live Stream: " + name;
            document.getElementById('video-modal').classList.remove('hidden');

            const video = document.getElementById('player');
            if (Hls.isSupported()) {
                if (hlsPlayer) hlsPlayer.destroy();
                hlsPlayer = new Hls();
                hlsPlayer.loadSource(url);
                hlsPlayer.attachMedia(video);
                hlsPlayer.on(Hls.Events.MANIFEST_PARSED, () => video.play());
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = url;
                video.play();
            }
        }

        function closeModal() {
            document.getElementById('video-modal').classList.add('hidden');
            const video = document.getElementById('player');
            video.pause();
            if (hlsPlayer) hlsPlayer.destroy();
        }

        function openAddModal() { document.getElementById('add-modal').classList.remove('hidden'); }
        function closeAddModal() { document.getElementById('add-modal').classList.add('hidden'); }

        async function saveNewCamera() {
            const name = document.getElementById('add-name').value;
            const url = document.getElementById('add-url').value;

            if (!name || !url) {
                alert("Mohon isi Nama dan URL Stream.");
                return;
            }

            await fetch('/api/cctv/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, stream_url: url })
            });

            closeAddModal();
            showToast("Kamera baru berhasil ditambahkan!");
            fetchStatus();
        }

        async function deleteCam(id) {
            if (confirm("Apakah Anda yakin ingin menghapus CCTV ini?")) {
                await fetch(`/api/cctv/delete/${id}`, { method: 'DELETE' });
                showToast("Kamera dihapus.");
                fetchStatus();
            }
        }

        function showToast(msg) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'glass bg-slate-800 text-slate-200 px-4 py-2.5 rounded-xl shadow-xl text-xs font-medium flex items-center space-x-2 border border-slate-700 border-l-4 border-l-emerald-500 animate-bounce';
            toast.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> <span>${msg}</span>`;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 3500);
        }

        async function scanStreams() {
            const btn = document.getElementById('btn-scan');
            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> <span>Scanning...</span>`;
            
            try {
                const res = await fetch('/api/scan', { method: 'POST' });
                const data = await res.json();
                alert("✅ Pemindaian Berhasil!\n\nDitemukan " + (data.count || 0) + " stream CCTV Jogja.");
                await fetchStatus();
            } catch (err) {
                alert("❌ Gagal melakukan pemindaian stream CCTV.");
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<i class="fa-solid fa-radar"></i> <span>Auto Scan URL</span>`;
            }
        }

        // Auto polling status
        fetchStatus();
        setInterval(fetchStatus, 3000);
    </script>
</body>
</html>
"""

from recorder_engine import CCTVRecorder, CONFIG_FILE, OFFLINE_CONFIG_FILE, RECORDINGS_DIR, BACKUP_DIR, LOGS_DIR, load_settings, save_settings

@app.route("/")
def index():
    from flask import render_template, make_response
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.route("/api/update/check", methods=["GET"])
def check_update():
    """Check the latest public GitHub release without changing local files."""
    try:
        req = urllib.request.Request(GITHUB_RELEASES_API, headers={"User-Agent": "CCTV-ZIQVA-Updater"})
        with urllib.request.urlopen(req, timeout=10) as response:
            release = json.loads(response.read().decode("utf-8"))
        tag = str(release.get("tag_name", "")).lstrip("v")
        asset = next((a for a in release.get("assets", []) if a.get("name") == UPDATE_ASSET_NAME), None)
        return jsonify({"status": "ok", "current_version": APP_VERSION, "latest_version": tag,
                        "update_available": bool(asset and tag and tag != APP_VERSION),
                        "asset_name": UPDATE_ASSET_NAME, "release_url": release.get("html_url", "")})
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Gagal mengecek update: {exc}", "current_version": APP_VERSION}), 502

@app.route("/api/update/install", methods=["POST"])
def install_update():
    """Download the verified release installer and launch it after stopping recording."""
    try:
        req = urllib.request.Request(GITHUB_RELEASES_API, headers={"User-Agent": "CCTV-ZIQVA-Updater"})
        with urllib.request.urlopen(req, timeout=10) as response:
            release = json.loads(response.read().decode("utf-8"))
        tag = str(release.get("tag_name", "")).lstrip("v")
        asset = next((a for a in release.get("assets", []) if a.get("name") == UPDATE_ASSET_NAME), None)
        if not asset or not tag or tag == APP_VERSION:
            return jsonify({"status": "noop", "message": "CCTV ZIQVA sudah menggunakan versi terbaru."})
        if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.\-_]*", tag):
            return jsonify({"status": "error", "message": "Versi release tidak valid."}), 400
        target = Path(tempfile.gettempdir()) / f"CCTV_ZIQVA_Setup_{tag}.exe"
        download = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "CCTV-ZIQVA-Updater"})
        with urllib.request.urlopen(download, timeout=120) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        recorder.stop_all()
        subprocess.Popen([str(target)], close_fds=True)
        threading.Thread(target=lambda: (threading.Event().wait(2), os._exit(0)), daemon=True).start()
        return jsonify({"status": "started", "version": tag})
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Update gagal: {exc}"}), 502

@app.route("/api/scan", methods=["POST"])
def trigger_scan():
    import discover_streams
    import asyncio
    data = request.json or {}
    custom_urls = data.get("urls", [])
    
    if custom_urls:
        st = load_settings()
        existing = st.get("saved_website_urls", [])
        updated = list(existing)
        for u in custom_urls:
            u_clean = u.strip()
            if u_clean and u_clean not in updated:
                updated.append(u_clean)
        st["saved_website_urls"] = updated
        save_settings(st)
    
    try:
        res_dict = asyncio.run(discover_streams.discover_streams(custom_urls=custom_urls))
        # Cek ulang daftar CCTV OFF: jika saat di-scan sudah aktif (ON), otomatis kembalikan ke daftar ON!
        health_res = recorder.run_health_scan(mode="offline_only")
        recorder.reload_config()
        if isinstance(res_dict, dict):
            return jsonify({
                "status": "ok",
                "count": health_res.get("online_total", res_dict.get("total", 0)),
                "newly_found": res_dict.get("newly_found", 0) + health_res.get("moved_to_on", 0),
                "recovered_from_off": health_res.get("moved_to_on", 0)
            })
        else:
            return jsonify({"status": "ok", "count": len(res_dict), "newly_found": 0})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Gagal melakukan pemindaian stream CCTV: {str(e)}"}), 500

@app.route("/api/browse_folder", methods=["POST"])
def browse_folder():
    """Buka dialog native Windows Folder Picker agar user bisa memilih folder secara visual"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        selected_path = []
        def ask_dir():
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory(title="Pilih Folder Penyimpanan")
            root.destroy()
            selected_path.append(folder)

        # Jalankan di main thread / thread terpisah
        t = threading.Thread(target=ask_dir)
        t.start()
        t.join(timeout=60)

        path = selected_path[0] if selected_path else ""
        if path:
            return jsonify({"status": "ok", "path": path})
        return jsonify({"status": "cancelled", "path": ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings/default", methods=["GET"])
def get_default_settings():
    """Mengembalikan path default bawaan aplikasi"""
    return jsonify({
        "default_recordings_dir": str(RECORDINGS_DIR.resolve())
    })

@app.route("/api/settings", methods=["GET", "POST"])
def manage_settings():
    if request.method == "POST":
        data = request.json or {}
        st = load_settings()
        if "recordings_dir" in data and data["recordings_dir"]:
            st["recordings_dir"] = data["recordings_dir"]
        if "backup_dir" in data and data["backup_dir"]:
            st["backup_dir"] = data["backup_dir"]
        if "saved_website_urls" in data:
            st["saved_website_urls"] = data["saved_website_urls"]
        if "segment_duration_minutes" in data:
            try:
                st["segment_duration_minutes"] = int(data["segment_duration_minutes"])
            except ValueError:
                pass
        if "auto_record_enabled" in data:
            st["auto_record_enabled"] = bool(data["auto_record_enabled"])
        if "auto_record_duration_minutes" in data:
            try:
                st["auto_record_duration_minutes"] = max(0.1, float(data["auto_record_duration_minutes"]))
            except (ValueError, TypeError):
                pass
        if "auto_record_repeat_count" in data:
            try:
                st["auto_record_repeat_count"] = max(0, int(data["auto_record_repeat_count"]))
            except (ValueError, TypeError):
                pass
        if "auto_record_interval_seconds" in data:
            try:
                st["auto_record_interval_seconds"] = max(0, int(data["auto_record_interval_seconds"]))
            except (ValueError, TypeError):
                pass
        if "folder_organization" in data:
            val = str(data["folder_organization"]).strip().lower()
            if val in ("single", "per_session", "per_camera"):
                st["folder_organization"] = val
            else:
                st["folder_organization"] = "single"
        if "auto_record_camera_mode" in data:
            st["auto_record_camera_mode"] = str(data["auto_record_camera_mode"])
        if "auto_record_camera_count" in data:
            try:
                st["auto_record_camera_count"] = max(1, int(data["auto_record_camera_count"]))
            except (ValueError, TypeError):
                pass
        if "auto_record_area" in data:
            area = str(data["auto_record_area"]).strip().lower()
            if area in ("all", "malang", "surabaya", "yogyakarta", "india"):
                st["auto_record_area"] = area
        if "auto_record_selected_cams" in data:
            st["auto_record_selected_cams"] = list(data["auto_record_selected_cams"])

        save_settings(st)
        recorder.auto_scheduler.load_from_settings()
        return jsonify({"status": "ok", "settings": st})
    else:
        st = load_settings()
        return jsonify(st)

@app.route("/api/open_folder", methods=["GET", "POST"])
def open_folder():
    import subprocess
    st = load_settings()
    base_rec_dir = Path(st.get("recordings_dir", str(RECORDINGS_DIR)))
    
    # 1 Folder saja untuk semua hasil rekaman
    target_dir = base_rec_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_str = str(target_dir.resolve())
    
    try:
        if os.name == "nt":
            try:
                os.startfile(target_str)
            except Exception:
                subprocess.Popen(["explorer", target_str])
        else:
            subprocess.Popen(["xdg-open", target_str])
        return jsonify({"status": "ok", "path": target_str})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/status", methods=["GET"])
def get_status():
    configs = []
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                configs = json.load(f)
        except Exception:
            pass

    statuses = recorder.get_all_status()
    statuses_dict = {}
    active_count = 0
    for cid, st in statuses.items():
        if st.is_recording:
            active_count += 1
        statuses_dict[cid] = {
            "is_recording": st.is_recording,
            "is_error": st.is_error,
            "error_msg": st.error_msg,
            "bytes_recorded": st.bytes_recorded,
            "current_file": st.current_file,
            "start_time": st.start_time.isoformat() if st.start_time else None
        }

    usage = CCTVRecorder.get_disk_usage()
    free_gb = f"{usage['free'] / (1024**3):.1f} GB"
    st_conf = load_settings()
    auto_status = recorder.auto_scheduler.get_status()
    active_auto_ids = auto_status.get("active_camera_ids", []) if auto_status.get("is_running") else []

    for idx, cam in enumerate(configs):
        cam["catalog_index"] = idx

    def _cam_sort_key(cam):
        cid = cam.get("id", "")
        is_rec = bool(statuses_dict.get(cid, {}).get("is_recording")) or (cid in active_auto_ids)
        auto_pos = active_auto_ids.index(cid) if cid in active_auto_ids else 999999
        return (0 if is_rec else 1, auto_pos, cam.get("catalog_index", 0))

    configs.sort(key=_cam_sort_key)
    offline_configs = recorder.load_offline_configs()

    return jsonify({
        "cctvs": configs,
        "offline_cctvs": offline_configs,
        "offline_count": len(offline_configs),
        "statuses": statuses_dict,
        "active_count": active_count,
        "disk_free": free_gb,
        "recordings_dir": st_conf.get("recordings_dir", str(RECORDINGS_DIR)),
        "segment_duration_minutes": st_conf.get("segment_duration_minutes", 60),
        "auto_record": auto_status,
        "settings": st_conf
    })

@app.route("/api/auto_record/start", methods=["POST"])
def start_auto_record():
    data = request.json or {}
    if data:
        st = load_settings()
        for k in ["auto_record_duration_minutes", "auto_record_repeat_count",
                  "auto_record_interval_seconds", "auto_record_camera_mode",
                  "auto_record_camera_count", "auto_record_selected_cams", "auto_record_area"]:
            if k in data:
                st[k] = data[k]
        save_settings(st)

    recorder.auto_scheduler.start(config_override=data)
    return jsonify({"status": "ok", "auto_record": recorder.auto_scheduler.get_status()})

@app.route("/api/auto_record/stop", methods=["POST"])
def stop_auto_record():
    recorder.auto_scheduler.stop()
    return jsonify({"status": "ok", "auto_record": recorder.auto_scheduler.get_status()})

@app.route("/api/auto_record/status", methods=["GET"])
def get_auto_record_status():
    return jsonify(recorder.auto_scheduler.get_status())

@app.route("/api/stream/start/<cctv_id>", methods=["POST"])
def start_stream(cctv_id):
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            configs = json.load(f)
        for cam in configs:
            if cam["id"] == cctv_id:
                if recorder.is_stream_online(cam.get("stream_url", "")):
                    recorder.start_stream(cam["id"], cam["stream_url"], skip_precheck=True)
                    return jsonify({"status": "ok", "switched": False, "cam_id": cam["id"], "cam_name": cam.get("name", cam["id"])})
                else:
                    # Pindahkan kamera yang mati ke Menu CCTV OFF & alihkan ke kamera lain yang online
                    recorder.move_to_offline(cctv_id, reason="Offline saat mulai rekam manual")
                    valid_cams = [c for c in configs if c.get("enabled", True) and c.get("stream_url") and c.get("id") != cctv_id]
                    active_ids = {cid for cid, st in recorder.get_all_status().items() if st.is_recording}
                    replacement = recorder.auto_scheduler._pick_single_online_replacement(valid_cams, active_ids | {cctv_id})
                    if replacement:
                        recorder.start_stream(replacement["id"], replacement["stream_url"], skip_precheck=True)
                        return jsonify({
                            "status": "ok",
                            "switched": True,
                            "from_name": cam.get("name", cctv_id),
                            "cam_id": replacement["id"],
                            "cam_name": replacement.get("name", replacement["id"])
                        })
                    return jsonify({"error": f"Kamera '{cam.get('name', cctv_id)}' sedang offline (dipindahkan ke Menu CCTV OFF)."}), 503
    return jsonify({"error": "not found"}), 404

@app.route("/api/stream/stop/<cctv_id>", methods=["POST"])
def stop_stream(cctv_id):
    recorder.stop_stream(cctv_id)
    return jsonify({"status": "ok"})

@app.route("/api/stream/start_all", methods=["POST"])
def start_all():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            configs = json.load(f)
        recorder.start_all(configs)
    return jsonify({"status": "ok"})

@app.route("/api/stream/stop_all", methods=["POST"])
def stop_all():
    recorder.stop_all()
    return jsonify({"status": "ok"})

@app.route("/api/backup", methods=["POST"])
def do_backup():
    count = recorder.backup_recordings()
    return jsonify({"files_copied": count})

@app.route("/api/cctv/add", methods=["POST"])
def add_cctv():
    data = request.json or {}
    configs = []
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            configs = json.load(f)
    
    cid = f"cctv_manual_{int(time.time())}"
    stream_url = str(data.get("stream_url", "")).strip()
    is_on = recorder.is_stream_online(stream_url)
    new_cam = {
        "id": cid,
        "name": str(data.get("name", "CCTV Baru")).strip(),
        "location": str(data.get("location", "Manual")).strip(),
        "city": str(data.get("city", data.get("location", "Manual"))).strip(),
        "country": str(data.get("country", "Indonesia")).strip(),
        "stream_url": stream_url,
        "enabled": is_on,
        "source": "manual",
        "status_health": "online" if is_on else "offline",
        "offline_reason": "" if is_on else "Offline saat ditambahkan",
    }
    if is_on:
        configs.append(new_cam)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)
        recorder.reload_config()
    else:
        off_list = recorder.load_offline_configs()
        off_list.append(new_cam)
        recorder.save_offline_configs(off_list)
    
    return jsonify({"status": "ok", "cam": new_cam, "online": is_on})

@app.route("/api/cctv/edit/<cctv_id>", methods=["PUT", "POST"])
def edit_cctv(cctv_id):
    data = request.json or {}
    updated_cam = None

    # Cek di daftar ON (cctv_streams.json)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            configs = json.load(f)
        for cam in configs:
            if cam.get("id") == cctv_id:
                for k in ("name", "location", "city", "country", "stream_url"):
                    if k in data and str(data[k]).strip():
                        cam[k] = str(data[k]).strip()
                updated_cam = cam
                break
        if updated_cam:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(configs, f, indent=2, ensure_ascii=False)
            recorder.reload_config()
            return jsonify({"status": "ok", "cam": updated_cam, "list": "on"})

    # Cek di daftar OFF (cctv_offline.json)
    off_list = recorder.load_offline_configs()
    for cam in off_list:
        if cam.get("id") == cctv_id:
            for k in ("name", "location", "city", "country", "stream_url"):
                if k in data and str(data[k]).strip():
                    cam[k] = str(data[k]).strip()
            updated_cam = cam
            break
    if updated_cam:
        recorder.save_offline_configs(off_list)
        return jsonify({"status": "ok", "cam": updated_cam, "list": "off"})

    return jsonify({"error": "Kamera tidak ditemukan"}), 404

@app.route("/api/cctv/delete/<cctv_id>", methods=["DELETE", "POST"])
def delete_cctv(cctv_id):
    recorder.stop_stream(cctv_id)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            configs = json.load(f)
        new_configs = [c for c in configs if c.get("id") != cctv_id]
        if len(new_configs) != len(configs):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_configs, f, indent=2, ensure_ascii=False)
            recorder.reload_config()

    off_list = recorder.load_offline_configs()
    new_off = [c for c in off_list if c.get("id") != cctv_id]
    if len(new_off) != len(off_list):
        recorder.save_offline_configs(new_off)

    return jsonify({"status": "ok"})

@app.route("/api/cctv/delete_offline_bulk", methods=["POST"])
def delete_offline_bulk():
    """Hapus banyak / seluruh CCTV di daftar OFF sekaligus (CRUD Bulk Delete)"""
    data = request.json or {}
    mode = data.get("mode", "all")  # 'all', 'repeated' (fail_count >= 2), atau 'ids'
    ids_to_del = set(data.get("ids", []))
    off_list = recorder.load_offline_configs()
    before_count = len(off_list)

    if mode == "all":
        remaining = []
    elif mode == "repeated":
        remaining = [c for c in off_list if int(c.get("fail_count", 1)) < 2]
    elif mode == "ids":
        remaining = [c for c in off_list if c.get("id") not in ids_to_del]
    else:
        remaining = off_list

    recorder.save_offline_configs(remaining)
    deleted_count = before_count - len(remaining)
    return jsonify({"status": "ok", "deleted": deleted_count, "remaining": len(remaining)})

@app.route("/api/cctv/move_to_off/<cctv_id>", methods=["POST"])
def api_move_to_off(cctv_id):
    recorder.stop_stream(cctv_id)
    cam = recorder.move_to_offline(cctv_id, reason="Dipindahkan ke Menu OFF oleh pengguna")
    if cam:
        return jsonify({"status": "ok", "cam": cam})
    return jsonify({"error": "Kamera tidak ditemukan di daftar ON"}), 404

@app.route("/api/cctv/recheck/<cctv_id>", methods=["POST"])
def api_recheck_cctv(cctv_id):
    """
    Cek ulang 1 kamera (baik dari menu OFF maupun ON):
    - Jika ternyata ONLINE -> otomatis pindahkan ke daftar ON!
    - Jika masih OFFLINE -> tetap/pindahkan ke daftar OFF dengan fail_count bertambah.
    """
    off_list = recorder.load_offline_configs()
    target = next((c for c in off_list if c.get("id") == cctv_id), None)
    in_off = True

    if not target and CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            on_list = json.load(f)
        target = next((c for c in on_list if c.get("id") == cctv_id), None)
        in_off = False

    if not target:
        return jsonify({"error": "Kamera tidak ditemukan"}), 404

    is_on = recorder.is_stream_online(target.get("stream_url", ""), timeout=8)
    if is_on:
        if in_off:
            recorder.move_to_online(cctv_id)
        return jsonify({"status": "ok", "online": True, "cam_name": target.get("name", cctv_id)})
    else:
        if not in_off:
            recorder.stop_stream(cctv_id)
            recorder.move_to_offline(cctv_id, reason="Offline saat dicek ulang")
        else:
            from datetime import datetime
            target["fail_count"] = int(target.get("fail_count", 1)) + 1
            target["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            recorder.save_offline_configs(off_list)
        return jsonify({"status": "ok", "online": False, "cam_name": target.get("name", cctv_id), "fail_count": target.get("fail_count", 1)})

@app.route("/api/cctv/health_scan", methods=["POST"])
def api_health_scan():
    """
    Auto-Scanning seluruh CCTV:
    - Yang mati (OFF) otomatis dipindah ke Menu CCTV OFF
    - Yang ada di Menu CCTV OFF jika sudah aktif kembali otomatis masuk ke daftar ON!
    """
    data = request.json or {}
    mode = data.get("mode", "all")
    res = recorder.run_health_scan(mode=mode)
    return jsonify({"status": "ok", **res})

@app.route("/api/surabaya_hls/<sby_cctv_id>/<path:filename>", methods=["GET"])
def proxy_surabaya_hls(sby_cctv_id, filename):
    """
    Proxy & On-Demand Trigger untuk stream HLS Dishub Surabaya (http://36.66.208.101:5000)
    agar terbebas dari blokir CORS di browser dan otomatis menyalakan stream saat dibuka.
    """
    import time
    import urllib.request
    import urllib.error
    from flask import Response

    base_sby = "http://36.66.208.101:5000"
    target_url = f"{base_sby}/hls/{sby_cctv_id}/{filename}"
    headers = {"User-Agent": "Mozilla/5.0"}

    def fetch_remote():
        req = urllib.request.Request(target_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read(), resp.headers.get("Content-Type", "application/octet-stream")

    try:
        data, ctype = fetch_remote()
    except urllib.error.HTTPError as e:
        if e.code == 404 and filename.endswith(".m3u8"):
            # Aktifkan on-demand stream terlebih dahulu
            try:
                start_req = urllib.request.Request(
                    f"{base_sby}/api/start_stream/{sby_cctv_id}",
                    method="POST",
                    headers=headers
                )
                urllib.request.urlopen(start_req, timeout=15).read()
                for _ in range(8):
                    try:
                        data, ctype = fetch_remote()
                        break
                    except Exception:
                        time.sleep(0.5)
                else:
                    return jsonify({"error": "Stream belum siap"}), 404
            except Exception as ex:
                return jsonify({"error": str(ex)}), 502
        else:
            return jsonify({"error": str(e)}), e.code
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    if filename.endswith(".m3u8"):
        ctype = "application/vnd.apple.mpegurl"
    elif filename.endswith(".ts"):
        ctype = "video/mp2t"

    resp = Response(data, status=200, content_type=ctype)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@app.route("/api/malang_hls/<path:filename>", methods=["GET"])
def proxy_malang_hls(filename):
    """
    Proxy untuk stream HLS CCTV Kota Malang (https://cctv.malangkota.go.id/cctv-stream/streams/<filename>)
    dengan menyertakan cookie otentikasi nancy_auth_v1c secara otomatis.
    """
    import requests
    import urllib3
    from flask import Response
    urllib3.disable_warnings()

    target_url = f"https://cctv.malangkota.go.id/cctv-stream/streams/{filename}"
    ck = recorder._get_malang_cookie(force_refresh=False)
    headers = {
        "User-Agent": recorder.CHROME_UA,
        "Referer": "https://cctv.malangkota.go.id/",
    }
    if ck:
        headers["Cookie"] = ck

    try:
        r = requests.get(target_url, headers=headers, verify=False, timeout=10)
        if r.status_code == 403:
            ck = recorder._get_malang_cookie(force_refresh=True)
            if ck:
                headers["Cookie"] = ck
                r = requests.get(target_url, headers=headers, verify=False, timeout=10)
        if r.status_code != 200:
            return jsonify({"error": f"HTTP {r.status_code}"}), r.status_code
        ctype = "application/vnd.apple.mpegurl" if filename.endswith(".m3u8") else "video/mp2t"
        resp = Response(r.content, status=200, content_type=ctype)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/logs", methods=["GET"])
def get_logs():
    log_files = sorted(LOGS_DIR.glob("*.log"), key=os.path.getmtime, reverse=True)
    if log_files:
        try:
            with open(log_files[0], "r", encoding="utf-8") as f:
                lines = f.readlines()[-30:]
                return jsonify({"logs": lines})
        except Exception as e:
            return jsonify({"logs": [f"Error reading log: {e}"]})
    return jsonify({"logs": ["Belum ada berkas log perekaman."]})

if __name__ == "__main__":
    print("==================================================")
    print("  CCTV ZIQVA Web Dashboard Server (by team ziqva.com)")
    print("  Buka di Browser: http://localhost:8899")
    print("==================================================")
    app.run(host="0.0.0.0", port=8899, debug=False)
