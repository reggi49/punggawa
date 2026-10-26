"""Publisher client for Dongeng CMS (Bogorstore) with duplicate search and multipart upload."""
import logging
import os
from typing import Any
import httpx

from config.settings import settings
from orchestrator.tools.youtube_client import get_best_youtube_bg

logger = logging.getLogger("DongengPublisher")

HARDCODED_CATEGORIES: dict[str, str] = {
    "1": "Legenda",
    "2": "Mite",
    "3": "Fabel",
    "4": "Hikayat",
    "5": "Sage",
    "6": "Parabel",
    "7": "Jenaka",
}


class DongengPublishError(Exception):
    def __init__(self, message: str, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    """Helper untuk mengekstrak array item dari berbagai struktur respons API."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        if isinstance(data, dict):
            data = data.get("data", [])
        if isinstance(data, list):
            return data
    return []


def is_already_in_cms(video_id: str) -> bool:
    """
    Pengecekan anti-duplikat ke search API CMS Bogorstore.
    Menerapkan prinsip Fail-Closed: Jika request gagal/timeout, lemparkan Exception
    agar proses dibatalkan demi keamanan integritas database CMS.
    """
    search_url = settings.DONGENG_CMS_SEARCH_URL
    if not search_url:
        logger.warning("DONGENG_CMS_SEARCH_URL tidak diset, melewati cek duplikat.")
        return False

    target = str(video_id).strip()
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(search_url, params={"keyword": target})
            if resp.status_code != 200:
                raise DongengPublishError(
                    f"Search API CMS gagal (HTTP {resp.status_code}): {resp.text[:200]}",
                    status_code=resp.status_code,
                )
            payload = resp.json()

        for item in _extract_items(payload):
            if not isinstance(item, dict):
                continue
            for key in ("videoId", "videoid", "video_id"):
                val = item.get(key)
                if val is not None and str(val).strip() == target:
                    return True
        return False

    except Exception as exc:
        logger.error(f"Gagal memeriksa duplikat CMS untuk video '{target}': {exc}")
        raise


def post_to_cms(
    video_id: str,
    info: dict[str, Any],
    final_title: str,
    category_id: str | int,
    thumbnail_path: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Mengunggah video dan thumbnail portrait ke Bogorstore CMS via HTTP multipart/form-data.
    """
    post_url = settings.DONGENG_CMS_POST_URL
    if not post_url:
        raise DongengPublishError("DONGENG_CMS_POST_URL tidak diset di konfigurasi")

    cat_str = str(category_id).strip()
    category_name = HARDCODED_CATEGORIES.get(cat_str, HARDCODED_CATEGORIES["3"])
    background_url = get_best_youtube_bg(video_id)

    data = {
        "videoId": video_id,
        "channelId": info.get("channel_id", ""),
        "channelTitle": info.get("channel_title", ""),
        "title": final_title,
        "description": info.get("description", ""),
        "published": "1",
        "featured": "1",
        "background": background_url,
        "categories[0]": category_name,
    }

    if dry_run:
        logger.info(f"🧪 [DRY-RUN] Akan POST ke CMS Bogorstore: videoId={video_id}, title='{final_title}', category='{category_name}'")
        return {
            "status": "dry-run",
            "id": video_id,
            "title": final_title,
            "category": category_name,
            "success": True,
        }

    if not os.path.exists(thumbnail_path):
        raise DongengPublishError(f"File thumbnail tidak ditemukan di path: {thumbnail_path}")

    headers = {"Accept": "application/json"}

    try:
        logger.info(f"📤 [DONGENG-CMS] Mengunggah video '{video_id}' ke {post_url}...")
        with open(thumbnail_path, "rb") as f:
            files = {"thumbnail": (os.path.basename(thumbnail_path), f, "image/jpeg")}
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(post_url, data=data, files=files, headers=headers)

        if resp.status_code in [200, 201]:
            logger.info("🎉 [DONGENG-CMS] Post dan thumbnail berhasil terbit ke CMS!")
            try:
                return resp.json()
            except Exception:
                return {"success": True, "status_code": resp.status_code, "text": resp.text[:200]}

        raise DongengPublishError(
            f"CMS Bogorstore menolak request (HTTP {resp.status_code}): {resp.text[:300]}",
            status_code=resp.status_code,
            body=resp.text[:500],
        )

    except Exception as exc:
        logger.error(f"Error saat mengirim ke CMS Bogorstore: {exc}")
        raise


def post_story_to_cms(
    channel_id: str,
    title: str,
    video_id: str,
    thumbnail: str | None = None,
    published: int | bool = 1,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Mengunggah konten Stories / Shorts YouTube ke CMS Bogorstore via JSON API.

    Endpoint:
        POST /api/posts/stories (atau alias /api/stories, /api/shorts)

    Parameter:
        - channel_id: String (Wajib)
        - title: String (Wajib)
        - videoId: String 11 digit ID atau video_url (Wajib)
        - thumbnail: String URL opsional (jika kosong CMS auto-resolve ke hqdefault YouTube)
        - published: int/bool (1 = aktif, 0 = draft). Default: 1
    """
    stories_url = getattr(settings, "DONGENG_CMS_STORIES_URL", "") or "https://bogorstore.com/agoose/api/posts/stories"

    clean_video_id = str(video_id).strip()
    pub_val = 1 if published in (1, True, "1") else 0

    payload: dict[str, Any] = {
        "channel_id": str(channel_id).strip(),
        "title": str(title).strip(),
        "videoId": clean_video_id,
        "published": pub_val,
    }
    if thumbnail:
        payload["thumbnail"] = str(thumbnail).strip()

    if dry_run:
        logger.info(f"🧪 [DRY-RUN] Akan POST Story/Short ke {stories_url}: {payload}")
        return {
            "status": "dry-run",
            "id": clean_video_id,
            "title": title,
            "channel_id": channel_id,
            "type": "story",
            "success": True,
            "data": payload,
        }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        logger.info(f"📤 [DONGENG-CMS] Mengunggah Story/Shorts '{clean_video_id}' ke {stories_url}...")
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(stories_url, json=payload, headers=headers)

        if resp.status_code in (200, 201):
            logger.info("🎉 [DONGENG-CMS] Story / Short berhasil ditambahkan ke CMS!")
            try:
                res_data = resp.json()
                if isinstance(res_data, dict):
                    res_data.setdefault("success", True)
                return res_data
            except Exception:
                return {"status": "success", "success": True, "status_code": resp.status_code, "text": resp.text[:200]}

        raise DongengPublishError(
            f"CMS Stories menolak request (HTTP {resp.status_code}): {resp.text[:300]}",
            status_code=resp.status_code,
            body=resp.text[:500],
        )

    except Exception as exc:
        logger.error(f"Error saat mengirim Story ke CMS Bogorstore: {exc}")
        raise


__all__ = [
    "HARDCODED_CATEGORIES",
    "DongengPublishError",
    "is_already_in_cms",
    "post_to_cms",
    "post_story_to_cms",
]

