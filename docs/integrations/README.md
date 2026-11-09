# 🌐 Dokumentasi Integrasi Eksternal Punggawa

Koleksi panduan teknis dan referensi integrasi media sosial, CMS, dan layanan eksternal yang terhubung dengan **Punggawa Hybrid Autonomous AI Agent Orchestrator**.

---

## 📚 Daftar Panduan Integrasi

| Modul Integrasi | File Panduan | Deskripsi & Cakupan |
|---|---|---|
| **TikTok** | [`tiktok.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/tiktok.md) | Panduan lengkap otomatisasi TikTok: OAuth Developer Sandbox (`non_sandbox_target`), alur Keranjang Kuning via Draf Inbox HP, FFmpeg 1.0s video bumper cover, gateway web upload aman, dan multi-akun (`DongengIDN` & `Kedai Daily Nurul`). |
| **Instagram & Threads** | [`instagram.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/instagram.md) | Publikasi otomatis feed & reels Instagram via Meta Graph API, generator banner Pillow dinamis, integrasi postingan Threads, dan penanganan token OAuth. |
| **YouTube** | [`youtube.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/youtube.md) | Integrasi YouTube Data API v3, Deep Channel Scanner (hemat kuota 100x via Uploads Playlist), verifikasi integritas video publik tanpa kuota (Zero-Quota oEmbed), dan pipeline Shorts. |
| **Postiz Social Gateway** | [`postiz.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/postiz.md) | Panduan gateway terpusat multi-sosmed (`sosial.bogorstore.com`), API keys, endpoint upload media, payload broadcast multi-channel, dan manajemen token. |
| **CMS & Push Notifications** | [`cms.md`](file:///Users/reggi/Projects/punggawa/docs/integrations/cms.md) | Sindikasi artikel teknologi ke KodePintar, kurasi naskah dongeng ke Bogorstore CMS, dan Smart Anti-Collision Push Notification (Google FCM). |

---

## 🧪 Panduan & Domain Pendaftaran Tester per Platform

Saat aplikasi media sosial masih dalam status **Pengembangan / Sandbox / Testing**, platform membatasi akses OAuth hanya untuk akun-akun yang terdaftar secara resmi sebagai **Tester**.

Gunakan tabel referensi berikut untuk mendaftarkan akun tester:

| Platform | Portal Developer (Domain) | Lokasi Menu Tester | Cara Registrasi & Konfirmasi | Kuota Maksimal | Redirect URI (Postiz Callback) |
|---|---|---|---|:---:|---|
| **TikTok** | [developers.tiktok.com](https://developers.tiktok.com/) | `My Apps > [App] > Sandbox settings > Target users` | 1. Klik **+ Add account**.<br>2. Login dengan akun TikTok target dan setujui Terms.<br>3. Status langsung aktif di tabel Target Users. | 10 Akun | `https://sosial.bogorstore.com/api/auth/callback/tiktok` |
| **Instagram & Threads** | [developers.facebook.com](https://developers.facebook.com/) | `App Dashboard > App Roles > Roles > Instagram Testers` | 1. Klik **Add Instagram Testers** dan masukkan username.<br>2. **Wajib:** Buka [instagram.com/accounts/manage_access/](https://www.instagram.com/accounts/manage_access/) di browser akun tester.<br>3. Buka tab **Tester Invitations** -> klik **Accept**. | 50 Tester | `https://sosial.bogorstore.com/api/auth/callback/instagram`<br>`https://sosial.bogorstore.com/api/auth/callback/threads` |
| **YouTube** | [console.cloud.google.com](https://console.cloud.google.com/) | `APIs & Services > OAuth consent screen > Test users` | 1. Klik **+ ADD USERS**.<br>2. Masukkan alamat email Google / Gmail pengelola channel YouTube.<br>3. Klik **Save**. Saat login di Postiz, pilih *Advanced > Go to bogorstore.com (unsafe)*. | 100 Email | `https://sosial.bogorstore.com/api/auth/callback/google` |
| **Postiz Hub** | [sosial.bogorstore.com](https://sosial.bogorstore.com/) | `Settings > Integrations` | Hubungkan (*Connect*) akun yang telah disetujui sebagai tester di atas. | Tak Terbatas | Domain pusat gateway sosial |

---

## 🛠️ Ringkasan Environment Variable

Pastikan variabel-variabel berikut telah dikonfigurasi pada file `.env` root proyek Anda:

```env
# Postiz Gateway
POSTIZ_API_KEY=your_postiz_api_key
POSTIZ_BASE_URL=https://sosial.bogorstore.com/api/public/v1
POSTIZ_TIKTOK_INTEGRATION_ID=cmw3byats000ao2745rk4z14k
POSTIZ_TIKTOK_KEDAI_INTEGRATION_ID=cmw2y48yi0003o274ue9csad3
POSTIZ_INSTAGRAM_INTEGRATION_ID=cmvvzqhn7000epl6yd8bp7mzz
POSTIZ_INSTAGRAM_KITTENGAUL_INTEGRATION_ID=cmw909dnc0013o274l7q4fjc5
POSTIZ_THREADS_INTEGRATION_ID=cmw1m3jvh0001o274j5o6snns
POSTIZ_YOUTUBE_INTEGRATION_ID=cmw1jqlvs0001mk736aotawcm

# YouTube Data API
YOUTUBE_API_KEY=AIzaSy...

# CMS & Push Notifications
DONGENG_CMS_POST_URL=https://bogorstore.com/agoose/api/posts
DONGENG_CMS_STORIES_URL=https://bogorstore.com/agoose/api/posts/stories
DONGENG_CMS_NOTIFICATION_URL=https://bogorstore.com/agoose/posts/sendnotification
```
