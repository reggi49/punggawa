#!/usr/bin/env python3
"""Launcher terpadu untuk menjalankan seluruh ekosistem Punggawa lokal."""
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
    print("\n🛑 Mematikan seluruh proses Punggawa...")
    for p in processes:
        if p.poll() is None:
            p.terminate()
    time.sleep(1)
    for p in processes:
        if p.poll() is None:
            p.kill()
    print("✨ Semua proses berhasil dihentikan.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    print("🚀 Menjalankan ekosistem Punggawa terpadu...")

    # 1. Jalankan FastAPI Streaming Gateway (Port 8000)
    print("📡 [1/3] Memulai Streaming Gateway Server...")
    p_server = subprocess.Popen(
        [VENV_PYTHON, "scripts/visualizer_server.py"],
        cwd=PROJECT_ROOT
    )
    processes.append(p_server)
    time.sleep(1.5)

    # 2. Jalankan Autonomous Worker
    print("⚙️  [2/3] Memulai Background Worker Runner...")
    p_worker = subprocess.Popen(
        [VENV_PYTHON, "-m", "workers.runner"],
        cwd=PROJECT_ROOT
    )
    processes.append(p_worker)

    # 3. Jalankan Vite Web Visualizer 3D (Port 5173)
    web_dir = os.path.join(PROJECT_ROOT, "web")
    if os.path.exists(web_dir):
        print("🎨 [3/3] Memulai Web 3D Visualizer (Vite)...")
        p_web = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=web_dir
        )
        processes.append(p_web)

    print("\n✅ Seluruh sistem Punggawa aktif!")
    print("👉 Buka antarmuka 3D di browser: http://localhost:5173")
    print("Tekan Ctrl + C kapan saja untuk menghentikan semua servis sekaligus.\n")

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()