#!/usr/bin/env python3
"""
Google Drive Content Queue & Synchronization Module.
Mengambil stok video langsung dari Google Drive secara READ-ONLY tanpa mengubah atau
menghapus file di Google Drive. Riwayat publikasi dicatat di Supabase PostgreSQL
(gdrive_media_dispatches) berbasis (channel_id, gdrive_file_id), sehingga video yang
sama dapat digunakan untuk channel lain jika diinginkan tanpa risiko duplikasi.
"""
import io
import json
import logging
import os
import sys
from typing import Any

# Ensure project root in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from config.settings import settings
from orchestrator.connections import postgres_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GDriveSync")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TEMP_DOWNLOAD_DIR = os.path.join(project_root, "data", "temp_gdrive_downloads")


def get_drive_service():
    """Menginisialisasi klien Google Drive API dengan Service Account (Read-Only)."""
    creds = None

    # Opsi 1: Raw JSON string dari environment variable
    raw_json = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_JSON_RAW", None) or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_RAW")
    if raw_json and raw_json.strip():
        try:
            info = json.loads(raw_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            logger.info("🔑 Google Drive API diinisialisasi via GOOGLE_SERVICE_ACCOUNT_JSON_RAW.")
        except Exception as exc:
            logger.warning(f"Gagal mem-parse GOOGLE_SERVICE_ACCOUNT_JSON_RAW: {exc}")

    # Opsi 2: File JSON di disk (misal config/gdrive_credentials.json)
    if not creds:
        json_path = (
            getattr(settings, "GOOGLE_SERVICE_ACCOUNT_JSON", "config/gdrive_credentials.json")
            or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "config/gdrive_credentials.json")
        )
        if not os.path.isabs(json_path):
            json_path = os.path.join(project_root, json_path)

        if os.path.exists(json_path):
            try:
                creds = service_account.Credentials.from_service_account_file(json_path, scopes=SCOPES)
                logger.info(f"🔑 Google Drive API diinisialisasi via file: {os.path.basename(json_path)}")
            except Exception as exc:
                logger.warning(f"Gagal memuat kredensial Google Drive dari {json_path}: {exc}")
        else:
            logger.debug(f"File kredensial Google Drive tidak ditemukan di: {json_path}")

    if not creds:
        return None

    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return service
    except Exception as exc:
        logger.error(f"❌ Gagal membuat service Google Drive v3: {exc}", exc_info=True)
        return None


def resolve_folder_id_for_channel(account_key: str | None = None) -> str | None:
    """Menentukan Google Drive Folder ID berdasarkan akun target."""
    if account_key == "kittengaul":
        folder_id = (
            getattr(settings, "GOOGLE_DRIVE_FOLDER_ID_KITTENGAUL", None)
            or os.getenv("GOOGLE_DRIVE_FOLDER_ID_KITTENGAUL")
        )
        if folder_id and folder_id.strip():
            return folder_id.strip()

    # Fallback ke folder utama umum
    main_folder = (
        getattr(settings, "GOOGLE_DRIVE_FOLDER_ID", None)
        or os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    )
    return main_folder.strip() if main_folder and main_folder.strip() else None


def list_videos_in_folder(service, folder_id: str) -> list[dict[str, Any]]:
    """
    Mengambil daftar file video dari folder Google Drive secara terurut (FIFO).
    Hanya membaca metadata (id, name, mimeType, md5Checksum, size, createdTime).
    """
    query = (
        f"'{folder_id}' in parents and trashed = false and "
        f"(mimeType contains 'video/' or name contains '.mp4' or name contains '.mov' or name contains '.webm')"
    )

    videos = []
    page_token = None

    while True:
        try:
            response = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, md5Checksum, size, createdTime)",
                    orderBy="createdTime asc",
                    pageToken=page_token,
                    pageSize=100,
                )
                .execute()
            )

            files = response.get("files", [])
            videos.extend(files)

            page_token = response.get("nextPageToken")
            if not page_token:
                break
        except Exception as exc:
            logger.error(f"❌ Gagal membaca isi folder Google Drive '{folder_id}': {exc}")
            break

    logger.info(f"📂 Ditemukan {len(videos)} file video di Google Drive folder '{folder_id}'.")
    return videos


