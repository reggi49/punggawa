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


def extract_fallback_query(primary_url: str = "", topic: str = "") -> str:
    """
    Ekstrak query alternatif yang ringkas dan efektif jika query utama tidak membuahkan hasil:
    - Jika primary_url adalah GitHub (github.com/owner/repo), ambil nama repo + ulasan/fitur.
    - Jika URL memiliki slug artikel yang deskriptif, ambil kata-kata dari slug.
    - Jika topik terlalu panjang, ekstrak 5-7 kata kunci utama.
    """
    if primary_url:
        try:
            parsed = urllib.parse.urlparse(primary_url)
            path = parsed.path.strip("/")
            if "github.com" in parsed.netloc.lower():
                parts = [p for p in path.split("/") if p]
                if len(parts) >= 2:
                    repo_clean = parts[1].replace("-", " ").replace("_", " ")
                    return f"{repo_clean} review OR guide"
                elif len(parts) == 1:
                    return f"{parts[0]} review"
            elif path:
                last_segment = path.split("/")[-1]
                slug_words = re.sub(r"[_\-\.]+", " ", last_segment).strip()
                tokens = [w for w in slug_words.split() if len(w) > 2 and not w.isdigit()]
                if len(tokens) >= 2:
                    return " ".join(tokens[:6])
        except Exception:
            pass

    words = re.findall(r"\b[A-Za-z0-9_\-\.]{2,}\b", topic)
    if words:
        return " ".join(words[:6])
    return ""


def clean_search_query(topic: str, primary_url: str = "") -> str:
    """
    Membersihkan query topik agar optimal saat dicari di Brave Search:
    - Menghapus prefix seperti 'Bedah Repositori: ', 'Liputan Tren: ', dsb.
    - Menangani pola owner/repo GitHub agar mencari ulasan/dokumentasi terkait tanpa membatasi ke domain github.
    - Menghapus hashtag atau karakter aneh yang mengganggu pencarian.
    - Membatasi panjang query maksimal 8 kata agar tidak over-specific.
    """
    q = re.sub(
        r"^(bedah repositori trending|bedah repositori|eksplorasi repositori github|eksplorasi repositori|liputan tren|trending weekly):\s*",
        "",
        topic,
        flags=re.IGNORECASE,
    )
    # Jika format GitHub owner/repo ada di dalam string
    repo_match = re.search(r"([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)", q)
    if repo_match:
        owner = repo_match.group(1).replace("-", " ").strip()
        repo_name = repo_match.group(2).replace("-", " ").replace("_", " ").strip()
        # Jika nama repo cukup unik (>= 4 karakter), gunakan nama repo langsung agar pencarian luas
        q = f"{repo_name} {owner}" if len(repo_name) < 4 else f"{repo_name}"
    else:
        # Hapus karakter khusus dan normalisasi spasi
        q = re.sub(r"#\w+", "", q)
        q = re.sub(r"[^\w\s\-\.]", " ", q)
        q = re.sub(r"\s+", " ", q).strip()

    # Batasi agar tidak lebih dari 8 kata
    words = q.split()
    if len(words) > 8:
        q = " ".join(words[:7])

    return q[:80]


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
            raw_results = (data.get("web") or {}).get("results", [])
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
    Mendukung fallback query otomatis jika pencarian pertama tidak membuahkan hasil.
    """
    query = clean_search_query(topic, primary_url=primary_url)
    primary_domain = get_domain(primary_url)
    
    # Jika sumber utama adalah GitHub, jangan biarkan hasil pencarian hanya mengulang halaman internal GitHub
    search_q = query
    if "github.com" in primary_domain and "-site:github.com" not in search_q:
        search_q = f"{search_q} -site:github.com"

    candidates: list[dict[str, Any]] = []

    if search_q:
        logger.info(f"🔍 [Brave Search] Mencari sumber referensi pendukung untuk query: '{search_q}'...")
        candidates = search_brave(query=search_q, count=8)

    # Fallback jika query utama tidak menghasilkan kandidat
    if not candidates:
        import time
        time.sleep(1.2)  # Menghindari limit 1 req/detik pada Brave API free tier
        fallback_q = extract_fallback_query(primary_url=primary_url, topic=topic)
        if "github.com" in primary_domain and "-site:github.com" not in fallback_q:
            fallback_q = f"{fallback_q} -site:github.com"
        if fallback_q and fallback_q.lower() != (search_q or "").lower():
            logger.info(
                f"🔄 [Brave Search] Query utama '{search_q}' nihil. Mencoba fallback query: '{fallback_q}'..."
            )
            candidates = search_brave(query=fallback_q, count=8)

    if not candidates:
        logger.warning(
            f"⚠️ [Brave Search] Tidak ada kandidat sumber ditemukan untuk topic='{topic}' / url='{primary_url}'."
        )
        return []

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

        # Hindari URL homepage portal umum (misal 'https://techcrunch.com/'), kecuali domain resmi proyek itu sendiri (misal 'ghostty.org')
        parsed = urllib.parse.urlparse(url)
        is_root = not parsed.path or parsed.path == "/"
        is_project_domain = any(word in domain for word in query.lower().split() if len(word) >= 4)
        if is_root and not is_project_domain:
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

