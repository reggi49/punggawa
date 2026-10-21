"""Publisher client for KodePintar platform with retry handling and category mapping."""
import logging
import os
import time
import httpx
from config.settings import settings

logger = logging.getLogger("KodePintarPublisher")


class PublishError(Exception):
    def __init__(self, message, status_code=None, body=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


CATEGORY_MAP = {
    "programming": "635692a2dbac7bb9ad31f00d",
    "technology": "635693c8dbac7bb9ad31f00e",
    "tech": "635693c8dbac7bb9ad31f00e",
    "internet of things": "6387239b2b0055b07adc11ec",
    "iot": "6387239b2b0055b07adc11ec",
    "video": "63a1841a2df5e4a9c714422b",
    "games": "6a7a8d0dfdc56a24e518eb03",
}


def resolve_category(category: str) -> str:
    raw = (category or "").lower().strip()
    if len(raw) == 24 and all(c in "0123456789abcdef" for c in raw):
        return raw
    return CATEGORY_MAP.get(raw, "635693c8dbac7bb9ad31f00e")


def publish_article(
    ai_data: dict,
    category: str,
    image_base64: str,
    max_retries: int = 3,
) -> dict:
    """
    Kirim payload artikel lengkap ke API KodePintar.
    Granular timeout: connect=15s, read=60s, write=30s, pool=10s.
    """
    api_endpoint = settings.API_ENDPOINT or os.getenv("API_ENDPOINT")
    secret_key = settings.SECRET_KEY or os.getenv("SECRET_KEY")
    user_id = settings.USER_ID or os.getenv("USER_ID", "635def0b6094eb6d770dc213")

    if not api_endpoint:
        raise PublishError("API_ENDPOINT tidak diset di konfigurasi (.env)")
    if not secret_key:
        raise PublishError("SECRET_KEY tidak diset di konfigurasi (.env)")

    raw_tags = ai_data.get("tags", "")
    if isinstance(raw_tags, list):
        tags_formatted = ", ".join(str(t).strip() for t in raw_tags if t)
    else:
        tags_formatted = str(raw_tags or "")

    payload = {
        "title": ai_data["title"],
        "description": ai_data.get("meta_desc") or ai_data.get("description", ""),
        "content": ai_data["content"],
        "categoryId": resolve_category(category),
        "userId": user_id,
        "imageBase64": image_base64,
        "tags": tags_formatted,
        "locale": ai_data.get("locale", "id"),
        "translationKey": ai_data.get("translationKey", ""),
    }

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    http_timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=10.0)
    locale_name = ai_data.get("locale", "id").upper()
    logger.info(f"📤 [PUBLISH] Mengirim artikel [{locale_name}] ke {api_endpoint}...")

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                logger.info(f"🔄 [PUBLISH-RETRY] Percobaan {attempt}/{max_retries} [{locale_name}]...")

            with httpx.Client(follow_redirects=True, timeout=http_timeout) as client:
                res = client.post(api_endpoint, json=payload, headers=headers)

            if res.history:
                redirect_trail = " -> ".join(
                    [f"{r.status_code} ({r.url})" for r in res.history] + [f"{res.status_code} ({res.url})"]
                )
                logger.info(f"🔀 [PUBLISH] Request dialihkan: {redirect_trail}")

            if res.status_code >= 500:
                last_error = PublishError(
                    f"API server error (HTTP {res.status_code}) dari {res.url}",
                    status_code=res.status_code,
                    body=res.text[:500],
                )
                logger.warning(f"⚠️ [PUBLISH] Server error {res.status_code} pada percobaan {attempt}")
                time.sleep(2 * attempt)
                continue
            elif res.status_code >= 400:
                logger.error(f"❌ [PUBLISH] API menolak request (HTTP {res.status_code}): {res.text[:300]}")
                raise PublishError(
                    f"API menolak request (HTTP {res.status_code}) dari {res.url}: {res.text[:200]}",
                    status_code=res.status_code,
                    body=res.text[:500],
                )

            try:
                result = res.json()
            except Exception:
                raise PublishError(
                    f"Response API bukan JSON valid (HTTP {res.status_code}): {res.text[:300]}",
                    status_code=res.status_code,
                    body=res.text[:500],
                )

            if not result.get("success"):
                raise PublishError(f"API success=false: {result}", status_code=res.status_code, body=str(result)[:500])

            data = result.get("data")
            article_id = data.get("_id") if isinstance(data, dict) else result.get("id")
            logger.info(f"✅ [PUBLISH] Artikel [{locale_name}] berhasil diterbitkan (ID: {article_id})")
            return {"success": True, "status_code": res.status_code, "article_id": article_id}

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = PublishError(f"Gangguan jaringan saat menghubungi {api_endpoint}: {type(e).__name__} ({e})")
            logger.warning(f"⚠️ [PUBLISH] Network timeout/error pada percobaan {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
        except httpx.RequestError as e:
            last_error = PublishError(f"Gagal koneksi ke API ({api_endpoint}): {e}")
            logger.warning(f"⚠️ [PUBLISH] Request error pada percobaan {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)

    if last_error:
        raise last_error
    raise PublishError(f"Gagal menerbitkan artikel setelah {max_retries} percobaan.")

