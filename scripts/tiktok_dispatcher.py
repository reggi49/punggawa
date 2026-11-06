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

from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TikTokDispatcher")

POSTIZ_API_KEY = settings.POSTIZ_API_KEY
POSTIZ_BASE_URL = settings.POSTIZ_BASE_URL
TIKTOK_INTEGRATION_ID = settings.POSTIZ_TIKTOK_INTEGRATION_ID
QUEUE_DIR = os.path.join(project_root, "data", "tiktok_queue")
COVERS_DIR = os.path.join(project_root, "data", "covers")

# Konfigurasi Preset Multi-Akun TikTok
TIKTOK_ACCOUNTS: dict[str, dict[str, Any]] = {
    "kedaidaily": {
        "name": "Kedai Daily Nurul (@nurulzulaikhha)",
        "integration_id": os.getenv("POSTIZ_TIKTOK_KEDAI_INTEGRATION_ID") or "cmw2y48yi0003o274ue9csad3",
        "subfolder": "kedaidaily",
        "method": "UPLOAD",  # Draf ke Inbox HP untuk disematkan Keranjang Kuning
        "apply_cover": False,
        "default_title": "Rekomendasi Spesial Kedai Daily Nurul",
        "default_caption": (
            "Rekomendasi terbaik hari ini dari Kedai Daily Nurul! ✨ "
            "Kualitas terjamin, harga bersahabat, siap kirim ke seluruh Indonesia 🛍️📦\n\n"
            "👉 Klik keranjang kuning di bawah untuk order sekarang!\n\n"
            "#kedaidailynurul #racuntiktok #belilokal #tiktokshop #rekomendasiproduk #fyp"
        ),
    },
    "berdongeng": {
        "name": "DongengIDN (@berdongeng)",
        "integration_id": os.getenv("POSTIZ_TIKTOK_INTEGRATION_ID") or "cmw3byats000ao2745rk4z14k",
        "subfolder": "berdongeng",
        "method": "UPLOAD",  # Draf ke Inbox HP dengan Cover Otomatis (FYP & Keranjang Kuning Maksimal)
        "apply_cover": True,
        "default_title": "Dongeng Indonesia: Kisah Pilihan",
        "default_caption": (
            "Kisah dongeng pilihan spesial untuk hari ini! ✨ Cerita baik, untuk hari yang lebih baik 🌙📖\n\n"
            "👉 Jangan lupa follow TikTok @berdongeng dan unduh aplikasinya sekarang di App Store & Google Play! 📲💖\n\n"
            "#dongengindonesia #berdongeng #ceritaanak #kisahdongeng #fyp"
        ),
    },
}


def has_audio_stream(file_path: str) -> bool:
    """Mengecek apakah file video memiliki stream audio."""
    import subprocess
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return bool(res.stdout.strip())
    except Exception:
        return True


def resolve_channel_cover(file_path: str, integration_id: str | None = None) -> str | None:
    """
    Menemukan cover gambar berdasarkan hierarki:
    1. Per-video: {video_name}.jpg, {video_name}.png, {video_name}_cover.jpg di folder video
    2. Per-channel integration ID: data/covers/{integration_id}.jpg / .png / .jpeg
    3. Per-channel fallback alias (misal: berdongeng.jpg, dongeng.jpg)
    """
    base_name, _ = os.path.splitext(os.path.basename(file_path))
    video_dir = os.path.dirname(file_path)

    # 1. Cek per-video override
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        cand1 = os.path.join(video_dir, f"{base_name}{ext}")
        if os.path.exists(cand1):
            logger.info(f"🖼️ Menemukan cover khusus video: {os.path.basename(cand1)}")
            return cand1
        cand2 = os.path.join(video_dir, f"{base_name}_cover{ext}")
        if os.path.exists(cand2):
            logger.info(f"🖼️ Menemukan cover khusus video: {os.path.basename(cand2)}")
            return cand2

    # 2. Cek per-channel integration ID
    if integration_id and os.path.exists(COVERS_DIR):
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            cand = os.path.join(COVERS_DIR, f"{integration_id}{ext}")
            if os.path.exists(cand):
                logger.info(f"🖼️ Menemukan cover khusus channel ({integration_id}): {os.path.basename(cand)}")
                return cand

        # Fallback alias jika channel dongeng
        if integration_id == "cmw3byats000ao2745rk4z14k":
            for alias in ["berdongeng.jpg", "dongeng.jpg"]:
                cand = os.path.join(COVERS_DIR, alias)
                if os.path.exists(cand):
                    logger.info(f"🖼️ Menemukan cover alias channel dongeng: {alias}")
                    return cand

    return None


