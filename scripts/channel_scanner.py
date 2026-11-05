#!/usr/bin/env python3
"""
Deep YouTube Channel Scanner for Punggawa Dongeng Catalog.
Memindai seluruh katalog video dari 10 target channel YouTube menggunakan paginasi uploads playlist,
melakukan filter kualitas & deduplikasi, lalu menyimpannya ke tabel 'youtube_dongeng_catalog'.
Sangat hemat kuota YouTube Data API (hanya ~1 unit per 50 video!).
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

# Ensure project root in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import settings
from orchestrator.connections import postgres_pool
from orchestrator.tools.youtube_client import looks_like_skip

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ChannelScanner")


def get_existing_processed_ids() -> set[str]:
    """Mengambil seluruh video ID yang sudah ada di content_schedules dan execution logs."""
    existing: set[str] = set()
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM content_schedules;")
                for row in cur.fetchall():
                    payload_raw = row[0]
                    payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw or "{}")
                    v_id = payload.get("input_data", {}).get("video_id") or payload.get("video_id")
                    if v_id:
                        existing.add(str(v_id).strip().lower())
                
                cur.execute("SELECT video_id FROM youtube_dongeng_catalog WHERE status = 'completed';")
                for row in cur.fetchall():
                    if row[0]:
                        existing.add(str(row[0]).strip().lower())
    except Exception as exc:
        logger.warning(f"Gagal membaca existing video ID: {exc}")
    return existing


def scan_single_channel(
    channel_id: str,
    client: httpx.Client,
    api_key: str,
    existing_processed: set[str],
    max_pages: int = 50,
) -> dict[str, Any]:
    """Memindai seluruh video dari satu channel YouTube hingga tuntas."""
    # 1. Uploads playlist ID format: ganti 'UC' dengan 'UU'
    uploads_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else channel_id

    total_scanned = 0
    total_inserted = 0
    total_skipped = 0
    page_token = None
    channel_title = channel_id
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        params = {
            "part": "snippet,contentDetails",
            "playlistId": uploads_id,
            "maxResults": 50,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        res = client.get("https://www.googleapis.com/youtube/v3/playlistItems", params=params)
        if res.status_code != 200:
            logger.warning(f"[{channel_id}] Gagal mengambil playlistItems ({res.status_code}): {res.text}")
            break

        data = res.json()
        items = data.get("items", [])
        if not items:
            break

        records_to_insert = []
        for item in items:
            total_scanned += 1
            snippet = item.get("snippet", {})
            v_id = snippet.get("resourceId", {}).get("videoId")
            title = (snippet.get("title") or "").strip()
            desc = snippet.get("description", "")
            ch_title = snippet.get("channelTitle", channel_title)
            channel_title = ch_title
            pub_at = snippet.get("publishedAt")
            thumbs = snippet.get("thumbnails", {})
            thumb_url = thumbs.get("high", {}).get("url") or thumbs.get("default", {}).get("url")

            if not v_id or not title:
                continue

            # Abaikan video private/deleted
            if title.lower() in ("private video", "deleted video"):
                continue

            # Filter kualitas dongeng
            if looks_like_skip(title):
                total_skipped += 1
                status = "skipped"
            elif v_id.lower() in existing_processed:
                status = "completed"
            else:
                status = "unprocessed"

            records_to_insert.append((
                v_id,
                channel_id,
                ch_title,
                title,
                desc,
                thumb_url,
                pub_at,
                status,
            ))

        # Bulk upsert ke database
        if records_to_insert:
            with postgres_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        INSERT INTO youtube_dongeng_catalog (
                            video_id, channel_id, channel_title, title, 
                            description, thumbnail_url, published_at, status, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (video_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            channel_title = EXCLUDED.channel_title,
                            updated_at = NOW()
                        WHERE youtube_dongeng_catalog.status != 'completed';
                        """,
                        records_to_insert,
                    )
                    conn.commit()
            total_inserted += len([r for r in records_to_insert if r[7] == "unprocessed"])

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    logger.info(
        f"✅ [{channel_title}] Tuntas discan: {total_scanned} video dicek | "
        f"{total_inserted} kandidat baru siap pakai | {total_skipped} diskip SOP."
    )
    return {
        "channel_id": channel_id,
        "channel_title": channel_title,
        "total_scanned": total_scanned,
        "total_new_candidates": total_inserted,
        "total_skipped": total_skipped,
        "pages_fetched": page_count,
    }


def scan_all_channels(max_pages_per_channel: int = 50) -> dict[str, Any]:
    """Memindai seluruh 10 channel yang ada di DONGENG_TARGET_CHANNELS."""
    api_key = settings.YOUTUBE_API_KEY
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY belum dikonfigurasi di .env")

    raw_ch = settings.DONGENG_TARGET_CHANNELS
    channels: list[str] = json.loads(raw_ch) if isinstance(raw_ch, str) else raw_ch
    logger.info(f"🚀 Memulai Deep Scan untuk {len(channels)} target channel YouTube...")

    existing_processed = get_existing_processed_ids()
    logger.info(f"📊 Menemukan {len(existing_processed)} video riil yang sudah pernah dikerjakan.")

    results = []
    total_quota_used = 0

    with httpx.Client(timeout=20.0) as client:
        for ch_id in channels:
            res = scan_single_channel(
                channel_id=ch_id,
                client=client,
                api_key=api_key,
                existing_processed=existing_processed,
                max_pages=max_pages_per_channel,
            )
            results.append(res)
            total_quota_used += res["pages_fetched"]

    logger.info(
        f"🎉 Deep Scan Selesai! Total kuota YouTube API yang terpakai: HANYA {total_quota_used} unit "
        f"dari total kuota gratis 10.000 unit/hari ({total_quota_used / 10000 * 100:.2f}%)."
    )
    return {
        "channels_scanned": len(results),
        "total_quota_used": total_quota_used,
        "details": results,
    }


if __name__ == "__main__":
    scan_all_channels()

