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

---

## 📱 Panduan Integrasi Media Sosial & Troubleshooting OAuth

### 1. Mengatasi Error Login TikTok: `non_sandbox_target`

#### 📌 Penyebab Error
Error ini muncul ketika aplikasi TikTok di [TikTok Developer Portal](https://developers.tiktok.com/) masih berada dalam mode **Sandbox** (Development). Pada mode Sandbox, TikTok secara ketat membatasi login OAuth **hanya untuk akun-akun TikTok yang telah didaftarkan secara manual ke dalam daftar Target Users (Sandbox Test Accounts)**. Jika akun yang mencoba login belum didaftarkan, TikTok akan menolak otorisasi dengan pesan:
```text
We couldn't log in with TikTok. This may be due to specific app settings.
If you're a developer, correct the following and try again:
non_sandbox_target
```

#### 🛠️ Langkah-Langkah Menambahkan Akun/Email ke Target Users:
1. **Buka TikTok Developer Portal**:
   - Kunjungi [https://developers.tiktok.com/](https://developers.tiktok.com/) dan login menggunakan akun developer Anda.
2. **Buka Menu Aplikasi**:
   - Di navigasi atas, klik **My Apps** (atau **Manage apps**).
   - Pilih aplikasi yang Anda gunakan untuk integrasi sosial (misalnya aplikasi Bogorstore Social / Postiz).
3. **Pastikan Mode Sandbox Aktif**:
   - Periksa toggle mode di bagian atas / samping nama aplikasi, pastikan berada pada mode **Sandbox** (bukan Live/Production).
4. **Masuk ke Sandbox Settings**:
   - Di bilah menu sebelah kiri, klik tab **Sandbox settings** (atau gulir ke bawah pada halaman detail aplikasi).
5. **Tambahkan Akun Target (Target Users)**:
   - Temukan bagian bertuliskan **Target users**.
   - Klik tombol **+ Add account** (atau *Add Target User*). Anda dapat menambahkan hingga maksimal 10 akun penguji.
   - Akan muncul jendela otorisasi / login TikTok:
     - Masukkan **Email**, **Nomor Telepon**, atau **Username TikTok** yang ingin Anda gunakan untuk login di Bogorstore Social/Postiz.
     - Masukkan password akun TikTok tersebut dan selesaikan verifikasi captcha jika diminta.
     - Klik tombol **Log in** dan setujui **TikTok Developer Terms of Service**.
6. **Verifikasi Daftar Akun**:
   - Setelah berhasil login, akun tersebut akan langsung tercantum dalam daftar tabel **Target users**.
7. **Coba Login Ulang**:
   - Kembali ke halaman integrasi sosial (misalnya `https://sosial.bogorstore.com/integrations/social/tiktok` atau Postiz).
   - Klik **Connect / Tambah Akun TikTok**.
   - Login menggunakan akun yang baru saja didaftarkan ke Target Users. Proses otorisasi akan berjalan sukses tanpa error `non_sandbox_target`.

---

#### 💡 Troubleshooting Error TikTok Lainnya:

* **Error `scope`**:
  - *Penyebab*: Scope/izin yang diminta oleh platform integrasi (seperti `user.info.basic`, `user.info.profile`, `user.info.stats`, `video.list`, `video.upload`, `video.publish`) belum diaktifkan di portal developer.
  - *Solusi*: Di menu aplikasi TikTok Developer, buka **Products** / **Add Products**, tambahkan **Login Kit** dan **Video Kit**, lalu pastikan permissions/scopes tersebut dicentang dan disimpan.
* **Pindah ke Mode Live/Production**:
  - Jika aplikasi ingin dapat dihubungkan oleh akun TikTok publik tanpa perlu mendaftarkan akun satu per satu ke Target Users, ajukan aplikasi melalui tombol **Submit for Review** di TikTok Developer Portal hingga disetujui (*Approved*).

---

## 📱 Agen "Kang Sosmed" & Alur Antrean Video TikTok (Inbox Draft)

### 1. Peran & Spesialisasi
Agen **Kang Sosmed** (`sosmed`, warna branding `#E11D48` Crimson Rose) beroperasi di meja bundar kantor 3D (Kursi 0), bertugas mengelola publikasi media sosial multi-channel melalui platform Postiz (`sosial.bogorstore.com` / `sosial.mbtech.info`).

Fokus utamanya adalah memproses antrean konten video TikTok Shop untuk akun **Kedai Daily Nurul** (`cmw2y48yi0003o274ue9csad3`).

### 2. Alur Pengunggahan Video 7 Hari (`data/tiktok_queue/`):
1. **Unggah File Video**:
   - Letakkan file video MP4 produk ke dalam folder `data/tiktok_queue/` (misalnya: `promo_kopi_bogor.mp4`, `madu_hutan.mp4`, dll).
   - *(Opsional)* Jika ingin caption khusus, sertakan file teks dengan nama yang sama: `promo_kopi_bogor.txt`.
2. **Perencanaan & Dispatching**:
   - Kang Sosmed secara otomatis menjadwalkan video (jam 13:00 WIB setiap hari) via Planner.
   - Script dispatcher mengunggah video ke Postiz Media Storage lalu menerbitkannya sebagai **Draf Inbox TikTok** (`content_posting_method: "UPLOAD"`).
3. **Penyematan Keranjang Kuning di HP**:
   - Notifikasi sistem akan muncul di HP TikTok admin: *"Video Anda siap diposting"*.
   - Admin membuka notifikasi -> tap **+ Tambah Tautan / Produk (Add Link)** -> pilih produk dari etalase TikTok Shop -> klik **Posting**.
4. **Pembersihan Otomatis Storage**:
   - Setelah video sukses masuk ke Inbox TikTok, file lokal di `data/tiktok_queue/` otomatis dihapus demi menjaga efisiensi ruang disk.

### 3. Pengecekan Integritas Fisik oleh Kang Bos (Bay-Zero):
Setiap pagi, Kang Bos (Bay-Zero) melakukan audit kebenaran jadwal (bukan formalitas database):
* **Pengecekan Video TikTok**: Memastikan file fisik MP4 benar-benar ada di `data/tiktok_queue` sebelum waktu tayang tiba, dan memverifikasi Postiz Post ID untuk status `completed`.
* **Pengecekan Video YouTube**: Memverifikasi video YouTube masih aktif via oEmbed endpoint (bukan video terhapus atau diset private).
* **Pengecekan Artikel**: Memverifikasi tautan publikasi CMS (`result_url`) terdaftar valid.
* Jika ditemukan ketidaksesuaian, Kang Bos otomatis mengirimkan notifikasi diagnostik transparan agar strategi konten dapat segera diselaraskan.


