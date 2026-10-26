"""
Brave Search API Client for Multi-Source Research.
Mendukung pencarian referensi pendukung multi-sumber agar artikel kode-abc
memiliki minimal 2 sumber kredibel, lebih komprehensif, kaya fakta, dan objektif.
"""
import logging
import os
import re
import urllib.parse
from typing import Any

import httpx

from config.settings import settings
from orchestrator.tools.base import register_tool

logger = logging.getLogger("BraveSearch")

BRAVE_SEARCH_API_URL = "https://api.search.brave.com/res/v1/web/search"

# Domain yang diabaikan agar tidak dijadikan sumber sekunder artikel
EXCLUDED_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "pinterest.com",
    "reddit.com",       # Forum diskusi non-editorial (opsional, bisa diizinkan jika relevan)
    "linkedin.com",
    "quora.com",
}


def get_domain(url: str) -> str:
    """Ekstrak nama domain bersih dari URL (tanpa www)."""
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return netloc.replace("www.", "").strip()
    except Exception:
        return ""


def clean_search_query(topic: str) -> str:
    """
    Membersihkan query topik agar optimal saat dicari di Brave Search:
    - Menghapus prefix seperti 'Bedah Repositori: ', 'Liputan Tren: ', dsb.
    - Menangani pola owner/repo GitHub agar mencari ulasan/dokumentasi terkait.
    - Menghapus hashtag atau karakter aneh yang mengganggu pencarian.
    """
    q = re.sub(
        r"^(bedah repositori|eksplorasi repositori|liputan tren|trending weekly):\s*",
        "",
        topic,
        flags=re.IGNORECASE,
    )
    # Jika format GitHub owner/repo
    repo_match = re.search(r"([a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+)", q)
    if repo_match:
        repo_clean = repo_match.group(1).replace("/", " ")
        return f"{repo_clean} github"

    # Hapus karakter khusus dan normalisasi spasi
    q = re.sub(r"#\w+", "", q)
    q = re.sub(r"[^\w\s\-\.]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q[:90]


def search_brave(
    query: str,
    count: int = 5,
    freshness: str | None = None,
    timeout: float = 12.0,
) -> list[dict[str, Any]]:
    """
    Eksekusi pencarian web melalui Brave Search API.
    :param query: Kata kunci pencarian
    :param count: Jumlah hasil (maks 10)
    :param freshness: Filter waktu pencarian ('pd', 'pw', 'pm', 'py')
    :param timeout: Timeout request dalam detik
    """
    api_key = settings.BRAVE_API_KEY or os.getenv("BRAVE_API_KEY")
    if not api_key:
        logger.warning("BRAVE_API_KEY tidak diset di konfigurasi (.env). Pencarian multi-sumber dilewati.")
        return []

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }

    params: dict[str, Any] = {
        "q": query,
        "count": min(count, 10),
    }
    if freshness:
        params["freshness"] = freshness

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(BRAVE_SEARCH_API_URL, params=params, headers=headers)
            if resp.status_code != 200:
                logger.warning(
                    f"Brave Search API merespons status {resp.status_code}: {resp.text[:200]}"
                )
                return []

            data = resp.json()
            raw_results = data.get("web", {}).get("results", [])
            results = []
            for item in raw_results:
                url = item.get("url", "")
                title = item.get("title", "")
                desc = item.get("description", "")
                if url and title:
                    results.append({
                        "title": title,
                        "url": url,
                        "description": desc,
                        "domain": get_domain(url),
                    })
            return results
    except Exception as exc:
        logger.warning(f"Error saat memanggil Brave Search API: {exc}")
        return []


def find_related_sources(
    primary_url: str,
    topic: str,
    max_sources: int = 2,
) -> list[dict[str, str]]:
    """
    Mencari 1-2 sumber artikel sekunder yang independen dan berbeda domain
    dari sumber primer untuk memperkaya konteks artikel dan mengurangi subjektivitas.
    """
    query = clean_search_query(topic)
    if not query:
        return []

    logger.info(f"🔍 [Brave Search] Mencari sumber referensi pendukung untuk query: '{query}'...")
    candidates = search_brave(query=query, count=8)
    if not candidates:
        return []

    primary_domain = get_domain(primary_url)
    seen_domains = {primary_domain}
    discovered: list[dict[str, str]] = []

    for cand in candidates:
        url = cand.get("url", "")
        domain = cand.get("domain", "")
        if not url or not domain:
            continue

        # Lewati domain yang sama dengan sumber primer (agar sudut pandang berbeda)
        if domain in seen_domains:
            continue

        # Lewati media sosial atau agregator non-editorial
        if any(ex in domain for ex in EXCLUDED_DOMAINS):
            continue

        # Hindari URL homepage root (misal 'https://techcrunch.com/')
        parsed = urllib.parse.urlparse(url)
        if not parsed.path or parsed.path == "/":
            continue

        seen_domains.add(domain)
        discovered.append({
            "title": cand.get("title", ""),
            "url": url,
            "domain": domain,
        })

        if len(discovered) >= max_sources:
            break

    logger.info(
        f"✅ [Brave Search] Menemukan {len(discovered)} sumber pendukung: {[d['domain'] for d in discovered]}"
    )
    return discovered

