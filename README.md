# Punggawa: Hybrid Autonomous AI Agent Orchestrator

Arsitektur orkestrasi AI Agent berbasis **LangGraph** yang beroperasi secara hybrid (sinkronisasi nir-bentrok antara mesin Lokal Mac dan Cloud VPS) menggunakan **PostgreSQL Checkpointing** dan **Redis Distributed Lock**. Dilengkapi dengan dashboard visualisasi kantor 3D real-time interaktif berbasis Three.js / React Three Fiber.

---

## 🌟 Fitur Utama
1. **LangGraph StateGraph & PostgreSQL Checkpointer**:
   - Single source of truth menggunakan PostgreSQL terpusat (Supabase / Managed PostgreSQL).
   - Menghindari penggunaan SQLite lokal yang rawan desinkronisasi antar-node.
2. **Anti-Race Condition Distributed Lock**:
   - Atomic locking menggunakan Redis `SET NX EX`.
   - Safe release menggunakan Redis Lua Script berbasis token UUID kepemilikan.
   - Fail-fast mechanism: Task dilepas kembali ke queue jika sedang diproses instance worker lain.
3. **Modular Nodes & Checkpointing**:
   - `IngestNode`: Validasi payload dan audit worker metadata.
   - `ProcessorNode`: Eksekusi komputasi, multi-source research, dan tool calling.
   - `CompleteNode`: Finalisasi task dan completion logging.
4. **Human-in-the-Loop (HITL) Ready**:
   - Percabangan graf otomatis menahan eksekusi di checkpoint jika flag `requires_approval=True`.
   - Worker mendukung resume task langsung dari checkpoint PostgreSQL via Telegram / Web UI.
5. **Interactive 3D Virtual Office HUD**:
   - Visualisasi status agen AI secara spasial (3D scene) yang mencerminkan aktivitas agen di meja kerja masing-masing secara real-time via WebSocket / SSE.
6. **Graceful Shutdown**:
   - Penanganan sinyal OS (`SIGINT`, `SIGTERM`) untuk menghentikan worker tanpa memotong task yang sedang aktif.

---

## 👥 Skuad AI Agent Punggawa

Sistem Punggawa ditenagai oleh 5 agen otonom khusus yang beroperasi secara kolaboratif:

| Agen | Kode / Alias | Peran & Spesialisasi | Fokus Eksekusi |
|---|---|---|---|
| 👑 **Kang Bos** | `bayzero` | **SOP Auditor & Lead** | Audit integritas jadwal, validasi kepatuhan SOP, pengecekan ketersediaan video/link fisik, dan health check microservices. |
| ✍️ **Kang Nulis** | `stark` | **Tech Writer** | Riset multi-sumber (Brave Search & Google News), penulisan artikel mendalam, dan publikasi ke KodePintar CMS. |
| 📖 **Kang Dongeng** | `usagi` | **Media & Cerita** | Kurasi video YouTube, naskah cerita rakyat, tipografi thumbnail otomatis (PIL), dan publikasi Bogorstore CMS. |
| 💼 **Kang Kerja** | `scout` | **Career Intelligence** | Agregasi lowongan kerja, career profile matching, scoring relevansi, dan personalisasi cover letter. |
| 📱 **Kang Sosmed** | `sosmed` | **Social Media Lead** | Manajemen Postiz, antrean video TikTok Shop (Keranjang Kuning), FFmpeg bumper cover, Instagram, dan Threads. |

---

## 📁 Struktur Direktori

```text
.
├── config/                  # Pengaturan Pydantic & Profile Karir
│   ├── settings.py          # Konfigurasi ENV terpusat (Postgres, Redis, Postiz, dll)
│   └── career_profile.yml   # Profil preferensi karir untuk Kang Kerja
├── docs/                    # Dokumentasi Teknis Terpisah
│   └── integrations/        # Panduan Lengkap Integrasi Sosial Media & CMS
│       ├── README.md        # Index dokumentasi integrasi
│       ├── tiktok.md        # Integrasi TikTok (Draft Inbox, OAuth Sandbox, FFmpeg Cover)
│       ├── instagram.md     # Integrasi Instagram Feed/Reels & Threads via Meta Graph API
│       ├── youtube.md       # YouTube Data API v3, Deep Scanner, Zero-Quota oEmbed
│       ├── postiz.md        # Postiz Social Gateway API & Multi-Channel Broadcast
│       └── cms.md           # Bogorstore CMS, KodePintar, & Smart FCM Notifications
├── orchestrator/            # LangGraph Core Engine
│   ├── graph.py             # Definisi StateGraph, routing, dan node perakitan
│   ├── state.py             # AgentState TypedDict
│   ├── connections.py       # ConnectionPool PostgresSaver & Redis Client
│   ├── lock.py              # Redis Distributed Lock & Decorator
│   ├── graphs/              # Pipeline sub-graph (article, dongeng, job, chat)
│   └── tools/               # Tooling (YouTube, Scraper, CMS Notifier, PIL, dll)
├── workers/                 # Worker Task Processing
│   ├── runner.py            # Worker entrypoint (BLPOP queue polling)
│   └── enqueue_test.py      # Helper untuk mengirim task pengujian
├── scripts/                 # Utilitas Dispatching, Scanner & Planner
│   ├── tiktok_dispatcher.py # Dispatcher antrean multi-akun TikTok
│   ├── channel_scanner.py   # Deep scanner YouTube uploads playlist
│   ├── planner.py           # Perencanaan jadwal harian konten
│   └── test_postiz_autopost.py # Skrip verifikasi Meta/Instagram
├── server/                  # Real-Time Visualizer Streaming Server
│   └── stream_server.py     # FastAPI Server (WebSocket, SSE, API Upload TikTok)
├── web/                     # Frontend 3D Office HUD (React + Three.js)
├── data/                    # Storage Antrean Lokal & Cover Branding
│   ├── covers/              # File cover branding channel resmi
│   └── tiktok_queue/        # Antrean video (berdongeng & kedaidaily)
├── docker-compose.yml       # Container Postgres, Redis, dan Cloud Worker
├── requirements.txt         # Daftar dependensi Python
└── README.md
```