def prepend_cover_to_video(video_path: str, cover_path: str, duration: float = 1.0) -> str:
    """
    Menyisipkan gambar cover selama `duration` detik di awal video menggunakan FFmpeg.
    Mengembalikan path file video baru dengan cover yang sudah terpasang di frame pertama.
    """
    import subprocess
    import tempfile

    base_name, _ = os.path.splitext(os.path.basename(video_path))
    output_path = os.path.join(tempfile.gettempdir(), f"{base_name}_with_cover.mp4")

    logger.info(f"🎨 Menyisipkan cover '{os.path.basename(cover_path)}' ({duration}s) ke awal video...")
    audio_present = has_audio_stream(video_path)

    if audio_present:
        filter_complex = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24[v0];"
            "[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24[v1];"
            "[v0][v1]concat=n=2:v=1:a=0[vout];"
            f"aevalsrc=0:d={duration}[a0];"
            "[a0][1:a]concat=n=2:v=0:a=1[aout]"
        )
        map_args = ["-map", "[vout]", "-map", "[aout]"]
    else:
        filter_complex = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24[v0];"
            "[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24[v1];"
            "[v0][v1]concat=n=2:v=1:a=0[vout]"
        )
        map_args = ["-map", "[vout]"]

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", cover_path,
        "-i", video_path,
        "-filter_complex", filter_complex,
        *map_args,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            logger.error(f"❌ Gagal menyisipkan cover via FFmpeg: {proc.stderr[-300:]}")
            return video_path
        logger.info(f"✅ Cover berhasil disisipkan di frame pertama: {output_path}")
        return output_path
    except Exception as exc:
        logger.error(f"❌ Terjadi kesalahan saat memproses FFmpeg cover: {exc}")
        return video_path


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
    account_key: str | None = None,
    integration_id: str | None = None,
    method: str | None = None,
    apply_cover: bool | None = None,
    cover_duration: float = 1.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Mengirim 1 video ke TikTok (Draft atau Direct Post), lalu menghapus file lokal jika sukses."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File video tidak ditemukan: {file_path}")

    filename = os.path.basename(file_path)
    base_name, _ = os.path.splitext(filename)
    parent_dir = os.path.basename(os.path.dirname(os.path.abspath(file_path)))
    caption_txt_path = os.path.join(os.path.dirname(file_path), f"{base_name}.txt")

    # Deteksi preset akun berdasarkan argument, subfolder, atau integration_id
    detected_acc = account_key
    if not detected_acc:
        if parent_dir in TIKTOK_ACCOUNTS:
            detected_acc = parent_dir
        elif integration_id:
            for k, conf in TIKTOK_ACCOUNTS.items():
                if conf["integration_id"] == integration_id:
                    detected_acc = k
                    break
    
    # Fallback ke kedaidaily jika affiliate atau berdongeng
    acct_conf = TIKTOK_ACCOUNTS.get(detected_acc or "", {})
    target_integration = integration_id or acct_conf.get("integration_id") or TIKTOK_INTEGRATION_ID or "cmw3byats000ao2745rk4z14k"
    posting_method = method or acct_conf.get("method", "UPLOAD")
    should_cover = apply_cover if apply_cover is not None else acct_conf.get("apply_cover", False)

    # Baca caption kustom dari file .txt pendamping jika ada
    custom_caption = caption
    if not custom_caption and os.path.exists(caption_txt_path):
        try:
            with open(caption_txt_path, "r", encoding="utf-8") as f:
                custom_caption = f.read().strip()
            logger.info(f"📄 Menggunakan caption kustom dari: {os.path.basename(caption_txt_path)}")
        except Exception as exc:
            logger.warning(f"Gagal membaca caption txt: {exc}")

    # Fallback caption & title
    final_caption = custom_caption or acct_conf.get("default_caption", "Video terbaru hari ini! ✨ #fyp")
    final_title = title or acct_conf.get("default_title", "Video Terbaru")

    account_name = acct_conf.get("name", target_integration)
    if dry_run:
        logger.info(
            f"🔍 [DRY RUN] Simulasi kirim: '{filename}' | Akun: {account_name} | "
            f"Mode: {posting_method} | Cover: {should_cover}"
        )
        return {
            "status": "dry_run",
            "file": filename,
            "account": detected_acc,
            "integration_id": target_integration,
            "method": posting_method,
        }

    # Cek & pasang cover khusus channel / per-video jika diaktifkan
    upload_file = file_path
    temp_cover_file = None
    if should_cover:
        cover_image = resolve_channel_cover(file_path, target_integration)
        if cover_image:
            logger.info(f"🎨 Mempersiapkan video dengan cover khusus: {os.path.basename(cover_image)}")
            merged_file = prepend_cover_to_video(file_path, cover_image, duration=cover_duration)
            if merged_file != file_path:
                upload_file = merged_file
                temp_cover_file = merged_file

    try:
        logger.info(f"📤 Mengunggah video '{os.path.basename(upload_file)}' ke Postiz Storage...")
        upload_res = upload_media_to_postiz(upload_file)
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
                    "integration": {"id": target_integration},
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
                        "content_posting_method": posting_method,
                    },
                }
            ],
        }

        headers = {"Authorization": POSTIZ_API_KEY}
        logger.info(f"🚀 Menerbitkan video ke TikTok ({account_name}) dengan mode: {posting_method}...")
        res = requests.post(f"{POSTIZ_BASE_URL}/posts", headers=headers, json=payload, timeout=30.0)

        if res.status_code != 201:
            raise RuntimeError(f"Gagal membuat postingan di Postiz ({res.status_code}): {res.text}")

        result_data = res.json()
        logger.info(f"🎉 SUKSES! Video berhasil diproses ke TikTok: {result_data}")

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
            "account": detected_acc,
            "integration_id": target_integration,
            "method": posting_method,
            "post_id": result_data[0].get("postId") if isinstance(result_data, list) else None,
        }
    finally:
        # Selalu bersihkan file video sementara hasil merge cover jika ada
        if temp_cover_file and os.path.exists(temp_cover_file):
            try:
                os.remove(temp_cover_file)
                logger.info(f"🧹 Temporary video dengan cover dihapus: {temp_cover_file}")
            except Exception:
                pass


