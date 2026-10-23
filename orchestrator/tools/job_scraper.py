"""
job_scraper.py
Tool scraping dan pencarian lowongan kerja untuk Punggawa Career-Ops Agent (Clara).
Menggunakan remote Playwright CDP (`connect_over_cdp`) yang terhubung ke container Browserless,
dengan dukungan deteksi blocker deterministik dan integrasi Human-in-the-Loop (HITL).
"""
import asyncio
import concurrent.futures
import hashlib
import html
import logging
import os
import re
from typing import Any
import httpx

from config.settings import settings
from orchestrator.tools.hitl import (
    check_for_blockers,
    detect_page_blockers,
    handle_hitl_trigger,
    handle_hitl_trigger_sync,
    request_human_intervention,
    request_human_intervention_sync,
)

# Playwright / Patchright CDP Client
try:
    from playwright.async_api import async_playwright
except ImportError:
    try:
        import sys
        import patchright
        import patchright.async_api
        sys.modules["playwright"] = patchright
        sys.modules["playwright.async_api"] = patchright.async_api
        from playwright.async_api import async_playwright
    except ImportError:
        async_playwright = None

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
    text = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_ats_vendor(url: str, raw_html: str = "") -> str:
    """Mendeteksi platform ATS (Applicant Tracking System) dari URL dan DOM."""
    url_lower = url.lower()
    html_lower = raw_html[:5000].lower() if raw_html else ""

    if "ashbyhq.com" in url_lower or "ashby" in html_lower:
        return "Ashby"
    if "greenhouse.io" in url_lower or "grnh.se" in url_lower or "greenhouse" in html_lower:
        return "Greenhouse"
    if "lever.co" in url_lower or "lever" in html_lower:
        return "Lever"
    if "myworkdayjobs.com" in url_lower or "workday" in url_lower:
        return "Workday"
    if "smartrecruiters.com" in url_lower:
        return "SmartRecruiters"
    if "workable.com" in url_lower:
        return "Workable"
    if "bamboohr.com" in url_lower:
        return "BambooHR"
    if "rippling.com" in url_lower:
        return "Rippling"
    if "recruitee.com" in url_lower:
        return "Recruitee"
    if "remoteok.com" in url_lower:
        return "RemoteOK Board"
    if "linkedin.com" in url_lower:
        return "LinkedIn Jobs"
    if "indeed.com" in url_lower:
        return "Indeed"

    return "Custom / Career Portal"


def get_browserless_cdp_url() -> str:
    """
    Menyusun URL WebSocket CDP lengkap dengan query parameter:
    - ?token=<TOKEN>
    - &--user-data-dir=/data/profile (persistensi session cookie/login)
    - &--disable-blink-features=AutomationControlled
    """
    token = getattr(settings, "BROWSERLESS_TOKEN", None) or os.getenv("BROWSERLESS_TOKEN", "punggawa_super_secret_token_123")
    base_ws = getattr(settings, "BROWSERLESS_WS_URL", None) or os.getenv("BROWSERLESS_WS_URL", "ws://127.0.0.1:3000")
    base_ws = base_ws.rstrip("/")

    params = [
        f"token={token}",
        "--user-data-dir=/data/profile",
        "--disable-blink-features=AutomationControlled",
    ]
    return f"{base_ws}?{'&'.join(params)}"


async def fetch_job_via_cdp(url: str, job_id: str = "") -> dict[str, Any]:
    """
    Mengambil halaman loker via remote Playwright CDP ke container Browserless.
    Mendeteksi blocker secara deterministik dan memicu HITL jika diperlukan.
    """
    if not async_playwright:
        raise RuntimeError("Playwright / Patchright tidak tersedia di environment runtime.")

    ws_url = get_browserless_cdp_url()
    logger.info(f"Menghubungkan ke container Browserless via CDP: {ws_url.split('?')[0]}...")

    # 1. Lifecycle Browser Connection via CDP
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.connect_over_cdp(ws_url)
        except Exception as cdp_err:
            logger.error(
                f"❌ Gagal menghubungkan ke container Browserless via CDP ({ws_url}): {cdp_err}. "
                f"Pastikan container Browserless menyala dan port 3000 dapat diakses."
            )
            raise ConnectionError(f"Browserless CDP connection failed: {cdp_err}") from cdp_err

        # 2. Context Management: gunakan context yang ada atau buat baru
        if browser.contexts and len(browser.contexts) > 0:
            context = browser.contexts[0]
        else:
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
            )

        # 3. Tab/Page Management: Buka tab baru
        page = await context.new_page()
        try:
            logger.info(f"Navigasi ke target URL via Browserless: {url}")
            # Navigasi dengan timeout aman 30 detik (30000ms) dan domcontentloaded
            response = await page.goto(
                url,
                timeout=30000,
                wait_until="domcontentloaded",
            )

            status_code = response.status if response else 200
            final_url = page.url or url
            raw_html = await page.content()

            # 4. Deteksi Blocker Deterministik (Login Wall, CAPTCHA, 403, Cloudflare, 429)
            blocker = check_for_blockers(status_code, final_url, raw_html)
            if blocker and blocker in ["LOGIN_WALL", "CAPTCHA", "CLOUDFLARE_BLOCK", "RATE_LIMITED", "ACCESS_DENIED"]:
                logger.warning(f"🚨 Blocker '{blocker}' terdeteksi pada '{final_url}'. Memicu Human-in-the-Loop.")
                hitl_res = await handle_hitl_trigger(
                    job_id=job_id or "job-hitl",
                    target_url=final_url,
                    blocker_type=blocker,
                    action_required=(
                        f"Terdeteksi {blocker} saat mengakses URL lowongan. "
                        f"Silakan buka browser debugger untuk menyelesaikan autentikasi atau CAPTCHA."
                    ),
                )
                return {
                    "url": final_url,
                    "hitl_triggered": True,
                    "blocker_type": blocker,
                    "hitl_payload": hitl_res,
                    "raw_text": "",
                    "ats_vendor": detect_ats_vendor(final_url, raw_html),
                }

            # 5. Jika lolos dan bersih: Ekstraksi judul dan snapshot teks
            title = await page.title()
            if not title or title.strip() == "":
                h1_el = await page.query_selector("h1")
                if h1_el:
                    title = (await h1_el.inner_text()) or ""

            # Ambil elemen kontainer deskripsi lowongan kerja yang umum
            body_el = await page.query_selector(
                ".job-description, #job-description, .description, [class*='description'], article, main"
            )
            description_text = ""
            if body_el:
                body_html = await body_el.inner_html()
                description_text = clean_html_text(body_html)

            if not description_text or len(description_text) < 150:
                description_text = clean_html_text(raw_html)

            if len(description_text) > 10000:
                description_text = description_text[:10000]

            return {
                "url": final_url,
                "title": title.strip() or "Job Posting",
                "ats_vendor": detect_ats_vendor(final_url, raw_html),
                "raw_text": description_text,
                "raw_html": raw_html,
                "hitl_triggered": False,
            }
        finally:
            # Selalu tutup tab halaman, JANGAN memanggil browser.close()
            try:
                await page.close()
            except Exception as exc:
                logger.debug(f"Error saat menutup page Browserless: {exc}")