---

## 🚀 Panduan Memulai Cepat

### 1. Setup Environment Lokal
Buat virtual environment dan install dependensi:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Salin file `.env.example` ke `.env` lalu sesuaikan konfigurasi:
```bash
cp .env.example .env
```

### 2. Jalankan Infrastruktur (Docker)
Jika belum memiliki PostgreSQL dan Redis cloud, jalankan infrastruktur lokal via Docker:
```bash
docker compose up -d postgres redis
```

### 3. Jalankan Worker Punggawa
```bash
./venv/bin/python -m workers.runner
```
Output terminal:
```text
[INFO] [Worker-local-worker] 🚀 Worker 'local-worker' aktif mendengarkan queue 'agent:task:queue'...
```

### 4. Jalankan Real-time Streaming Server & Web HUD
Di terminal terpisah:
```bash
# Server Backend (FastAPI + WebSocket)
./venv/bin/python server/stream_server.py

# Frontend Web Dashboard (Opsional jika ingin tampilan dev)
cd web && npm run dev
```
Akses dashboard di browser melalui: `http://localhost:8000` (atau port Vite `http://localhost:5173`).

### 5. Kirim Task Percobaan
```bash
# Kirim task standar
./venv/bin/python -m workers.enqueue_test

# Kirim task dengan checkpoint Human-in-the-Loop
./venv/bin/python -m workers.enqueue_test --approval
```

---

## ☁️ Topologi Hybrid (Lokal ⟷ VPS Cloud)

Punggawa didesain untuk beroperasi serentak di laptop lokal dan VPS Cloud tanpa risiko bentrok pekerjaan:
1. Hubungkan `DATABASE_URL` ke PostgreSQL cloud yang sama (misal: Supabase).
2. Hubungkan `REDIS_URL` ke Redis cloud yang sama (misal: Upstash / Redis Cloud).
3. Berikan `WORKER_ID` yang unik pada masing-masing mesin:
   - Mac Lokal: `WORKER_ID=mac-local-reggi`
   - Cloud VPS: `WORKER_ID=vps-cloud-worker-1`
4. Kedua worker akan mengonsumsi antrean task bersama. **Redis Distributed Lock menjamin hanya ada satu worker yang mengeksekusi suatu thread ID**, sementara worker lainnya mengembalikan task ke antrean secara aman jika lock sedang dipegang.

---

## 🌐 Integrasi Media Sosial & Layanan Eksternal

Panduan teknis mendalam mengenai setiap integrasi eksternal telah diekstrak ke dalam dokumen terpisah:

| Layanan / Platform | Dokumentasi Lengkap | Topik Utama |
|---|---|---|
| **TikTok** | [📖 `docs/integrations/tiktok.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/tiktok.md) | Penanganan error OAuth `non_sandbox_target`, strategi Draf Inbox untuk Keranjang Kuning, auto-bumper video cover FFmpeg, upload gateway aman, dan multi-akun (`@berdongeng` & `@nurulzulaikhha`). |
| **Instagram & Threads** | [📖 `docs/integrations/instagram.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/instagram.md) | Meta Graph API via Postiz, syarat Akun Profesional, generator banner otomatis Pillow (1080x1080), Reels, dan postingan Threads. |
| **YouTube** | [📖 `docs/integrations/youtube.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/youtube.md) | YouTube Data API v3, Deep Channel Scanner (paginasi uploads playlist hemat kuota 100x), verifikasi video publik tanpa kuota (Zero-Quota oEmbed), dan pipeline Shorts. |
| **Postiz Social Gateway** | [📖 `docs/integrations/postiz.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/postiz.md) | Jembatan sosial terpusat `sosial.bogorstore.com`, autentikasi API Key, upload media storage, payload siaran multi-channel, dan pemulihan token. |
| **CMS & Push Notifications** | [📖 `docs/integrations/cms.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/cms.md) | Integrasi Bogorstore CMS (cmsAgoose), KodePintar Tech Articles, dan penjadwalan Smart Anti-Collision Google FCM Push Notification. |

👉 Kunjungi [**Index Dokumentasi Integrasi**](file:///Users/reggi/Projects/punggawa/docs/integrations/README.md) untuk ringkasan variabel lingkungan dan daftar lengkap panduan.

---

## 📜 Lisensi & Kontributor
Dikembangkan secara otonom oleh tim **Punggawa AI Orchestrator** untuk ekosistem Bogorstore & KodePintar.
