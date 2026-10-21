"""Web scraping and search tools."""
import logging
import re
from typing import Any
import httpx
from orchestrator.tools.base import register_tool

logger = logging.getLogger("WebTools")


@register_tool(
    name="fetch_web_content",
    description="Mengambil dan mengekstrak teks utama dari sebuah URL web publik.",
    sensitive=False,
)
def fetch_web_content(url: str, max_length: int = 2000) -> dict[str, Any]:
    """
    Mengambil isi webpage via HTTP GET dan membersihkan tag HTML.
    :param url: Alamat URL yang ingin dibaca (harus diawali http:// atau https://)
    :param max_length: Panjang karakter maksimal konten yang dikembalikan
    """
    if not (url.startswith("http://") or url.startswith("https://")):
        return {"error": "URL harus diawali dengan http:// atau https://"}

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PunggawaAgent/1.0; +https://github.com/reggi/punggawa)"
    }

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()

            # Bersihkan script/style tags dan ekstrak teks
            html_text = resp.text
            clean_text = re.sub(r"<(script|style).*?>.*?</\1>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
            clean_text = re.sub(r"<[^>]+>", " ", clean_text)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            snippet = clean_text[:max_length]
            return {
                "url": url,
                "status_code": resp.status_code,
                "length": len(clean_text),
                "content": snippet,
                "truncated": len(clean_text) > max_length,
            }
    except httpx.TimeoutException:
        logger.warning(f"Timeout saat mengakses web: {url}")
        return {"error": f"Request ke {url} mengalami timeout (10 detik)."}
    except Exception as exc:
        logger.error(f"Gagal mengambil webpage {url}: {exc}")
        return {"error": f"Gagal membaca URL: {str(exc)}"}

