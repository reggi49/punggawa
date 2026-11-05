#!/usr/bin/env python3
"""
TikTok Autonomous Queue Dispatcher for Punggawa (Kedai Daily Nurul).
Memproses video dari antrean 'data/tiktok_queue/', mengunggah ke Postiz,
menerbitkan sebagai Draf ke Inbox TikTok (Strategi Keranjang Kuning),
dan otomatis menghapus file lokal setelah berhasil terposting.
"""
import argparse
import glob
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import requests

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TikTokDispatcher")

POSTIZ_API_KEY = "d59b5fb460b5b78844e9ddd597a2bf575dc034b34d87e11868d21b3406837344"
POSTIZ_BASE_URL = "https://sosial.bogorstore.com/api/public/v1"
TIKTOK_INTEGRATION_ID = "cmw2y48yi0003o274ue9csad3"  # Kedai Daily Nurul
QUEUE_DIR = os.path.join(project_root, "data", "tiktok_queue")


def upload_media_to_postiz(file_path: str) -> dict[str, Any]:
    """Mengunggah video ke penyimpanan Postiz."""
    filename = os.path.basename(file_path)
    headers = {"Authorization": POSTIZ_API_KEY}
    with open(file_path, "rb") as f:
        files = {"file": (filename, f, "video/mp4")}
        res = requests.post(f"{POSTIZ_BASE_URL}/upload", headers=headers, files=files, timeout=60.0)

    if res.status_code != 201:
        raise RuntimeError(f"Gagal upload ke Postiz ({res.status_code}): {res.text}")
    return res.json()


def dispatch_tiktok_draft(
    file_path: str,
    caption: str | None = None,
    title: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Mengirim 1 video ke Inbox TikTok sebagai draf, lalu menghapus file lokal jika sukses."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File video tidak ditemukan: {file_path}")

    filename = os.path.basename(file_path)
    base_name, _ = os.path.splitext(filename)
    caption_txt_path = os.path.join(os.path.dirname(file_path), f"{base_name}.txt")

    # Baca caption kustom dari file .txt pendamping jika ada
    custom_caption = caption
    if not custom_caption and os.path.exists(caption_txt_path):
        try:
            with open(caption_txt_path, "r", encoding="utf-8") as f:
                custom_caption = f.read().strip()
            logger.info(f"📄 Menggunakan caption kustom dari: {os.path.basename(caption_txt_path)}")
        except Exception as exc:
            logger.warning(f"Gagal membaca caption txt: {exc}")

    final_caption = custom_caption or (
        "Rekomendasi terbaik hari ini dari Kedai Daily Nurul! ✨ "
        "Kualitas terjamin, harga bersahabat, siap kirim ke seluruh Indonesia 🛍️📦\n\n"
        "👉 Klik keranjang kuning di bawah untuk order sekarang!\n\n"
        "#kedaidailynurul #racuntiktok #belilokal #tiktokshop #rekomendasiproduk #fyp"
    )
    final_title = title or "Rekomendasi Spesial Kedai Daily Nurul"

    if dry_run:
        logger.info(f"🔍 [DRY RUN] Simulasi kirim: {filename} ({final_title})")
        return {"status": "dry_run", "file": filename}

    logger.info(f"📤 Mengunggah video '{filename}' ke Postiz Storage...")
    upload_res = upload_media_to_postiz(file_path)
    media_id = upload_res["id"]
    media_path = upload_res["path"]
    logger.info(f"✅ Video berhasil diunggah ke Postiz: {media_path}")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payload = {
        "type": "now",
        "date": now_iso,
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": TIKTOK_INTEGRATION_ID},
                "value": [
                    {
                        "content": final_caption,
                        "image": [{"id": media_id, "path": media_path}],
                    }
                ],
                "settings": {
                    "__type": "tiktok",
                    "title": final_title[:90],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "duet": False,
                    "stitch": False,
                    "comment": True,
                    "autoAddMusic": "no",
                    "brand_content_toggle": False,
                    "brand_organic_toggle": False,
                    "video_made_with_ai": False,
                    "content_posting_method": "UPLOAD",
                },
            }
        ],
    }

    headers = {"Authorization": POSTIZ_API_KEY}
    logger.info(f"🚀 Menerbitkan video ke Inbox TikTok ({TIKTOK_INTEGRATION_ID})...")
    res = requests.post(f"{POSTIZ_BASE_URL}/posts", headers=headers, json=payload, timeout=30.0)

    if res.status_code != 201:
        raise RuntimeError(f"Gagal membuat postingan di Postiz ({res.status_code}): {res.text}")

    result_data = res.json()
    logger.info(f"🎉 SUKSES! Video berhasil masuk ke Inbox TikTok: {result_data}")

    # Bersihkan file lokal setelah sukses terposting
    try:
        os.remove(file_path)
        logger.info(f"🗑️ File video lokal '{filename}' otomatis dihapus untuk hemat storage.")
        if os.path.exists(caption_txt_path):
            os.remove(caption_txt_path)
            logger.info(f"🗑️ File caption pendamping '{os.path.basename(caption_txt_path)}' dihapus.")
    except Exception as exc:
        logger.warning(f"Gagal menghapus file lokal: {exc}")

    return {
        "status": "success",
        "file": filename,
        "post_id": result_data[0].get("postId") if isinstance(result_data, list) else None,
    }


def process_queue(limit: int = 1, dry_run: bool = False):
    """Memproses video yang ada di data/tiktok_queue."""
    os.makedirs(QUEUE_DIR, exist_ok=True)
    video_patterns = [
        os.path.join(QUEUE_DIR, "*.mp4"),
        os.path.join(QUEUE_DIR, "*.mov"),
        os.path.join(QUEUE_DIR, "*.webm"),
    ]
    files = []
    for pat in video_patterns:
        files.extend(glob.glob(pat))

    files.sort(key=os.path.getmtime)  # FIFO (urut dari yang paling awal diupload)
    if not files:
        logger.info(f"ℹ️ Antrean kosong. Belum ada file video di folder '{QUEUE_DIR}'.")
        return

    logger.info(f"📋 Ditemukan {len(files)} file video di antrean '{QUEUE_DIR}'.")
    target_files = files[:limit]

    for f_path in target_files:
        try:
            dispatch_tiktok_draft(f_path, dry_run=dry_run)
        except Exception as exc:
            logger.error(f"❌ Gagal memproses video '{os.path.basename(f_path)}': {exc}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Punggawa TikTok Queue Dispatcher")
    parser.add_argument("--file", help="Path ke file video tertentu untuk diposting langsung")
    parser.add_argument("--caption", help="Caption kustom untuk video")
    parser.add_argument("--title", help="Judul TikTok kustom (max 90 char)")
    parser.add_argument("--limit", type=int, default=1, help="Berapa banyak video di antrean yang diproses (default: 1)")
    parser.add_argument("--all", action="store_true", help="Proses seluruh video yang ada di antrean")
    parser.add_argument("--dry-run", action="store_true", help="Simulasi tanpa mengirim ke API")
    args = parser.parse_args()

    if args.file:
        dispatch_tiktok_draft(args.file, caption=args.caption, title=args.title, dry_run=args.dry_run)
    else:
        lim = 999 if args.all else args.limit
        process_queue(limit=lim, dry_run=args.dry_run)

