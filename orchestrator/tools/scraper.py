"""Dual-layer web scraper with Fast HTTP fetcher, stealth fallback, and GitHub parser."""
import logging
import urllib.parse

logger = logging.getLogger("Scraper")

try:
    from scrapling import Selector
except Exception as e:
    Selector = None
    logger.error(f"Gagal import scrapling.Selector: {e}")

try:
    from scrapling.fetchers import Fetcher
except Exception as e:
    Fetcher = None
    logger.debug(f"Fetcher tidak tersedia (membutuhkan patchright): {e}")

try:
    from scrapling.fetchers import StealthyFetcher
except Exception as e:
    StealthyFetcher = None
    logger.debug(f"StealthyFetcher tidak tersedia (membutuhkan patchright): {e}")

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

try:
    import httpx
except Exception:
    httpx = None

try:
    from googlenewsdecoder import gnewsdecoder
except Exception:
    gnewsdecoder = None

MIN_CONTENT_LEN = 200


def _resolve_url(url: str) -> str:
    """Jika URL berasal dari Google News RSS (news.google.com/rss/articles/...), decode ke URL sumber asli."""
    if "news.google.com" in url.lower():
        if gnewsdecoder is not None:
            try:
                res = gnewsdecoder(url)
                if isinstance(res, dict) and res.get("decoded_url"):
                    decoded = res["decoded_url"]
                    logger.info(f"🔄 [GNews Decoder] Berhasil resolve URL asli: {decoded}")
                    return decoded
            except Exception as e:
                logger.warning(f"Gagal mendecode Google News URL '{url}': {e}")
    return url


def _extract_text(page, url: str) -> str:
    """Ekstrak teks bersih dari page, dengan parser spesifik untuk GitHub README."""
    if page is None:
        return ""

    parsed = urllib.parse.urlparse(url)

    # 1. Khusus GitHub: Ambil dari .markdown-body
    if "github.com" in parsed.netloc:
        try:
            els = page.css(".markdown-body *::text").getall()
            txt = "\n".join(t.strip() for t in els if t and t.strip())
            if txt.strip():
                logger.info(f"Terdeteksi GitHub, menggunakan parser .markdown-body ({len(txt)} chars).")
                return txt
        except Exception as e:
            logger.warning(f"Parser GitHub gagal: {e}")

    # 2. General parser via page.get_all_text()
    try:
        all_text = page.get_all_text(
            ignore_tags=("script", "style", "nav", "footer", "header")
        )
        text = str(all_text)
        paras = [ln.strip() for ln in text.split("\n") if len(ln.strip()) > 20]
        if paras:
            return "\n\n".join(paras)
        if text.strip():
            return text.strip()
    except Exception as e:
        logger.warning(f"get_all_text gagal: {e}")

    # 3. Fallback CSS text dari article / p
    try:
        parts = page.css("article ::text").getall() + page.css("p::text").getall()
        paras = [t.strip() for t in parts if t and len(t.strip()) > 20]
        if paras:
            return "\n\n".join(paras)
    except Exception as e:
        logger.warning(f"Fallback css text gagal: {e}")

    return ""


def _fetch_fast(url: str):
    """Layer 1: Fast HTTP Fetcher dengan multi-engine fallback (scrapling -> curl_cffi -> httpx)."""
    # 1. Coba Scrapling Fetcher bawaan jika tersedia
    if Fetcher is not None:
        try:
            return Fetcher.get(url, stealthy_headers=True)
        except TypeError:
            try:
                return Fetcher.get(url)
            except Exception as e:
                logger.warning(f"Fetcher.get error for {url}: {e}")
        except Exception as e:
            logger.warning(f"Fetcher.get error for {url}: {e}")

    # 2. Fallback ke curl_cffi dengan browser TLS impersonation
    if curl_requests is not None and Selector is not None:
        try:
            resp = curl_requests.get(
                url,
                impersonate="chrome",
                timeout=25,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
            if resp.status_code == 200 and resp.text:
                return Selector(resp.text)
            else:
                logger.warning(f"curl_cffi fetch returned status {resp.status_code} for {url}")
        except Exception as e:
            logger.warning(f"curl_cffi fallback error for {url}: {e}")

    # 3. Fallback ke httpx standar
    if httpx is not None and Selector is not None:
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"},
                timeout=25,
                follow_redirects=True,
            )
            if resp.status_code == 200 and resp.text:
                return Selector(resp.text)
            else:
                logger.warning(f"httpx fetch returned status {resp.status_code} for {url}")
        except Exception as e:
            logger.warning(f"httpx fallback error for {url}: {e}")

    return None


def _fetch_stealth(url: str):
    """Layer 2: StealthyFetcher (Camoufox headless browser) untuk menembus WAF/Cloudflare."""
    if StealthyFetcher is None:
        return None
    try:
        return StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            solve_cloudflare=True,
            timeout=60000,
        )
    except Exception as e:
        logger.error(
            f"StealthyFetcher gagal: {e}. Pastikan browser terpasang via `scrapling install`."
        )
        return None


def scrape_data(target_urls: str | list[str]) -> tuple[str, str]:
    """
    Scrape seluruh target URL dengan dual-layer fetcher.
    Mendukung decode URL Google News RSS secara otomatis.
    Mengembalikan (combined_text, url_references).
    """
    if isinstance(target_urls, str):
        url_list = [u.strip() for u in target_urls.split(",") if u.strip()]
    else:
        url_list = [str(u).strip() for u in target_urls if str(u).strip()]

    combined_clean_text = ""
    url_references = ""
    failed_details = []

    logger.info(f"🔗 [SCRAPER] Memproses {len(url_list)} sumber URL...")

    if Fetcher is None and StealthyFetcher is None and curl_requests is None and httpx is None:
        raise RuntimeError("Tidak ada engine HTTP fetcher yang terpasang (scrapling/curl_cffi/httpx).")

    for i, raw_url in enumerate(url_list):
        idx = i + 1
        url = _resolve_url(raw_url)
        try:
            # Layer 1: Fast HTTP
            page = _fetch_fast(url)
            clean_text = _extract_text(page, url)

            # Layer 2: Jika hasil tipis atau kosong, coba StealthyFetcher
            if len(clean_text.strip()) < MIN_CONTENT_LEN:
                logger.info(
                    f"Konten tipis ({len(clean_text.strip())} chars) di {url}. Beralih ke StealthyFetcher..."
                )
                stealth_page = _fetch_stealth(url)
                stealth_text = _extract_text(stealth_page, url)
                if len(stealth_text.strip()) > len(clean_text.strip()):
                    clean_text = stealth_text

            if clean_text and len(clean_text.strip()) >= 20:
                combined_clean_text += f"\n\n--- REF {idx} ---\n{clean_text}"
                url_references += f"- {url}\n"
                logger.info(f"✅ Scrape {idx} sukses ({len(clean_text)} karakter): {url}")
            else:
                err_msg = f"URL {idx} ({url}): Konten kosong atau terblokir WAF/Cloudflare ({len(clean_text.strip())} karakter)"
                failed_details.append(err_msg)
                logger.warning(f"⚠️ Scrape {idx} kosong/terblokir: {url}")

        except Exception as e:
            err_msg = f"URL {idx} ({url}): Error fetch ({e})"
            failed_details.append(err_msg)
            logger.error(f"❌ Scrape {idx} error: {e} | URL: {url}")

    if not combined_clean_text:
        detail_str = "; ".join(failed_details) if failed_details else "Tidak ada respons konten"
        raise ValueError(
            f"Semua target scraping gagal ({len(url_list)} URL). Detail: {detail_str}"
        )

    return combined_clean_text, url_references

