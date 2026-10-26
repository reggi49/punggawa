"""Push notification trigger client for Bogorstore Dongeng CMS (cmsAgoose).

Zero LLM Cost: Calls the Laravel web route to dispatch FCM NotificationJob.
"""
import logging
from typing import Any
import requests

from config.settings import settings

logger = logging.getLogger("CmsNotifier")

DEFAULT_NOTIFICATION_BASE_URL = "https://bogorstore.com/agoose/posts/sendnotification"


def trigger_post_notification(
    post_id: str | int,
    session_cookie: str | None = None,
    mode: str = "smart",
    delay_minutes: int | None = None,
    schedule_time: str | None = None,
    timeout: float = 12.0,
) -> dict[str, Any]:
    """
    Memicu push notification otomatis untuk postingan dongeng yang baru diterbitkan.
    Memanggil route web Laravel cmsAgoose: GET /posts/sendnotification/{id}
    yang mendispatch NotificationJob (Google FCM v1 API).

    Mendukung Smart Anti-Collision & Scheduling:
        - mode="smart" (Default): Menjadwalkan ke jam utama (17:00:00 WIB) atau slot kosong
          berikutnya (+2 jam ke 19:00, 21:00, atau 12:00 esok hari jika terdeteksi bentrok).
        - mode="instant": Dikirimkan saat itu juga.
        - mode="delay": Tunda selama delay_minutes (15, 30, 60, 120, 180 menit).
        - mode="specific": Jadwalkan pada waktu spesifik (misal '19:30').

    Args:
        post_id: ID postingan di database CMS Bogorstore (wajib integer/numerik).
        session_cookie: Cookie session Laravel (opsional).
        mode: Mode anti-bentrok/penjadwalan ('smart' | 'instant' | 'delay' | 'specific').
        delay_minutes: Menit penundaan jika mode='delay'.
        schedule_time: Format jam spesifik 'HH:MM' jika mode='specific'.
        timeout: Batas waktu request HTTP dalam detik.

    Returns:
        dict dengan format hasil eksekusi.
    """
    clean_id = str(post_id).strip()
    if not clean_id or not clean_id.isdigit():
        err = f"Invalid post_id '{post_id}'. post_id wajib berupa ID numerik database CMS."
        logger.warning(f"⚠️ [CMS-NOTIFIER] {err}")
        return {
            "success": False,
            "post_id": post_id,
            "mode": mode,
            "status_code": None,
            "target_url": "",
            "message": err,
            "error": err,
        }

    base_url = (settings.DONGENG_CMS_NOTIFICATION_URL or "").strip()
    if not base_url:
        base_url = DEFAULT_NOTIFICATION_BASE_URL

    if "{id}" in base_url:
        target_url = base_url.replace("{id}", clean_id)
    else:
        target_url = f"{base_url.rstrip('/')}/{clean_id}"

    # Susun parameter Smart Anti-Collision untuk backend Laravel
    params: dict[str, Any] = {}
    if mode:
        params["mode"] = mode
    if delay_minutes is not None:
        params["delay"] = int(delay_minutes)
    if schedule_time:
        params["time"] = str(schedule_time).strip()

    headers = {
        "User-Agent": "Punggawa-Notifier/1.0 (Automated Notification Trigger)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # Pasang cookie jika dikonfigurasi
    cookie_str = (session_cookie or settings.DONGENG_CMS_COOKIE or "").strip()
    if cookie_str:
        headers["Cookie"] = cookie_str

    logger.info(f"🔔 [CMS-NOTIFIER] Mengirim trigger push notification ke: {target_url} (params: {params})")

    try:
        response = requests.get(
            target_url,
            headers=headers,
            params=params,
            timeout=timeout,
            allow_redirects=True,
        )

        # Laravel controller mengembalikan HTTP 302 redirect ke posts.index
        # Dengan allow_redirects=True, status akhir bisa 200 (setelah redirect)
        # atau status awal 302 jika redirects ditangkap. Keduanya valid.
        is_success = response.status_code in (200, 301, 302, 303)

        if is_success:
            msg = f"Push notification untuk post #{clean_id} berhasil dipicu (Mode: {mode.upper()}, HTTP {response.status_code})."
            logger.info(f"🎉 [CMS-NOTIFIER] {msg}")
            return {
                "success": True,
                "post_id": int(clean_id),
                "mode": mode,
                "status_code": response.status_code,
                "target_url": response.url,
                "message": msg,
                "error": None,
            }
        else:
            err = f"CMS mengembalikan status HTTP {response.status_code}: {response.text[:200]}"
            logger.warning(f"⚠️ [CMS-NOTIFIER] {err}")
            return {
                "success": False,
                "post_id": int(clean_id) if clean_id.isdigit() else clean_id,
                "mode": mode,
                "status_code": response.status_code,
                "target_url": target_url,
                "message": err,
                "error": err,
            }

    except requests.exceptions.Timeout:
        err = f"Timeout saat memicu notifikasi CMS ke {target_url} (>{timeout}s)"
        logger.error(f"❌ [CMS-NOTIFIER] {err}")
        return {
            "success": False,
            "post_id": clean_id,
            "mode": mode,
            "status_code": None,
            "target_url": target_url,
            "message": err,
            "error": err,
        }
    except requests.exceptions.RequestException as exc:
        err = f"Gagal menghubungi server CMS: {str(exc)}"
        logger.error(f"❌ [CMS-NOTIFIER] {err}")
        return {
            "success": False,
            "post_id": clean_id,
            "mode": mode,
            "status_code": None,
            "target_url": target_url,
            "message": err,
            "error": err,
        }
