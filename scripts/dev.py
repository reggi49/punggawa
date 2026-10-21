#!/usr/bin/env python3
"""Launcher terpadu Punggawa (Server, Worker, dan Web)."""
import os
import signal
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

processes = []

def cleanup(signum=None, frame=None):
    print("\n🛑 Menghentikan seluruh proses Punggawa...")
    for p in processes:
        if p.poll() is None:
            try:
                # Mematikan seluruh process group (termasuk subproses node/vite)
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except Exception:
                p.terminate()
    time.sleep(1)
    for p in processes:
        if p.poll() is None:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception:
                p.kill()
    print("✨ Semua proses berhasil dibersihkan.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def start_process(cmd, cwd, env=None):
    # preexec_fn=os.setsid membuat process group baru agar bisa dihentikan total
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env or os.environ.copy(),
        preexec_fn=os.setsid
    )

def main():
    print("🚀 Menjalankan ekosistem Punggawa...")

    # 1. Jalankan FastAPI Streaming Gateway dengan deteksi port pintar
    from config.port_utils import find_available_port
    from config.settings import settings

    stream_port = find_available_port(
        preferred_port=settings.STREAM_SERVER_PORT,
        fallback_ports=[8001, 8002, 8003, 8080, 8081, 8888],
        host=settings.STREAM_SERVER_HOST,
    )
    if stream_port != settings.STREAM_SERVER_PORT:
        print(f"⚠️  Port {settings.STREAM_SERVER_PORT} sedang digunakan proses lain.")
        print(f"🔄 Mengalihkan Streaming Gateway ke port alternatif: {stream_port}")

    print(f"📡 [1/3] Memulai Streaming Gateway Server di port {stream_port}...")
    server_env = os.environ.copy()
    server_env["STREAM_SERVER_PORT"] = str(stream_port)
    processes.append(start_process([VENV_PYTHON, "scripts/visualizer_server.py"], PROJECT_ROOT, env=server_env))
    time.sleep(1.5)

    # 2. Jalankan Autonomous Worker
    print("⚙️  [2/3] Memulai Background Worker Runner...")
    processes.append(start_process([VENV_PYTHON, "-m", "workers.runner"], PROJECT_ROOT))

    # 3. Jalankan Web UI
    web_dir = os.path.join(PROJECT_ROOT, "web")
    if os.path.exists(web_dir):
        # Cek ketersediaan port Vite (5173)
        web_port = find_available_port(
            preferred_port=5173,
            fallback_ports=[5174, 5175, 5176, 3000, 3001],
            host="0.0.0.0",
        )
        if web_port != 5173:
            print(f"⚠️  Port 5173 sedang dipakai. Vite akan menggunakan port {web_port}")

        print(f"🎨 [3/3] Memulai Web 3D Visualizer (Vite) di port {web_port}...")
        web_env = os.environ.copy()
        web_env["VITE_STREAM_SERVER_PORT"] = str(stream_port)
        processes.append(start_process(["npm", "run", "dev", "--", "--port", str(web_port)], web_dir, env=web_env))

    print("\n✅ Seluruh sistem Punggawa aktif!")
    print(f"👉 Akses visualizer: http://localhost:{web_port if 'web_port' in locals() else 5173}")
    print(f"👉 Streaming Gateway API: http://localhost:{stream_port}/api/health")
    print("Tekan Ctrl + C kapan saja untuk mematikan semua proses.\n")

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()