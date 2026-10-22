"""
job_scraper.py
Tool scraping dan pencarian lowongan kerja untuk Punggawa Career-Ops Agent.
Mendukung:
1. Ekstraksi detail loker dari direct URL (LinkedIn, Greenhouse, Lever, RemoteOK, dsb).
2. Auto-scouting lowongan remote aktif via feed/API publik (RemoteOK, dsb).
3. Parsing deskripsi loker yang di-paste secara manual.
"""
import hashlib
import html
import logging
import re
from typing import Any
import httpx

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

try:
    from scrapling import Selector
except Exception:
    Selector = None

logger = logging.getLogger("JobScraper")

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def clean_html_text(raw_html: str) -> str:
    """Membersihkan tag HTML, script, style, dan whitespace berlebih."""
    if not raw_html:
        return ""
    # Hapus script dan style
    text = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    # Hapus tag HTML
    text = re.sub(r"<[^>]+>", " ", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Normalkan whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_job_from_url(url: str) -> dict[str, Any]:
    """Mengambil dan mengekstrak deskripsi pekerjaan dari sebuah URL."""
    logger.info(f"Mengambil konten lowongan dari URL: {url}")
    raw_html = ""

    # Prioritas 1: curl_cffi (impersonate Chrome untuk anti-bot)
    if curl_requests:
        try:
            res = curl_requests.get(url, impersonate="chrome110", timeout=20, headers={"User-Agent": USER_AGENT})
            if res.status_code == 200 and len(res.text) > 300:
                raw_html = res.text
        except Exception as exc:
            logger.warning(f"curl_cffi gagal fetch {url}: {exc}")

    # Prioritas 2: httpx fallback
    if not raw_html:
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                res = client.get(url, headers={"User-Agent": USER_AGENT})
                if res.status_code == 200:
                    raw_html = res.text
        except Exception as exc:
            logger.error(f"httpx gagal fetch {url}: {exc}")

    if not raw_html:
        raise RuntimeError(f"Gagal mengunduh halaman lowongan dari URL: {url}")

    # Ekstraksi judul dan konten teks
    title = ""
    description_text = ""

    if Selector:
        try:
            sel = Selector(raw_html)
            # Coba ambil judul dari h1 atau title tag
            h1 = sel.css("h1::text").getall()
            if h1:
                title = " ".join([h.strip() for h in h1 if h.strip()][:2])
            if not title:
                title = sel.css("title::text").get("")

            # Coba ambil kontainer deskripsi pekerjaan yang umum
            job_body = (
                sel.css(".job-description, #job-description, .description, [class*='description'], article, main")
                .get()
            )
            if job_body:
                description_text = clean_html_text(job_body)
        except Exception as exc:
            logger.warning(f"Selector parsing warning: {exc}")

    if not description_text or len(description_text) < 150:
        description_text = clean_html_text(raw_html)

    # Potong jika terlalu panjang agar muat di prompt context
    if len(description_text) > 10000:
        description_text = description_text[:10000]

    return {
        "url": url,
        "title": title.strip() or "Job Posting",
        "raw_text": description_text,
    }


def search_remote_jobs(keywords: list[str] | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """
    Mencari lowongan remote aktif dari feed RemoteOK.
    Memfilter berdasarkan keywords (misal: 'python', 'golang', 'react', 'backend').
    """
    logger.info(f"Mencari lowongan remote dengan keywords: {keywords}")
    url = "https://remoteok.com/api"
    try:
        with httpx.Client(timeout=15.0) as client:
            res = client.get(url, headers={"User-Agent": USER_AGENT})
            if res.status_code != 200:
                logger.warning(f"RemoteOK API mengembalikan status {res.status_code}")
                return []

            data = res.json()
            jobs = [j for j in data if isinstance(j, dict) and j.get("position")]

            filtered: list[dict[str, Any]] = []
            target_kw = [k.lower().strip() for k in (keywords or ["software", "engineer", "developer"])]

            for j in jobs:
                pos = str(j.get("position", "")).lower()
                tags = [str(t).lower() for t in j.get("tags", [])]
                desc = str(j.get("description", "")).lower()

                # Cek kecocokan keyword
                match = any(kw in pos or kw in tags or kw in desc for kw in target_kw)
                if match:
                    job_url = j.get("url") or f"https://remoteok.com/remote-jobs/{j.get('id')}"
                    clean_desc = clean_html_text(j.get("description", ""))
                    filtered.append({
                        "id": f"remok_{j.get('id')}",
                        "company_name": j.get("company", "Unknown Company"),
                        "role_title": j.get("position", "Software Engineer"),
                        "location": j.get("location") or "Worldwide / Remote",
                        "work_mode": "remote",
                        "salary_range": f"${j.get('salary_min', 0)} - ${j.get('salary_max', 0)}" if j.get("salary_max") else "Tidak Disebutkan",
                        "job_url": job_url,
                        "description": clean_desc[:8000],
                    })

                if len(filtered) >= limit:
                    break

            logger.info(f"Ditemukan {len(filtered)} lowongan remote sesuai kriteria.")
            return filtered
    except Exception as exc:
        logger.error(f"Gagal mencari lowongan remote: {exc}")
        return []


def generate_job_hash(company: str, title: str, url: str) -> str:
    """Menghasilkan ID unik untuk lowongan kerja."""
    key = f"{company.strip().lower()}:{title.strip().lower()}:{url.strip()}"
    return f"job_{hashlib.md5(key.encode('utf-8')).hexdigest()[:12]}"
