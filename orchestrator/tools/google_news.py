"""Google News RSS Feed scraper tool (zero quota / free XML parsing)."""
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any
import requests

from orchestrator.tools.base import register_tool

logger = logging.getLogger("GoogleNewsTool")


@register_tool(
    name="get_google_news_topics",
    description="Mengambil berita teknologi & topik terkini via Google News RSS Feed resmi (tanpa API key).",
    sensitive=False,
)
def get_google_news_topics(
    keyword: str = "technology",
    max_items: int = 5,
    lang: str = "en",
) -> list[dict[str, Any]]:
    """
    Mengambil feed XML dari Google News RSS resmi tanpa API key.
    - Menggunakan endpoint kurasi topik teknologi resmi:
      https://news.google.com/rss/headlines/section/topic/TECHNOLOGY
    - Mendukung mode pencarian kata kunci spesifik:
      https://news.google.com/rss/search?q={query}
    - Mendukung lokalisasi:
      'en' (default/internasional: hl=en-US&gl=US&ceid=US:en)
      'id' (Indonesia: hl=id&gl=ID&ceid=ID:id)
    """
    is_id = str(lang).lower().strip() in ("id", "id-id", "indonesia")
    hl = "id" if is_id else "en-US"
    gl = "ID" if is_id else "US"
    ceid = "ID:id" if is_id else "US:en"

    clean_kw = (keyword or "").strip()

    # Jika keyword kosong atau 'technology' / 'tech', gunakan section headline resmi
    if not clean_kw or clean_kw.lower() in ("technology", "tech"):
        rss_url = f"https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl={hl}&gl={gl}&ceid={ceid}"
    else:
        encoded_query = urllib.parse.quote(clean_kw)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={hl}&gl={gl}&ceid={ceid}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(rss_url, headers=headers, timeout=12)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items: list[dict[str, Any]] = []

        for entry in root.findall(".//item")[:max_items]:
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            pub_date = (entry.findtext("pubDate") or "").strip()
            source = (entry.findtext("source") or "").strip()

            if not title:
                continue

            items.append({
                "title": title,
                "url": link,
                "published_at": pub_date,
                "source": source or "Google News",
            })

        logger.info(
            f"Google News: berhasil mengambil {len(items)} berita dari {rss_url}"
        )
        return items

    except Exception as exc:
        logger.error(f"Gagal mengambil Google News untuk keyword '{keyword}' (lang={lang}): {exc}", exc_info=True)
        return []