def _fetch_job_http_fallback(url: str, job_id: str = "") -> dict[str, Any]:
    """Fallback scraper menggunakan curl_cffi / httpx jika Browserless CDP offline."""
    logger.info(f"Menjalankan HTTP fallback scraper untuk URL: {url}")
    raw_html = ""
    status_code = 200
    final_url = url

    # Prioritas 1: curl_cffi
    if curl_requests:
        try:
            res = curl_requests.get(url, impersonate="chrome110", timeout=20, headers={"User-Agent": USER_AGENT})
            status_code = res.status_code
            final_url = getattr(res, "url", url)
            raw_html = res.text
        except Exception as exc:
            logger.warning(f"curl_cffi fallback gagal fetch {url}: {exc}")

    # Prioritas 2: httpx
    if not raw_html:
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                res = client.get(url, headers={"User-Agent": USER_AGENT})
                status_code = res.status_code
                final_url = str(res.url)
                raw_html = res.text
        except Exception as exc:
            logger.error(f"httpx fallback gagal fetch {url}: {exc}")

    # Deteksi Blocker pada fallback
    blocker = check_for_blockers(status_code, final_url, raw_html)
    if blocker and blocker in ["LOGIN_WALL", "CAPTCHA", "CLOUDFLARE_BLOCK", "RATE_LIMITED", "ACCESS_DENIED"]:
        logger.warning(f"🚨 Blocker '{blocker}' terdeteksi pada HTTP fallback '{final_url}'.")
        hitl_res = handle_hitl_trigger_sync(
            job_id=job_id or "job-hitl",
            target_url=final_url,
            blocker_type=blocker,
            action_required=(
                f"Terdeteksi {blocker} saat mengakses URL lowongan. "
                f"Silakan buka browser debugger untuk menyelesaikan autentikasi atau CAPTCHA."
            ),
        )
        return {
            "url": final_url,
            "hitl_triggered": True,
            "blocker_type": blocker,
            "hitl_payload": hitl_res,
            "raw_text": "",
            "ats_vendor": detect_ats_vendor(final_url, raw_html),
        }

    if not raw_html:
        raise RuntimeError(f"Gagal mengunduh halaman lowongan dari URL: {url} (HTTP {status_code})")

    title = ""
    description_text = ""

    if Selector:
        try:
            sel = Selector(raw_html)
            h1 = sel.css("h1::text").getall()
            if h1:
                title = " ".join([h.strip() for h in h1 if h.strip()][:2])
            if not title:
                title = sel.css("title::text").get("")

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

    if len(description_text) > 10000:
        description_text = description_text[:10000]

    return {
        "url": url,
        "title": title.strip() or "Job Posting",
        "ats_vendor": detect_ats_vendor(url, raw_html),
        "raw_text": description_text,
        "raw_html": raw_html,
        "hitl_triggered": False,
    }


def fetch_job_from_url(url: str, job_id: str = "") -> dict[str, Any]:
    """
    Mengambil dan mengekstrak deskripsi lowongan kerja dari sebuah URL.
    Mengutamakan Playwright CDP ke container Browserless, dan secara otomatis
    beralih ke HTTP fallback jika container Browserless tidak tersedia.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, fetch_job_via_cdp(url, job_id=job_id)).result()
        else:
            return asyncio.run(fetch_job_via_cdp(url, job_id=job_id))
    except (ConnectionError, RuntimeError) as cdp_err:
        logger.warning(f"Browserless CDP tidak tersedia ({cdp_err}). Beralih ke fallback HTTP...")
        return _fetch_job_http_fallback(url, job_id=job_id)
    except Exception as general_err:
        logger.error(f"Error tak terduga saat fetch CDP: {general_err}. Menjalankan fallback HTTP...")
        return _fetch_job_http_fallback(url, job_id=job_id)


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
