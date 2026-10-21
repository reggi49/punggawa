"""GitHub Trending Weekly scraper tool without heavy headless browser."""
import logging
import re
from typing import Any
import requests

from orchestrator.tools.base import register_tool

logger = logging.getLogger("GitHubTrendingTool")


@register_tool(
    name="get_github_trending_weekly",
    description="Mengambil daftar repositori trending mingguan dari GitHub tanpa browser headless.",
    sensitive=False,
)
def get_github_trending_weekly(language: str = "", max_items: int = 5) -> list[dict[str, Any]]:
    """
    Mengikis daftar repositori trending mingguan dari GitHub menggunakan HTTP request ringan.
    Mengekstrak nama repo, deskripsi, bahasa pemrograman, dan jumlah bintang mingguan.
    """
    clean_lang = language.strip().lower() if language else ""
    path = f"/{clean_lang}" if clean_lang else ""
    url = f"https://github.com/trending{path}?since=weekly&spoken_language_code="

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        articles = re.findall(r'<article class="Box-row">(.*?)</article>', html, re.DOTALL)
        results: list[dict[str, Any]] = []

        for art in articles:
            # 1. Ekstrak nama repositori dari tag h2 / h1
            h2_match = re.search(r'<h2[^>]*>.*?<a[^>]+href="/([^"?#]+)"', art, re.DOTALL)
            if not h2_match:
                repo_match = re.search(r'href="/([^"/]+/[^"/]+)"', art)
                repo_path = repo_match.group(1).strip() if repo_match else None
            else:
                repo_path = h2_match.group(1).strip().strip("/")

            # Lewati tautan non-repo seperti sponsor atau profil individual
            if not repo_path or "/" not in repo_path or repo_path.startswith("sponsors/"):
                continue

            # 2. Deskripsi repositori
            desc_match = re.search(r'<p class="col-9[^"]*">(.*?)</p>', art, re.DOTALL)
            description = re.sub(r'<.*?>', '', desc_match.group(1)).strip() if desc_match else ""

            # 3. Bahasa pemrograman
            lang_match = re.search(r'itemprop="programmingLanguage">(.*?)</span>', art)
            if lang_match:
                prog_lang = lang_match.group(1).strip()
            elif clean_lang:
                prog_lang = clean_lang.capitalize()
            else:
                prog_lang = "General"

            # 4. Jumlah bintang (stars) minggu ini
            stars_match = re.search(r'(\d[\d,]*)\s+stars this week', art)
            weekly_stars = stars_match.group(1).replace(',', '') if stars_match else "0"

            results.append({
                "repo_name": repo_path,
                "repo_url": f"https://github.com/{repo_path}",
                "description": description,
                "language": prog_lang,
                "stars_this_week": int(weekly_stars),
            })

            if len(results) >= max_items:
                break

        logger.info(f"GitHub Trending: berhasil mengambil {len(results)} repositori (language='{language or 'all'}')")
        return results

    except Exception as exc:
        logger.error(f"Gagal mengambil GitHub Trending (language='{language}'): {exc}", exc_info=True)
        return []
