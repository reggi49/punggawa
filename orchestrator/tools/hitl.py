"""
hitl.py
Human-in-the-Loop (HITL) Protocol and Blocker Detection for Clara (Career Scout Agent).
Handles detection of Login Walls, CAPTCHAs, Cloudflare WAF blocks, and triggers
operator alerts via Telegram webhook with browser debugger URLs and resume endpoints.
"""
import asyncio
import logging
from typing import Any, Literal
import httpx

from config.settings import settings

logger = logging.getLogger("ClaraHITL")

BlockerType = Literal["LOGIN_WALL", "CAPTCHA", "CLOUDFLARE_BLOCK", "RATE_LIMITED", "ACCESS_DENIED", "JOB_NOT_FOUND"]


def detect_page_blockers(status_code: int, url: str, raw_html: str = "") -> BlockerType | None:
    """
    Mendeteksi secara deterministik apakah halaman terhambat oleh blocker akses:
    1. Status HTTP 403/429/404
    2. Cloudflare Turnstile / Challenge / Captcha
    3. Login Wall / Auth Redirect
    """
    url_lower = url.lower()
    html_lower = raw_html[:10000].lower() if raw_html else ""

    # 1. HTTP Status Checks
    if status_code == 429:
        return "RATE_LIMITED"
    if status_code == 403:
        if "cloudflare" in html_lower or "access denied" in html_lower or "attention required" in html_lower:
            return "CLOUDFLARE_BLOCK"
        return "ACCESS_DENIED"
    if status_code == 404:
        return "JOB_NOT_FOUND"

    # 2. CAPTCHA & Cloudflare WAF Detection
    captcha_signatures = [
        "cf-turnstile",
        "challenges.cloudflare.com",
        "cf-challenge",
        "ray id:",
        "g-recaptcha",
        "hcaptcha",
        "captcha-box",
        "security check to continue",
        "verify you are human",
        "please verify you are not a robot",
        "press & hold",
    ]
    for sig in captcha_signatures:
        if sig in html_lower or sig in url_lower:
            return "CAPTCHA"

    # 3. Login Wall / Auth Challenge Detection
    login_signatures = [
        "/login",
        "/checkpoint/challenge",
        "/checkpoint/lg/login",
        "authwall",
        "sign in to linkedin",
        "join to view full profile",
        "login to view this job",
        "enter your credentials",
    ]
    for sig in login_signatures:
        if sig in url_lower:
            return "LOGIN_WALL"

    # Deteksi form login spesifik jika halaman sangat pendek dan memiliki password input
    if "type=\"password\"" in html_lower and len(raw_html) < 4000:
        return "LOGIN_WALL"

    return None


async def request_human_intervention(
    job_id: str,
    target_url: str,
    blocker_type: BlockerType,
    action_required: str,
    debugger_url: str = "",
    resume_endpoint: str = "",
) -> dict[str, Any]:
    """
    Menghentikan browsing otomatis dan mengirimkan sinyal intervensi manusia (HITL).
    Mengirimkan alert ke Telegram jika kredensial tersedia dan mengembalikan state PAUSED_HITL.
    """
    logger.warning(
        f"🚨 [HITL ALERT] Clara terhambat oleh '{blocker_type}' di URL: {target_url}. Job ID: {job_id}."
    )

    if not debugger_url:
        debugger_url = f"{settings.BROWSER_DEBUGGER_BASE_URL}?job_id={job_id}"
    if not resume_endpoint:
        resume_endpoint = f"/api/jobs/{job_id}/resume"

    # 1. Format pesan notifikasi untuk Telegram / Discord
    pesan = (
        f"🚨 <b>Clara Butuh Bantuan (HITL Alert)</b>\n"
        f"<b>Job ID:</b> <code>{job_id}</code>\n"
        f"<b>Blocker:</b> {blocker_type}\n"
        f"<b>URL:</b> {target_url}\n"
        f"<b>Instruksi:</b> {action_required}\n\n"
        f"🔗 <b>Akses Browser Debugger:</b>\n{debugger_url}\n\n"
        f"✅ <b>Lanjutkan Task (Resume Link):</b>\nhttps://api.punggawa.internal{resume_endpoint}"
    )

    # 2. Kirim notifikasi via Webhook Telegram jika dikonfigurasi
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": settings.TELEGRAM_CHAT_ID,
                        "text": pesan,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
                if res.status_code == 200:
                    logger.info(f"✅ Notifikasi HITL berhasil terkirim ke Telegram chat {settings.TELEGRAM_CHAT_ID}.")
                else:
                    logger.warning(f"Gagal mengirim notifikasi Telegram: {res.status_code} - {res.text}")
        except Exception as exc:
            logger.error(f"Error koneksi webhook Telegram HITL: {exc}")
    else:
        logger.info("Telegram bot token/chat_id tidak disetel, notifikasi dicatat di log lokal.")

    # 3. Kembalikan payload state interrupt LangGraph
    return {
        "status": "PAUSED_HITL",
        "job_id": job_id,
        "target_url": target_url,
        "blocker_type": blocker_type,
        "action_required": action_required,
        "debugger_url": debugger_url,
        "resume_endpoint": resume_endpoint,
        "waiting_for_resume": True,
    }


def request_human_intervention_sync(
    job_id: str,
    target_url: str,
    blocker_type: BlockerType,
    action_required: str,
    debugger_url: str = "",
    resume_endpoint: str = "",
) -> dict[str, Any]:
    """Synchronous bridge wrapper untuk pemanggilan request_human_intervention di node sync LangGraph."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(
                asyncio.run,
                request_human_intervention(
                    job_id, target_url, blocker_type, action_required, debugger_url, resume_endpoint
                ),
            ).result()
    else:
        return asyncio.run(
            request_human_intervention(
                job_id, target_url, blocker_type, action_required, debugger_url, resume_endpoint
            )
        )


# Aliases for unified HITL API
check_for_blockers = detect_page_blockers


async def handle_hitl_trigger(
    job_id: str,
    target_url: str,
    blocker_type: BlockerType,
    action_required: str = "",
    debugger_url: str = "",
    resume_endpoint: str = "",
) -> dict[str, Any]:
    """Trigger asynchronous handler untuk intervensi manusia saat blocker terdeteksi."""
    if not action_required:
        action_required = (
            f"Terdeteksi {blocker_type} saat mengakses URL lowongan. "
            f"Silakan buka browser debugger untuk menyelesaikan autentikasi atau CAPTCHA."
        )
    return await request_human_intervention(
        job_id=job_id,
        target_url=target_url,
        blocker_type=blocker_type,
        action_required=action_required,
        debugger_url=debugger_url,
        resume_endpoint=resume_endpoint,
    )


def handle_hitl_trigger_sync(
    job_id: str,
    target_url: str,
    blocker_type: BlockerType,
    action_required: str = "",
    debugger_url: str = "",
    resume_endpoint: str = "",
) -> dict[str, Any]:
    """Trigger synchronous handler untuk intervensi manusia saat blocker terdeteksi."""
    if not action_required:
        action_required = (
            f"Terdeteksi {blocker_type} saat mengakses URL lowongan. "
            f"Silakan buka browser debugger untuk menyelesaikan autentikasi atau CAPTCHA."
        )
    return request_human_intervention_sync(
        job_id=job_id,
        target_url=target_url,
        blocker_type=blocker_type,
        action_required=action_required,
        debugger_url=debugger_url,
        resume_endpoint=resume_endpoint,
    )