def get_posted_file_ids(channel_id: str) -> set[str]:
    """Mengambil seluruh gdrive_file_id yang SUDAH pernah tayang untuk channel_id ini dari Supabase."""
    posted_ids = set()
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT gdrive_file_id FROM gdrive_media_dispatches WHERE channel_id = %s;",
                    (channel_id,),
                )
                rows = cur.fetchall()
                for r in rows:
                    if r[0]:
                        posted_ids.add(r[0])
    except Exception as exc:
        logger.error(f"❌ Gagal mengambil riwayat posting Supabase untuk channel '{channel_id}': {exc}")

    return posted_ids


def download_file_from_drive(service, file_id: str, destination_path: str, file_name: str) -> bool:
    """Mengunduh file dari Google Drive ke destination_path secara bertahap (streaming chunk)."""
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    logger.info(f"📥 Mengunduh video dari Google Drive: '{file_name}' (ID: {file_id})...")

    try:
        request = service.files().get_media(fileId=file_id)
        with open(destination_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request, chunksize=10 * 1024 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    percent = int(status.progress() * 100)
                    logger.debug(f"   ⏳ Progress unduh '{file_name}': {percent}%")

        logger.info(f"✅ Selesai mengunduh ke: {destination_path} ({os.path.getsize(destination_path)} bytes)")
        return True
    except Exception as exc:
        logger.error(f"❌ Gagal mengunduh file Google Drive '{file_id}': {exc}", exc_info=True)
        if os.path.exists(destination_path):
            try:
                os.remove(destination_path)
            except Exception:
                pass
        return False


def get_next_unposted_drive_video(
    account_key: str,
    channel_id: str,
    folder_id: str | None = None,
) -> tuple[str, dict[str, Any]] | None:
    """
    Mencari 1 video antrean di Google Drive yang BELUM pernah diunggah untuk channel_id ini.
    Jika ditemukan, file diunduh ke direktori temporer lokal dan path serta metadatanya dikembalikan.
    Jika tidak ada atau Drive tidak aktif, mengembalikan None.
    """
    is_enabled = (
        getattr(settings, "GOOGLE_DRIVE_SYNC_ENABLED", False)
        or os.getenv("GOOGLE_DRIVE_SYNC_ENABLED", "false").lower() in ("true", "1", "yes")
    )
    if not is_enabled:
        logger.debug("Google Drive sync dinonaktifkan (GOOGLE_DRIVE_SYNC_ENABLED=false).")
        return None

    target_folder = folder_id or resolve_folder_id_for_channel(account_key)
    if not target_folder:
        logger.warning(f"⚠️ Google Drive folder ID belum dikonfigurasi untuk akun '{account_key}'.")
        return None

    service = get_drive_service()
    if not service:
        logger.warning("⚠️ Klien Google Drive API belum siap (periksa service account JSON).")
        return None

    # 1. Ambil daftar file video di folder Drive
    all_videos = list_videos_in_folder(service, target_folder)
    if not all_videos:
        logger.info(f"ℹ️ Tidak ada video di folder Google Drive '{target_folder}'.")
        return None

    # 2. Ambil daftar video yang sudah pernah tayang di channel ini dari Supabase
    posted_ids = get_posted_file_ids(channel_id)
    logger.info(f"📊 Riwayat posting channel '{channel_id}': {len(posted_ids)} video sudah terbit.")

    # 3. Cari video pertama yang belum pernah tayang (FIFO)
    candidate = None
    for vid in all_videos:
        if vid["id"] not in posted_ids:
            candidate = vid
            break

    if not candidate:
        logger.info(f"🎉 Semua video ({len(all_videos)}) di Google Drive sudah pernah tayang di channel '{channel_id}'.")
        return None

    # 4. Unduh video kandidat ke folder temporer
    safe_name = "".join(c for c in candidate["name"] if c.isalnum() or c in ("-", "_", ".")).strip()
    if not safe_name.lower().endswith((".mp4", ".mov", ".webm")):
        safe_name += ".mp4"

    temp_file_path = os.path.join(TEMP_DOWNLOAD_DIR, f"{candidate['id']}_{safe_name}")
    success = download_file_from_drive(service, candidate["id"], temp_file_path, candidate["name"])

    if not success or not os.path.exists(temp_file_path):
        return None

    return temp_file_path, candidate


def record_video_dispatch(
    channel_id: str,
    channel_name: str,
    gdrive_file_id: str,
    gdrive_file_name: str,
    file_md5: str | None = None,
    file_size_bytes: int | None = None,
    postiz_post_id: str | None = None,
    platform: str = "instagram",
) -> bool:
    """Mencatat publikasi sukses ke tabel Supabase PostgreSQL gdrive_media_dispatches."""
    logger.info(f"📝 Mencatat publikasi ke Supabase: '{gdrive_file_name}' untuk channel '{channel_name}' ({channel_id})...")
    sql = """
    INSERT INTO gdrive_media_dispatches (
        channel_id, channel_name, gdrive_file_id, gdrive_file_name,
        file_md5, file_size_bytes, postiz_post_id, platform, dispatched_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (channel_id, gdrive_file_id) DO UPDATE SET
        postiz_post_id = EXCLUDED.postiz_post_id,
        dispatched_at = EXCLUDED.dispatched_at;
    """
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        channel_id,
                        channel_name,
                        gdrive_file_id,
                        gdrive_file_name,
                        file_md5,
                        file_size_bytes,
                        postiz_post_id,
                        platform,
                    ),
                )
        logger.info("✅ Berhasil mencatat riwayat publikasi di Supabase PostgreSQL.")
        return True
    except Exception as exc:
        logger.error(f"❌ Gagal mencatat publikasi gdrive_media_dispatches: {exc}", exc_info=True)
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Punggawa Google Drive Content Queue Inspector")
    parser.add_argument("--account", default="kittengaul", help="Nama akun target (default: kittengaul)")
    parser.add_argument("--channel-id", help="Override channel ID target")
    parser.add_argument("--folder-id", help="Override Google Drive folder ID")
    parser.add_argument("--list", action="store_true", help="Tampilkan daftar video antrean vs sudah tayang")
    args = parser.parse_args()

    svc = get_drive_service()
    if not svc:
        print("❌ Klien Google Drive belum terhubung. Pastikan file JSON Service Account tersedia.")
        sys.exit(1)

    fid = args.folder_id or resolve_folder_id_for_channel(args.account)
    if not fid:
        print(f"❌ Folder ID belum diatur untuk akun '{args.account}'. Atur GOOGLE_DRIVE_FOLDER_ID di .env.")
        sys.exit(1)

    cid = args.channel_id or (
        os.getenv("POSTIZ_INSTAGRAM_KITTENGAUL_INTEGRATION_ID")
        or getattr(settings, "POSTIZ_INSTAGRAM_KITTENGAUL_INTEGRATION_ID", "cmw909dnc0013o274l7q4fjc5")
    )

    videos = list_videos_in_folder(svc, fid)
    posted = get_posted_file_ids(cid)

    print(f"\n========================================================")
    print(f"📦 Google Drive Folder: {fid}")
    print(f"🎯 Target Channel     : {args.account} ({cid})")
    print(f"📊 Total Video di Drive: {len(videos)} | Sudah Tayang: {len(posted)}")
    print(f"========================================================\n")

    for i, v in enumerate(videos, 1):
        status = "✅ SUDAH TAYANG" if v["id"] in posted else "⏳ ANTRIAN (PENDING)"
        print(f"{i:3d}. [{status}] {v['name']} (ID: {v['id']})")

