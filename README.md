# Punggawa: Hybrid Autonomous AI Agent Orchestrator

Arsitektur orkestrasi AI Agent berbasis **LangGraph** yang beroperasi secara hybrid (Sinkron antara mesin Lokal Mac dan Cloud VPS) **tanpa race condition**.

---

## 🌟 Fitur Utama
1. **LangGraph StateGraph & PostgresSaver**:
   - Single source of truth menggunakan PostgreSQL terpusat (Supabase / Managed PostgreSQL).
   - Menghindari penggunaan SQLite lokal yang rawan desinkronisasi.
2. **Anti-Race Condition Distributed Lock**:
   - Atomic locking menggunakan Redis `SET NX EX`.
   - Safe release menggunakan Redis Lua Script berbasis token UUID kepemilikan.
   - Fail-fast mechanism: Task dilepas kembali ke queue jika sedang diproses instance lain.
3. **Modular Nodes & Checkpointing**:
   - `IngestNode`: Validasi payload dan audit worker metadata.
   - `ProcessorNode`: Eksekusi komputasi / Tool Calling.
   - `CompleteNode`: Finalisasi task dan completion logging.
4. **Human-in-the-Loop Ready**:
   - Percabangan graf otomatis menahan eksekusi di checkpoint jika flag `requires_approval=True`.
   - Worker mendukung resume task langsung dari checkpoint PostgreSQL.
5. **Graceful Shutdown**:
   - Penanganan sinyal OS (`SIGINT`, `SIGTERM`) untuk menghentikan worker tanpa memotong task yang sedang aktif.

---

## 📁 Struktur Direktori

```text
.
├── config/
│   ├── __init__.py
│   └── settings.py          # Pydantic Settings (ENV: Postgres, Redis, Workers)
├── orchestrator/
│   ├── __init__.py
│   ├── state.py             # Definisi AgentState TypedDict
│   ├── connections.py       # ConnectionPool PostgresSaver & Redis Client
│   ├── lock.py              # Redis Distributed Lock & Decorator
│   └── graph.py             # LangGraph assembly, modular nodes, and routing
├── workers/
│   ├── __init__.py
│   ├── runner.py            # Worker entrypoint (BLPOP queue polling)
│   └── enqueue_test.py      # Helper untuk mengirim task ke antrean
├── .env.example             # Template konfigurasi variabel lingkungan
├── requirements.txt         # Daftar dependensi Python
├── docker-compose.yml       # Setup container Postgres, Redis, dan Cloud Worker
├── Dockerfile               # Production image Docker worker
└── README.md
```

---

## 🚀 Panduan Memulai Cepat

### 1. Setup Environment Lokal

Buat virtual environment dan install dependensi:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Salin file `.env.example` ke `.env`:

```bash
cp .env.example .env
```

Sesuaikan nilai di dalam `.env`:
```env
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/punggawa_db
REDIS_URL=redis://localhost:6379/0
WORKER_ID=mac-local-worker
```

### 2. Jalankan Infrastruktur Lokal (Opsional)

Jika belum memiliki PostgreSQL dan Redis cloud, jalankan infrastruktur lokal via Docker:

```bash
docker compose up -d postgres redis
```

### 3. Jalankan Worker Lokal

```bash
python -m workers.runner
```

Output terminal:
```text
2026-10-19 [INFO] [Worker-mac-local-worker] 🚀 Worker 'mac-local-worker' aktif mendengarkan queue 'agent:task:queue'...
```

### 4. Kirim Test Task ke Antrean

Di terminal lain, kirim task percobaan:

```bash
# Task standar
python -m workers.enqueue_test

# Task dengan Human-in-the-loop checkpoint
python -m workers.enqueue_test --approval
```

---

## ☁️ Topologi Hybrid (Lokal ⟷ VPS Cloud)

Untuk menjalankan worker di VPS Cloud bersamaan dengan Mac Lokal:
1. Hubungkan `DATABASE_URL` ke PostgreSQL cloud yang sama (misal Supabase).
2. Hubungkan `REDIS_URL` ke Redis cloud yang sama (misal Redis Cloud / Upstash).
3. Berikan `WORKER_ID` yang berbeda:
   - Mac Lokal: `WORKER_ID=mac-reggi`
   - Cloud VPS: `WORKER_ID=vps-cloud-worker-1`
4. Kedua worker akan mengonsumsi antrean yang sama. Jika kedua worker mencoba thread yang sama, **Redis Distributed Lock menjamin hanya ada 1 worker yang mengeksekusinya**, sementara worker lainnya mengembalikan task ke queue tanpa bentrok data.