def process_queue(limit: int = 1, account_key: str | None = None, dry_run: bool = False):
    """Memproses video antrean multi-akun yang ada di data/tiktok_queue."""
    os.makedirs(QUEUE_DIR, exist_ok=True)
    targets = [account_key] if account_key else ["kedaidaily", "berdongeng"]

    total_processed = 0
    for acc in targets:
        acct_conf = TIKTOK_ACCOUNTS.get(acc, {})
        sub_dir = os.path.join(QUEUE_DIR, acct_conf.get("subfolder", acc))
        os.makedirs(sub_dir, exist_ok=True)

        video_patterns = [
            os.path.join(sub_dir, "*.mp4"),
            os.path.join(sub_dir, "*.mov"),
            os.path.join(sub_dir, "*.webm"),
        ]
        files = []
        for pat in video_patterns:
            files.extend(glob.glob(pat))

        files.sort(key=os.path.getmtime)  # FIFO
        if not files:
            logger.info(f"ℹ️ Antrean untuk akun '{acc}' ({acct_conf.get('name')}) kosong.")
            continue

        logger.info(f"📋 Ditemukan {len(files)} file video untuk akun '{acc}' di '{sub_dir}'.")
        target_files = files[:limit]

        for f_path in target_files:
            try:
                dispatch_tiktok_draft(f_path, account_key=acc, dry_run=dry_run)
                total_processed += 1
            except Exception as exc:
                logger.error(f"❌ Gagal memproses video '{os.path.basename(f_path)}': {exc}", exc_info=True)

    # Cek jika ada video tersisa di root QUEUE_DIR
    root_videos = [f for f in glob.glob(os.path.join(QUEUE_DIR, "*.mp4")) if os.path.isfile(f)]
    if root_videos and not account_key:
        logger.info(f"ℹ️ Ditemukan {len(root_videos)} video di folder root tiktok_queue. Memproses ke default...")
        for f_path in root_videos[:limit]:
            try:
                dispatch_tiktok_draft(f_path, dry_run=dry_run)
                total_processed += 1
            except Exception as exc:
                logger.error(f"❌ Gagal memproses video root: {exc}", exc_info=True)

    logger.info(f"🏁 Selesai memproses antrean. Total video diproses: {total_processed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Punggawa TikTok Queue Dispatcher")
    parser.add_argument("--file", help="Path ke file video tertentu untuk diposting langsung")
    parser.add_argument("--account", choices=["kedaidaily", "berdongeng"], help="Pilih akun target (kedaidaily / berdongeng)")
    parser.add_argument("--caption", help="Caption kustom untuk video")
    parser.add_argument("--title", help="Judul TikTok kustom (max 90 char)")
    parser.add_argument("--method", choices=["UPLOAD", "DIRECT_POST"], help="Override mode posting: UPLOAD (Draf) atau DIRECT_POST (Langsung)")
    parser.add_argument("--integration-id", help="Override ID Integrasi TikTok tujuan")
    parser.add_argument("--limit", type=int, default=1, help="Berapa banyak video di antrean yang diproses per akun (default: 1)")
    parser.add_argument("--all", action="store_true", help="Proses seluruh video yang ada di antrean")
    parser.add_argument("--dry-run", action="store_true", help="Simulasi tanpa mengirim ke API")
    args = parser.parse_args()

    if args.file:
        dispatch_tiktok_draft(
            args.file,
            caption=args.caption,
            title=args.title,
            account_key=args.account,
            integration_id=args.integration_id,
            method=args.method,
            dry_run=args.dry_run,
        )
    else:
        lim = 999 if args.all else args.limit
        process_queue(limit=lim, account_key=args.account, dry_run=args.dry_run)

