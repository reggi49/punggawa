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

def start_process(cmd, cwd):
    # preexec_fn=os.setsid membuat process group baru agar bisa dihentikan total
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        preexec_fn=os.setsid
    )

def main():
    print("🚀 Menjalankan ekosistem Punggawa...")

    # 1. Jalankan FastAPI Streaming Gateway (Port 8000)
    print("📡 [1/3] Memulai Streaming Gateway Server...")
    processes.append(start_process([VENV_PYTHON, "scripts/visualizer_server.py"], PROJECT_ROOT))
    time.sleep(1.5)

    # 2. Jalankan Autonomous Worker
    print("⚙️  [2/3] Memulai Background Worker Runner...")
    processes.append(start_process([VENV_PYTHON, "-m", "workers.runner"], PROJECT_ROOT))

    # 3. Jalankan Web UI
    web_dir = os.path.join(PROJECT_ROOT, "web")
    if os.path.exists(web_dir):
        print("🎨 [3/3] Memulai Web 3D Visualizer (Vite)...")
        processes.append(start_process(["npm", "run", "dev"], web_dir))

    print("\n✅ Seluruh sistem Punggawa aktif!")
    print("👉 Akses visualizer: http://localhost:5173")
    print("Tekan Ctrl + C kapan saja untuk mematikan semua proses.\n")

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()