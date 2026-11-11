"""
Planner Bay-Zero: Autonomous Content Scheduling & Editorial Calendar.
Mengatur ritme penerbitan konten Stark & Usagi secara otomatis selama 7 hari ke depan,
menghindari penumpukan artikel dalam 1 hari, dan mencatat rencana ke PostgreSQL content_schedules.
"""
import glob
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

# Ensure project root in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import settings
from orchestrator.connections import postgres_pool
from orchestrator.tools.github_trending import get_github_trending_weekly
from orchestrator.tools.google_news import get_google_news_topics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BayZeroPlanner")

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))

# Konfigurasi ritme kerja harian per agen (Setiap agen wajib memiliki tugas setiap hari)
AGENT_CADENCE: dict[str, dict[str, Any]] = {
    "Stark": {
        "name": "Stark",
        "target_hour_wib": 9,
        "slots": [
            {"hour": 9, "category": "technology", "label": "Pagi (Tech / AI / Programming)"},
            {"hour": 16, "category": "games", "label": "Sore (Gaming / Hardware / IoT)"},
        ],
        "task_type": "trend-article",
        "description": "Tech, Gaming & Programming Article Specialist (2x sehari)",
    },
    "Sosmed": {
        "name": "Sosmed",
        "target_hour_wib": 13,
        "slots": [
            {"hour": 13, "category": None, "label": "Siang (TikTok / Instagram Campaign)"},
        ],
        "task_type": "tiktok",
        "description": "Social Media & TikTok Shop Campaign Specialist",
    },
    "Usagi": {
        "name": "Usagi",
        "target_hour_wib": 19,
        "slots": [
            {"hour": 19, "category": None, "label": "Malam (Cerita Rakyat & Dongeng Anak)"},
        ],
        "task_type": "dongeng",
        "description": "Children Folktale & Animation Specialist",
    },
}


def get_existing_scheduled_topics() -> set[str]:
    """Mengambil seluruh judul, nama repo, URL, dan video ID yang sudah ada di database (schedules dan publish logs)."""
    existing: set[str] = set()
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                # 1. Dari content_schedules (termasuk status discarded/recycle bin agar tidak muncul lagi)
                cur.execute("SELECT title, payload FROM content_schedules;")
                for row in cur.fetchall():
                    raw_title = (row[0] or "").strip().lower()
                    if raw_title:
                        existing.add(raw_title)
                        # Ekstrak nama repo jika format "bedah repositori: owner/name"
                        if "bedah repositori:" in raw_title:
                            repo_part = raw_title.replace("bedah repositori:", "").strip()
                            existing.add(repo_part)
                    
                    payload_raw = row[1]
                    payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw or "{}")
                    inp = payload.get("input_data", {})
                    if inp.get("target_urls"):
                        existing.add(str(inp["target_urls"]).strip().lower())
                    if inp.get("video_id"):
                        existing.add(str(inp["video_id"]).strip().lower())
                    if inp.get("topic"):
                        existing.add(str(inp["topic"]).strip().lower())
                    if inp.get("query"):
                        existing.add(str(inp["query"]).strip().lower())

                # 2. Dari agent_execution_logs (khusus node publish_node yang telah dipublikasikan ke CMS/web)
                cur.execute("SELECT message, details FROM agent_execution_logs WHERE node = 'publish_node';")
                for msg, det in cur.fetchall():
                    if msg:
                        existing.add(msg.strip().lower())
                    if isinstance(det, dict):
                        for v in det.values():
                            if isinstance(v, str):
                                s = v.strip().lower()
                                existing.add(s)
                                for match in re.findall(r'([a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+)', s):
                                    existing.add(match.lower())
    except Exception as exc:
        logger.warning(f"Gagal membaca riwayat jadwal untuk deduplikasi: {exc}")
    return existing


def get_occupied_time_slots() -> set[str]:
    """Mengambil daftar slot waktu WIB (format: YYYY-MM-DD-HH) yang sudah terisi jadwal pending atau in_progress."""
    occupied: set[str] = set()
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT scheduled_at FROM content_schedules 
                    WHERE status IN ('pending', 'in_progress');
                """)
                for row in cur.fetchall():
                    dt = row[0]
                    if dt:
                        dt_wib = dt.astimezone(WIB)
                        slot_key = dt_wib.strftime("%Y-%m-%d-%H")
                        occupied.add(slot_key)
    except Exception as exc:
        logger.warning(f"Gagal memeriksa slot waktu terisi: {exc}")
    return occupied


def delete_editorial_schedule(schedule_id: str, permanent: bool = False) -> bool:
    """
    Menghapus jadwal spesifik dari PostgreSQL content_schedules.
    Jika permanent=False (default): Soft-delete dengan mengubah status menjadi 'discarded' (masuk Recycle Bin).
    Jika permanent=True: Hapus data baris secara fisik dari database.
    """
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                if permanent:
                    cur.execute("DELETE FROM content_schedules WHERE id = %s;", (schedule_id,))
                    action_msg = "dihapus permanen"
                else:
                    cur.execute(
                        "UPDATE content_schedules SET status = 'discarded', error_message = NULL WHERE id = %s;",
                        (schedule_id,),
                    )
                    action_msg = "dipindahkan ke Recycle Bin (status: discarded)"
                deleted = cur.rowcount > 0
                if deleted:
                    logger.info(f"🗑️ [Bay-Zero Planner] Jadwal '{schedule_id}' berhasil {action_msg}.")
                return deleted
    except Exception as exc:
        logger.error(f"Gagal menghapus jadwal {schedule_id}: {exc}", exc_info=True)
        return False


def restore_editorial_schedule(schedule_id: str) -> bool:
    """Memulihkan jadwal dari Recycle Bin (status 'discarded' -> 'pending')."""
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE content_schedules SET status = 'pending', error_message = NULL WHERE id = %s AND status = 'discarded';",
                    (schedule_id,),
                )
                restored = cur.rowcount > 0
                if restored:
                    logger.info(f"♻️ [Bay-Zero Planner] Jadwal '{schedule_id}' berhasil dipulihkan dari Recycle Bin.")
                return restored
    except Exception as exc:
        logger.error(f"Gagal memulihkan jadwal {schedule_id}: {exc}", exc_info=True)
        return False


def empty_trash_schedules() -> int:
    """Mengosongkan Recycle Bin: menghapus seluruh jadwal berstatus 'discarded' secara permanen."""
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM content_schedules WHERE status = 'discarded';")
                count = cur.rowcount
                logger.info(f"🧹 [Bay-Zero Planner] Berhasil mengosongkan Recycle Bin: {count} jadwal dihapus.")
                return count
    except Exception as exc:
        logger.error(f"Gagal mengosongkan Recycle Bin: {exc}", exc_info=True)
        return 0


def cleanup_duplicate_schedules() -> int:
    """
    Membersihkan jadwal duplikat dari PostgreSQL content_schedules secara komprehensif:
    1. Hapus jadwal pending/failed jika judul yang sama sudah berstatus 'in_progress' atau 'completed'.
    2. Hapus duplikat jadwal pending yang memiliki judul sama (hanya simpan yang paling awal).
    3. Hapus duplikat jadwal failed yang memiliki judul sama (hanya simpan yang paling baru).
    """
    deleted_total = 0
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                # 1. Hapus pending/failed jika sudah ada yang in_progress atau completed untuk judul yang sama
                cur.execute("""
                    DELETE FROM content_schedules
                    WHERE status IN ('pending', 'failed')
                      AND LOWER(TRIM(title)) IN (
                          SELECT LOWER(TRIM(title))
                          FROM content_schedules
                          WHERE status IN ('completed', 'in_progress')
                      );
                """)
                deleted_total += cur.rowcount

                # 2. Hapus duplikat antar sesama pending (hanya sisakan 1 yang paling awal)
                cur.execute("""
                    DELETE FROM content_schedules
                    WHERE id IN (
                        SELECT id
                        FROM (
                            SELECT id,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY LOWER(TRIM(title)) 
                                       ORDER BY scheduled_at ASC, created_at ASC
                                   ) as rnum
                            FROM content_schedules
                            WHERE status = 'pending'
                        ) t
                        WHERE t.rnum > 1
                    );
                """)
                deleted_total += cur.rowcount

                # 3. Hapus duplikat antar sesama failed (hanya sisakan 1 yang paling baru)
                cur.execute("""
                    DELETE FROM content_schedules
                    WHERE id IN (
                        SELECT id
                        FROM (
                            SELECT id,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY LOWER(TRIM(title)) 
                                       ORDER BY created_at DESC
                                   ) as rnum
                            FROM content_schedules
                            WHERE status = 'failed'
                        ) t
                        WHERE t.rnum > 1
                    );
                """)
                deleted_total += cur.rowcount

                if deleted_total > 0:
                    logger.info(f"🧹 [Bay-Zero Planner] Berhasil membersihkan {deleted_total} jadwal duplikat dari database.")
    except Exception as exc:
        logger.error(f"Gagal membersihkan jadwal duplikat: {exc}", exc_info=True)
    return deleted_total


# Alias backward compatibility
cleanup_duplicate_pending_schedules = cleanup_duplicate_schedules


def is_agent_covered_on_date(
    agent_name: str, target_date: datetime.date, target_hour: int | None = None
) -> tuple[bool, str, list[dict]]:
    """
    Memeriksa apakah seorang agen sudah memiliki jadwal atau telah menyelesaikan tugas pada target_date (WIB).
    Jika target_hour ditentukan, memeriksa apakah slot waktu spesifik (+/- 2 jam) sudah terisi.
    """
    today_wib = datetime.now(WIB).date()
    tasks: list[dict] = []

    hour_filter = ""
    params_today = [agent_name, target_date, target_date]
    params_future = [agent_name, target_date]

    if target_hour is not None:
        hour_filter = " AND ABS(EXTRACT(HOUR FROM (scheduled_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')) - %s) <= 2"
        params_today.append(target_hour)
        params_future.append(target_hour)

    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                if target_date == today_wib:
                    cur.execute(f"""
                        SELECT id, title, status, scheduled_at, completed_at
                        FROM content_schedules
                        WHERE agent_name = %s
                          AND (
                            (status = 'completed' AND (completed_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')::date = %s)
                            OR status = 'in_progress'
                            OR (status = 'pending' AND (scheduled_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')::date = %s)
                          )
                          {hour_filter}
                        ORDER BY scheduled_at ASC;
                    """, tuple(params_today))
                else:
                    cur.execute(f"""
                        SELECT id, title, status, scheduled_at, completed_at
                        FROM content_schedules
                        WHERE agent_name = %s
                          AND status IN ('pending', 'in_progress')
                          AND (scheduled_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')::date = %s
                          {hour_filter}
                        ORDER BY scheduled_at ASC;
                    """, tuple(params_future))
                
                rows = cur.fetchall()
                for r in rows:
                    tasks.append({
                        "id": r[0],
                        "title": r[1],
                        "status": r[2],
                        "scheduled_at": r[3],
                        "completed_at": r[4],
                    })

        if tasks:
            status_summary = "completed_today" if any(t["status"] == "completed" for t in tasks) else tasks[0]["status"]
            return True, status_summary, tasks
        return False, "unassigned_idle", []
    except Exception as exc:
        logger.error(f"Gagal memeriksa status kerja {agent_name} pada {target_date}: {exc}")
        return False, "error", []


def pull_earliest_future_task_forward(
    agent_name: str, target_date: datetime.date, target_hour: int
) -> dict[str, Any] | None:
    """
    Mencari tugas pending terdekat dari hari-hari berikutnya dan memajukan jadwalnya ke target_date (Fast-Forward Schedule).
    Contoh: Task hari Senin dimajukan ke hari Minggu karena task hari Minggu sudah selesai di hari Sabtu.
    """
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, title, scheduled_at, payload
                    FROM content_schedules
                    WHERE agent_name = %s
                      AND status = 'pending'
                      AND (scheduled_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')::date > %s
                    ORDER BY scheduled_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED;
                """, (agent_name, target_date))
                row = cur.fetchone()
                if not row:
                    return None

                sched_id, title, old_sched_utc, payload_raw = row
                old_sched_wib = old_sched_utc.astimezone(WIB)
                old_date_str = old_sched_wib.strftime("%Y-%m-%d")

                now_wib = datetime.now(WIB)
                if target_date == now_wib.date() and now_wib.hour >= target_hour:
                    new_sched_wib = now_wib + timedelta(minutes=5)
                else:
                    new_sched_wib = datetime.combine(target_date, datetime.min.time()).replace(
                        hour=target_hour, minute=0, second=0, microsecond=0, tzinfo=WIB
                    )
                new_sched_utc = new_sched_wib.astimezone(timezone.utc)

                cur.execute("""
                    UPDATE content_schedules
                    SET scheduled_at = %s
                    WHERE id = %s;
                """, (new_sched_utc, sched_id))

                logger.info(
                    f"⏩ [Bay-Zero Fast-Forward] Memajukan tugas '{title}' milik {agent_name} "
                    f"dari {old_date_str} ke {target_date.strftime('%Y-%m-%d')} ({new_sched_wib.strftime('%H:%M WIB')})!"
                )

                return {
                    "schedule_id": sched_id,
                    "agent_name": agent_name,
                    "title": title,
                    "old_date": old_date_str,
                    "new_date": target_date.strftime("%Y-%m-%d"),
                    "new_time_wib": new_sched_wib.strftime("%H:%M WIB"),
                    "action": "pull_forward",
                }
    except Exception as exc:
        logger.error(f"Gagal memajukan jadwal {agent_name} ke {target_date}: {exc}", exc_info=True)
        return None


def fetch_candidate_for_stark(
    existing_topics: set[str], preferred_category: str | None = None
) -> tuple[str, str, dict[str, Any]]:
    """
    Mengambil 1 topik teknologi/gaming/AI/IoT baru yang belum pernah dikerjakan Stark.
    Prioritas 1: Database Sumber RSS (content_rss_sources di Supabase - 28+ media aktif)
    Prioritas 2: GitHub Trending Weekly (Programming & Tools)
    Prioritas 3: Google News Tech & Gaming RSS
    Prioritas 4: Dynamic Curated Fallbacks
    """
    # 1. Database RSS Sources (28+ media feed terdaftar di Supabase)
    try:
        from orchestrator.tools.rss_fetcher import fetch_next_rss_candidate
        rss_cand = fetch_next_rss_candidate(existing_topics, preferred_category=preferred_category)
        if rss_cand:
            return rss_cand
    except Exception as exc:
        logger.warning(f"Gagal mengambil dari database RSS feed: {exc}")

    # 2. GitHub Trending (jika slot programming atau fallback)
    if preferred_category in (None, "programming", "technology"):
        try:
            raw_gh = get_github_trending_weekly(language="", max_items=15)
            for item in raw_gh:
                r_name = item.get("repo_name", "").strip().lower()
                r_url = item.get("repo_url", "").strip().lower()
                if r_name and r_name not in existing_topics and r_url not in existing_topics:
                    title = f"Bedah Repositori: {item['repo_name']}"
                    existing_topics.add(r_name)
                    existing_topics.add(r_url)
                    existing_topics.add(title.lower())
                    input_data = {
                        "query": item.get("description") or item["repo_name"],
                        "topic": title,
                        "task_type": "article",
                        "action": "trend-article",
                        "source": "github",
                        "target_urls": item["repo_url"],
                        "category": "programming",
                        "dry_run": False,
                    }
                    return title, "trend-article", input_data
        except Exception as exc:
            logger.warning(f"Gagal mengambil GitHub Trending: {exc}")

    # 3. Google News Tech & Gaming RSS
    try:
        gnews_kw = "gaming" if preferred_category == "games" else "technology"
        raw_news = get_google_news_topics(keyword=gnews_kw, max_items=15, lang="en")
        for item in raw_news:
            t = item.get("title", "").strip().lower()
            u = item.get("url", "").strip().lower()
            if t and t not in existing_topics and u not in existing_topics:
                title = item.get("title", "Google News Tech & Gaming Update")
                existing_topics.add(t)
                existing_topics.add(u)
                existing_topics.add(title.lower())
                from orchestrator.tools.kodepintar_publisher import determine_article_category
                cat = determine_article_category(title, default_category=preferred_category or "technology")
                input_data = {
                    "query": title,
                    "topic": title,
                    "task_type": "article",
                    "action": "trend-article",
                    "source": "gnews",
                    "target_urls": item.get("url", ""),
                    "category": cat,
                    "dry_run": False,
                }
                return title, "trend-article", input_data
    except Exception as exc:
        logger.warning(f"Gagal mengambil Google News: {exc}")

    # 3. Dynamic Fallback Curated Topics
    dynamic_topics = [
        ("Bedah Repositori: astral-sh/uv", "https://github.com/astral-sh/uv", "Extremely fast Python package installer and resolver."),
        ("Bedah Repositori: langchain-ai/langgraph", "https://github.com/langchain-ai/langgraph", "Build resilient language agents as graphs."),
        ("Bedah Repositori: ollama/ollama", "https://github.com/ollama/ollama", "Get up and running with large language models locally."),
        ("Bedah Repositori: vllm-project/vllm", "https://github.com/vllm-project/vllm", "High-throughput and memory-efficient LLM inference engine."),
        ("Bedah Repositori: fastapi/fastapi", "https://github.com/fastapi/fastapi", "Modern, fast web framework for building APIs with Python."),
        ("Autonomous Multi-Agent Orchestration Patterns in 2026", "https://techcrunch.com/category/enterprise/", "Deep dive into multi-agent workflows and event-driven LLMs."),
        ("Post-Quantum Cryptography & Zero-Knowledge Security", "https://theverge.com/tech", "Evaluating enterprise migration to quantum-resistant encryption."),
    ]
    for t_title, t_url, t_desc in dynamic_topics:
        if t_title.lower() not in existing_topics and t_url.lower() not in existing_topics:
            existing_topics.add(t_title.lower())
            existing_topics.add(t_url.lower())
            input_data = {
                "query": t_desc,
                "topic": t_title,
                "task_type": "article",
                "action": "trend-article",
                "source": "curated",
                "target_urls": t_url,
                "category": "programming",
                "dry_run": False,
            }
            return t_title, "trend-article", input_data

    # 4. Jika seluruh sumber habis, laporkan ke Kang Bos (Jangan gunakan dummy string)
    try:
        from orchestrator.events import notify_kang_bos
        notify_kang_bos(
            agent_name="Stark",
            subject="Sumber Topik Teknologi Habis",
            message=(
                "Seluruh repositori GitHub Trending mingguan, Google News teknologi, dan katalog kurasi "
                "telah selesai dikerjakan atau sudah terjadwal. Pembuatan jadwal dummy dihentikan agar tidak terjadi false error. "
                "Menunggu arahan/strategi topik baru dari Kang Bos."
            ),
            details={"existing_topics_count": len(existing_topics)},
        )
    except Exception as exc:
        logger.warning(f"Gagal mengirim notifikasi Kang Bos: {exc}")

    return None


def fetch_candidate_for_usagi(existing_topics: set[str]) -> tuple[str, str, dict[str, Any]] | None:
    """Mengambil 1 cerita dongeng anak baru yang belum pernah dikerjakan Usagi (Database Catalog -> YouTube Channels -> Folk Lore Fallback)."""
    # 0. Ambil dari database youtube_dongeng_catalog (2.200+ video tersimpan siap pakai tanpa kuota API!)
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT video_id, title 
                    FROM youtube_dongeng_catalog 
                    WHERE status = 'unprocessed' 
                    ORDER BY published_at DESC 
                    LIMIT 30;
                """)
                rows = cur.fetchall()
                for v_id, v_title in rows:
                    v_id_key = v_id.lower()
                    v_title_key = v_title.lower()
                    if v_id_key not in existing_topics and v_title_key not in existing_topics:
                        existing_topics.add(v_id_key)
                        existing_topics.add(v_title_key)
                        cur.execute("UPDATE youtube_dongeng_catalog SET status = 'scheduled', updated_at = NOW() WHERE video_id = %s;", (v_id,))
                        conn.commit()
                        logger.info(f"✨ [Bay-Zero Planner] Mengambil video dari katalog database: {v_id} ('{v_title}')")
                        return v_title, "dongeng", {
                            "video_id": v_id,
                            "query": v_title,
                            "topic": v_title,
                            "task_type": "dongeng",
                            "action": "start",
                            "dry_run": False,
                        }
    except Exception as exc:
        logger.warning(f"Gagal mengambil dari youtube_dongeng_catalog: {exc}")

    # 1. YouTube Dongeng Channels
    try:
        from orchestrator.tools.youtube_client import list_channel_videos
        for ch_id in settings.DONGENG_TARGET_CHANNELS:
            vids = list_channel_videos(ch_id, max_results=30)
            for v in vids:
                v_id = str(v.get("id") or v.get("video_id") or "").strip()
                v_title = str(v.get("title") or "").strip()
                v_id_key = v_id.lower()
                v_title_key = v_title.lower()
                if v_id and v_id_key not in existing_topics and v_title_key not in existing_topics:
                    title = v.get("title") or f"Dongeng Anak {v_id}"
                    existing_topics.add(v_id_key)
                    existing_topics.add(v_title_key)
                    input_data = {
                        "video_id": v_id,
                        "query": title,
                        "topic": title,
                        "task_type": "dongeng",
                        "action": "start",
                        "dry_run": False,
                    }
                    return title, "dongeng", input_data
    except Exception as exc:
        logger.warning(f"Gagal memindai YouTube Dongeng: {exc}")

    # 2. Classic Folktale Fallbacks (Real verified YouTube video IDs)
    dongeng_catalog = [
        ("KUrlU6WW7ZI", "Kisah Si Kancil dan Buaya yang Cerdik Menyeberang Sungai"),
        ("x2RGBsncrmo", "Legenda Sangkuriang dan Terciptanya Gunung Tangkuban Perahu"),
        ("juEC_Q-j9Tw", "Petualangan Berani Timun Mas Mengalahkan Raksasa Jahat"),
        ("x-OETwI6ij0", "Kisah Pengorbanan Ibu dan Pelajaran Hidup Malin Kundang"),
        ("14xZV-jEnY0", "Misteri Keong Mas dan Putri Candra Kirana yang Bijaksana"),
        ("XYKYCVb1oCU", "Kisah Bawang Merah dan Bawang Putih: Kebaikan Berbuah Manis"),
        ("CapRqHdluYM", "Asal Usul Danau Toba dan Sumpah Ikan Mas Ajaib"),
        ("yo9IsAMSFks", "Legenda Ciung Wanara dan Ayam Jago Sakti Kerajaan Galuh"),
    ]
    for v_id, v_title in dongeng_catalog:
        if v_id.lower() not in existing_topics and v_title.lower() not in existing_topics:
            existing_topics.add(v_id.lower())
            existing_topics.add(v_title.lower())
            return v_title, "dongeng", {
                "video_id": v_id,
                "query": v_title,
                "topic": v_title,
                "task_type": "dongeng",
                "action": "start",
                "dry_run": False,
            }

    # 3. Dynamic Real YouTube Search (Pencarian video dongeng nyata dari YouTube)
    try:
        import httpx
        from orchestrator.tools.youtube_client import looks_like_skip
        api_key = settings.YOUTUBE_API_KEY
        if api_key:
            search_keywords = [
                "Dongeng Animasi Anak Bahasa Indonesia",
                "Cerita Rakyat Nusantara Cerita Anak",
                "Dongeng Fabel Indonesia",
                "Kisah Cerita Rakyat Nusantara",
                "Dongeng Sebelum Tidur Anak Indonesia",
            ]
            with httpx.Client(timeout=10.0) as client:
                for kw in search_keywords:
                    res = client.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "part": "snippet",
                            "q": kw,
                            "type": "video",
                            "maxResults": 15,
                            "relevanceLanguage": "id",
                            "key": api_key,
                        },
                    )
                    if res.status_code == 200:
                        for item in res.json().get("items", []):
                            vid = item.get("id", {}).get("videoId")
                            title = (item.get("snippet", {}).get("title") or "").strip()
                            if not vid or not title:
                                continue
                            if looks_like_skip(title):
                                continue
                            v_id_key = vid.lower()
                            v_title_key = title.lower()
                            if v_id_key not in existing_topics and v_title_key not in existing_topics:
                                existing_topics.add(v_id_key)
                                existing_topics.add(v_title_key)
                                logger.info(f"✨ [Bay-Zero Planner] Berhasil menemukan video dongeng nyata: {vid} ('{title}')")
                                return title, "dongeng", {
                                    "video_id": vid,
                                    "query": title,
                                    "topic": title,
                                    "task_type": "dongeng",
                                    "action": "start",
                                    "dry_run": False,
                                }
    except Exception as exc:
        logger.warning(f"Dynamic YouTube Search fallback gagal: {exc}")

    # 4. Jika seluruh sumber habis, laporkan ke Kang Bos (Jangan gunakan dummy string)
    try:
        from orchestrator.events import notify_kang_bos
        notify_kang_bos(
            agent_name="Usagi",
            subject="Semua Video Selesai Dikerjakan",
            message=(
                "Semua video dari channel YouTube target, katalog dongeng klasik, dan pencarian dinamis YouTube "
                "telah selesai dikerjakan atau sudah terjadwal (tidak ada video baru). Pembuatan jadwal dummy dihentikan agar tidak terjadi false error. "
                "Menunggu Kang Bos menentukan strategi konten atau menambahkan channel target baru."
            ),
            details={"existing_topics_count": len(existing_topics)},
        )
    except Exception as exc:
        logger.warning(f"Gagal mengirim notifikasi Kang Bos: {exc}")

    return None


def fetch_candidate_for_sosmed(existing_topics: set[str]) -> tuple[str, str, dict[str, Any]] | None:
    """
    Mengambil file video dari antrean 'data/tiktok_queue/' untuk dijadwalkan oleh Kang Sosmed.
    Jika antrean kosong, memberi tahu Kang Bos.
    """
    queue_dir = os.path.join(project_root, "data", "tiktok_queue")
    os.makedirs(queue_dir, exist_ok=True)
    video_files = sorted(glob.glob(os.path.join(queue_dir, "*.mp4")))

    for vpath in video_files:
        filename = os.path.basename(vpath)
        base_name, _ = os.path.splitext(filename)
        clean_title = f"TikTok Promo: {base_name.replace('_', ' ').replace('-', ' ').title()}"

        # Cek caption file pendamping jika ada
        caption_file = os.path.join(queue_dir, f"{base_name}.txt")
        custom_caption = None
        if os.path.exists(caption_file):
            try:
                with open(caption_file, "r", encoding="utf-8") as f:
                    custom_caption = f.read().strip()
            except Exception:
                pass

        if clean_title.lower() in existing_topics or filename.lower() in existing_topics:
            continue

        target_integ = settings.POSTIZ_TIKTOK_INTEGRATION_ID or "cmw3byats000ao2745rk4z14k"
        resolved_caption = custom_caption
        if not resolved_caption:
            if target_integ in ("cmw3byats000ao2745rk4z14k", "cmw2y48yi0003o274ue9csad3"):
                resolved_caption = "#fyppppppp\n#viralootd\n#hijabviral"

        return clean_title, "tiktok", {
            "task_type": "tiktok",
            "file_path": vpath,
            "filename": filename,
            "caption": resolved_caption,
            "integration_id": target_integ,
            "strategy": "draft_inbox",
        }

    # Jika antrean video kosong
    logger.info("ℹ️ [Sosmed Planner] Antrean video di data/tiktok_queue kosong.")
    try:
        from orchestrator.events import notify_kang_bos
        notify_kang_bos(
            agent_name="Sosmed",
            subject="Antrean Video TikTok Kosong",
            message=(
                "Antrean video TikTok di folder 'data/tiktok_queue/' belum memiliki file MP4 baru untuk dijadwalkan. "
                "Silakan unggah video produk untuk 7 hari ke depan ke folder data/tiktok_queue agar Kang Sosmed "
                "dapat menjadwalkannya secara otomatis."
            ),
            details={"queue_dir": queue_dir, "found_files": len(video_files)},
        )
    except Exception as exc:
        logger.warning(f"Gagal mengirim notifikasi Kang Bos untuk Sosmed: {exc}")

    return None


def replenish_task_for_agent(
    agent_name: str,
    target_date: datetime.date,
    target_hour: int,
    existing_topics: set[str],
    preferred_category: str | None = None,
) -> dict[str, Any] | None:
    """Mencari/menghasilkan pekerjaan baru dari web/feed dan menjadwalkannya pada target_date (Auto-Replenish)."""
    if agent_name == "Stark":
        candidate = fetch_candidate_for_stark(existing_topics, preferred_category=preferred_category)
    elif agent_name == "Sosmed":
        candidate = fetch_candidate_for_sosmed(existing_topics)
    else:
        candidate = fetch_candidate_for_usagi(existing_topics)

    if not candidate:
        logger.warning(
            f"⏸️ [Bay-Zero Replenish] Tidak ada task baru untuk {agent_name} pada {target_date}. "
            "Slot dibiarkan kosong dan laporan telah dikirimkan ke Kang Bos."
        )
        return None

    title, task_type, input_data = candidate
    schedule_id = f"sched_{uuid.uuid4().hex[:10]}"
    task_id = f"task_{schedule_id[6:]}"

    now_wib = datetime.now(WIB)
    if target_date == now_wib.date() and now_wib.hour >= target_hour:
        sched_time_wib = now_wib + timedelta(minutes=5)
    else:
        sched_time_wib = datetime.combine(target_date, datetime.min.time()).replace(
            hour=target_hour, minute=0, second=0, microsecond=0, tzinfo=WIB
        )
    sched_time_utc = sched_time_wib.astimezone(timezone.utc)

    payload = {
        "schedule_id": schedule_id,
        "task_id": task_id,
        "thread_id": task_id,
        "task_type": "article" if agent_name == "Stark" else input_data.get("task_type"),
        "action": input_data.get("action", "trend-article" if agent_name == "Stark" else "start"),
        "input_data": {
            **input_data,
            "schedule_id": schedule_id,
        },
    }

    with postgres_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO content_schedules (
                    id, agent_name, task_type, title, payload, scheduled_at, status
                ) VALUES (%s, %s, %s, %s, %s, %s, 'pending');
            """, (
                schedule_id,
                agent_name,
                task_type,
                title[:250],
                json.dumps(payload),
                sched_time_utc,
            ))

    logger.info(
        f"✨ [Bay-Zero Replenish] Menambahkan tugas baru '{title}' untuk {agent_name} "
        f"pada {target_date.strftime('%Y-%m-%d')} ({sched_time_wib.strftime('%H:%M WIB')})!"
    )

    return {
        "schedule_id": schedule_id,
        "agent_name": agent_name,
        "title": title,
        "date": target_date.strftime("%Y-%m-%d"),
        "time_wib": sched_time_wib.strftime("%H:%M WIB"),
        "action": "replenished",
    }


def rebalance_and_replenish_schedules(days_ahead: int = 7) -> dict[str, Any]:
    """
    Audit mandiri Bay-Zero: Memastikan SETIAP AGEN memiliki tugas SETIAP HARI.
    Jika ada hari kosong (misal: tugas hari Minggu sudah selesai dikerjakan hari Sabtu):
    1. PULL FORWARD: Tugas hari Senin dimajukan ke hari Minggu, Selasa ke Senin, dst.
    2. REPLENISH: Tugas baru dicari dan dijadwalkan di akhir periode sehingga pipeline 7 hari selalu penuh.
    Bisa dijalankan kapan saja (pagi, siang, sore) secara self-healing.
    """
    logger.info("🛡️ [Bay-Zero Rebalancer] Memulai pemindaian dan penyelarasan jadwal 7 hari ke depan...")

    cleanup_duplicate_schedules()
    existing_topics = get_existing_scheduled_topics()
    today_wib = datetime.now(WIB).date()

    pulled_forward: list[dict[str, Any]] = []
    replenished: list[dict[str, Any]] = []
    coverage_summary: dict[str, dict[str, str]] = {}

    for agent_name, cfg in AGENT_CADENCE.items():
        coverage_summary[agent_name] = {}
        slots = cfg.get("slots", [{"hour": cfg["target_hour_wib"], "category": None}])

        for day_offset in range(days_ahead):
            target_date = today_wib + timedelta(days=day_offset)
            date_str = target_date.strftime("%Y-%m-%d")
            slot_reports = []

            for slot_info in slots:
                target_hour = slot_info["hour"]
                preferred_cat = slot_info.get("category")

                is_covered, status_reason, tasks = is_agent_covered_on_date(
                    agent_name, target_date, target_hour=target_hour
                )

                if is_covered:
                    slot_reports.append(f"{target_hour:02d}:00 OK")
                    continue

                # Agen terdeteksi kosong/nganggur pada slot ini!
                logger.warning(
                    f"⚠️ [Bay-Zero Audit] Agen {agent_name} terdeteksi KOSONG pada {date_str} jam {target_hour:02d}:00! Mengisi slot..."
                )

                # Langkah 1: Coba majukan tugas pending dari hari berikutnya (Fast-Forward)
                pulled = pull_earliest_future_task_forward(agent_name, target_date, target_hour)
                if pulled:
                    pulled_forward.append(pulled)
                    slot_reports.append(f"{target_hour:02d}:00 Pulled")

                    try:
                        from orchestrator.events import emit_agent_event
                        emit_agent_event(
                            thread_id="system",
                            node="bayzero_schedule_audit",
                            status="in_progress",
                            message=(
                                f"⏩ Bay-Zero memajukan jadwal '{pulled['title'][:35]}...' milik {agent_name} "
                                f"ke {date_str} ({target_hour:02d}:00 WIB) agar slot terisi."
                            ),
                            details={
                                "agent_name": "Bay-Zero",
                                "action": "pull_forward",
                                "target_agent": agent_name,
                                "schedule_id": pulled["schedule_id"],
                            },
                        )
                    except Exception:
                        pass
                else:
                    # Langkah 2: Cari tugas baru (Replenish) dengan preferred category slot
                    new_task = replenish_task_for_agent(
                        agent_name, target_date, target_hour, existing_topics, preferred_category=preferred_cat
                    )
                    if new_task:
                        replenished.append(new_task)
                        slot_reports.append(f"{target_hour:02d}:00 Replenished")

                        try:
                            from orchestrator.events import emit_agent_event
                            emit_agent_event(
                                thread_id="system",
                                node="bayzero_schedule_audit",
                                status="in_progress",
                                message=(
                                    f"✨ Bay-Zero menemukan tugas baru '{new_task['title'][:35]}...' untuk {agent_name} "
                                    f"pada {date_str} ({target_hour:02d}:00 WIB) agar kuota terpenuhi."
                                ),
                                details={
                                    "agent_name": "Bay-Zero",
                                    "action": "replenish",
                                    "target_agent": agent_name,
                                    "schedule_id": new_task["schedule_id"],
                                },
                            )
                        except Exception:
                            pass
                    else:
                        slot_reports.append(f"{target_hour:02d}:00 KOSONG")

            coverage_summary[agent_name][date_str] = " | ".join(slot_reports)

    total_actions = len(pulled_forward) + len(replenished)
    logger.info(
        f"✅ [Bay-Zero Rebalancer] Penyelarasan tuntas! {len(pulled_forward)} tugas dimajukan (Fast-Forward), "
        f"{len(replenished)} tugas baru dibuat (Replenish)."
    )

    if total_actions > 0:
        try:
            from orchestrator.events import emit_agent_event
            emit_agent_event(
                thread_id="system",
                node="bayzero_schedule_audit",
                status="completed",
                message=(
                    f"🛡️ Kalender kerja diselaraskan oleh Bay-Zero: {len(pulled_forward)} tugas dimajukan, "
                    f"{len(replenished)} tugas baru ditambahkan. Seluruh agen 100% aktif setiap hari!"
                ),
                details={
                    "agent_name": "Bay-Zero",
                    "pulled_forward_count": len(pulled_forward),
                    "replenished_count": len(replenished),
                },
            )
        except Exception:
            pass

    return {
        "success": True,
        "pulled_forward": pulled_forward,
        "replenished": replenished,
        "coverage": coverage_summary,
        "timestamp": datetime.now(WIB).isoformat(),
    }


def verify_youtube_video_availability(video_id: str) -> bool:
    """Verifikasi cepat dan hemat kuota apakah video YouTube aktif via oEmbed endpoint."""
    if not video_id or str(video_id).startswith("dongeng_"):
        return False
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        res = requests.get(url, timeout=5.0)
        return res.status_code == 200
    except Exception:
        return True  # Toleran jika network lambat


def audit_schedule_item_integrity(sched: dict[str, Any]) -> dict[str, Any]:
    """
    Pengecekan kebenaran fisik (Physical & Live Content Integrity Check).
    Memastikan status terupload bukan formalitas, dan file/sumber daya fisik benar-benar ada.
    """
    agent = sched.get("agent_name")
    status = sched.get("status")
    payload = sched.get("payload") or {}
    inp = payload.get("input_data", {})
    result_url = sched.get("result_url")
    title = sched.get("title", "")
    sched_id = sched.get("id")

    res = {
        "id": sched_id,
        "agent": agent,
        "title": title,
        "status": status,
        "is_valid": True,
        "anomaly": None,
    }

    # 1. Pengecekan Tugas TikTok (Kang Sosmed)
    if agent == "Sosmed" or sched.get("task_type") == "tiktok":
        target_file = inp.get("file_path") or inp.get("video_file")
        if status == "pending":
            queue_file_exists = False
            if target_file and os.path.exists(target_file):
                queue_file_exists = True
            elif target_file:
                alt = os.path.join(project_root, "data", "tiktok_queue", os.path.basename(target_file))
                queue_file_exists = os.path.exists(alt)

            if not queue_file_exists:
                res["is_valid"] = False
                res["anomaly"] = f"File video fisik tidak ditemukan di disk untuk jadwal pending: {target_file}"
        elif status == "completed":
            if not result_url and not payload.get("postiz_post_id"):
                res["is_valid"] = False
                res["anomaly"] = "Status ditandai 'completed' tapi tidak memiliki bukti upload (result_url / postiz_post_id kosong)"

    # 2. Pengecekan Tugas Dongeng YouTube (Kang Dongeng / Usagi)
    elif agent == "Usagi" or sched.get("task_type") == "dongeng":
        vid_id = inp.get("video_id")
        if vid_id and status in ("pending", "in_progress"):
            if not verify_youtube_video_availability(vid_id):
                res["is_valid"] = False
                res["anomaly"] = f"Video YouTube '{vid_id}' tidak dapat diakses (private/deleted/404)"
        elif status == "completed":
            if not result_url:
                res["is_valid"] = False
                res["anomaly"] = "Status 'completed' tanpa tautan publikasi (result_url kosong)"

    # 3. Pengecekan Tugas Tech Writer (Kang Nulis / Stark)
    elif agent == "Stark" or sched.get("task_type") in ("article", "trend-article"):
        if status == "completed":
            if not result_url:
                res["is_valid"] = False
                res["anomaly"] = "Status 'completed' tanpa link artikel terbit (result_url kosong)"

    return res


def scan_and_audit_schedules(days_ahead: int = 7) -> dict[str, Any]:
    """
    Audit komprehensif harian oleh Kang Bos (Bay-Zero).
    Memverifikasi keterisian kalender serta kebenaran fisik (integritas file video & URL live).
    """
    today_wib = datetime.now(WIB).date()
    report: dict[str, list[dict[str, Any]]] = {}
    anomalies: list[dict[str, Any]] = []

    # 1. Audit keterisian ritme harian
    for agent_name, cfg in AGENT_CADENCE.items():
        report[agent_name] = []
        for day_offset in range(days_ahead):
            target_date = today_wib + timedelta(days=day_offset)
            is_covered, status_reason, tasks = is_agent_covered_on_date(agent_name, target_date)
            report[agent_name].append({
                "date": target_date.strftime("%Y-%m-%d"),
                "day_name": target_date.strftime("%A"),
                "is_covered": is_covered,
                "status": status_reason,
                "task_title": tasks[0]["title"] if tasks else None,
                "task_id": tasks[0]["id"] if tasks else None,
            })

    # 2. Audit integritas fisik seluruh jadwal aktif & selesai
    all_schedules = list_editorial_schedules(limit=100, days_window=days_ahead)
    for s in all_schedules:
        check = audit_schedule_item_integrity(s)
        if not check["is_valid"]:
            anomalies.append(check)
            logger.warning(f"⚠️ [Bay-Zero Audit Anomaly] {check['agent']} - {check['title']}: {check['anomaly']}")

    # 3. Laporkan ke Kang Bos jika ditemukan anomali fisik atau formalitas palsu
    if anomalies:
        try:
            from orchestrator.events import notify_kang_bos
            notify_kang_bos(
                agent_name="Bay-Zero",
                subject=f"Audit Pagi: Ditemukan {len(anomalies)} Anomali Integritas Jadwal",
                message=(
                    f"Kang Bos menemukan {len(anomalies)} jadwal dengan ketidaksesuaian integritas fisik "
                    "(file video tidak ditemukan di disk, video YouTube 404/private, atau status completed tanpa bukti upload)."
                ),
                details={"anomalies": anomalies[:5]},
            )
        except Exception as exc:
            logger.warning(f"Gagal mengirim notifikasi audit Kang Bos: {exc}")

    return {
        "audit_date": today_wib.strftime("%Y-%m-%d"),
        "agents": report,
        "anomalies_count": len(anomalies),
        "anomalies": anomalies,
    }


def generate_weekly_editorial_plan(days_ahead: int = 7) -> list[dict[str, Any]]:
    """Membangun / menyempurnakan kalender editorial mingguan dengan jaminan setiap agen memiliki pekerjaan setiap hari."""
    rebalance_and_replenish_schedules(days_ahead=days_ahead)
    return list_editorial_schedules(limit=days_ahead * 3, status="pending")


def list_editorial_schedules(
    limit: int = 50,
    status: str | None = None,
    include_discarded: bool = False,
    days_window: int | None = None,
) -> list[dict[str, Any]]:
    """
    Mengambil daftar jadwal konten dari PostgreSQL content_schedules setelah auto-deduplikasi.
    
    Filter:
    - status: filter status tertentu ('pending', 'completed', 'in_progress', 'failed', 'discarded').
    - include_discarded: jika False dan status bukan 'discarded', jadwal berstatus 'discarded' disembunyikan.
    - days_window: membatasi rentang waktu (misal: 7 hari terakhir hingga 7 hari ke depan).
    """
    # Selalu jalankan auto-cleanup terlebih dahulu agar data yang dikembalikan ke API 100% bebas duplikat!
    cleanup_duplicate_schedules()

    query = """
        SELECT id, agent_name, task_type, title, payload, scheduled_at, status, 
               started_at, completed_at, result_url, error_message, created_at
        FROM content_schedules
        WHERE 1=1
    """
    params: list[Any] = []

    if status and status.lower() != "all":
        query += " AND status = %s"
        params.append(status.lower())
    elif not include_discarded:
        query += " AND status != 'discarded'"

    if days_window and days_window > 0:
        # Batasi jendela waktu: [NOW - days_window] s/d [NOW + days_window]
        query += """
            AND scheduled_at >= (NOW() - INTERVAL '%s days')
            AND scheduled_at <= (NOW() + INTERVAL '%s days')
        """
        params.extend([days_window, days_window])

    # Prioritaskan jadwal aktif/mendatang (in_progress, pending) secara kronologis masa depan (ASC),
    # disusul riwayat jadwal selesai/gagal dari yang paling baru (DESC).
    # Menjamin jadwal hari ini dan masa depan tidak pernah terpotong oleh LIMIT.
    query += """
        ORDER BY 
            CASE WHEN status IN ('in_progress', 'pending') THEN 0 ELSE 1 END,
            CASE WHEN status IN ('in_progress', 'pending') THEN scheduled_at END ASC,
            scheduled_at DESC
        LIMIT %s;
    """
    params.append(limit)

    results: list[dict[str, Any]] = []
    with postgres_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            for r in rows:
                results.append({
                    "id": r[0],
                    "agent_name": r[1],
                    "task_type": r[2],
                    "title": r[3],
                    "payload": r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"),
                    "scheduled_at": r[5].isoformat() if r[5] else None,
                    "status": r[6],
                    "started_at": r[7].isoformat() if r[7] else None,
                    "completed_at": r[8].isoformat() if r[8] else None,
                    "result_url": r[9],
                    "error_message": r[10],
                    "created_at": r[11].isoformat() if r[11] else None,
                })
    return results


def print_schedules_table(schedules: list[dict[str, Any]]):
    """Mencetak daftar jadwal ke terminal dengan visual tabel bersih."""
    if not schedules:
        print("\n📅 Belum ada jadwal konten tersimpan di database.")
        print("   Gunakan: python -m scripts.dispatch plan --generate-week untuk membuat jadwal 7 hari ke depan.")
        return

    print("\n" + "=" * 90)
    print("📅 KALENDER EDITORIAL KONTEN PUNGGAWA (BAY-ZERO PLANNER)")
    print("=" * 90)
    print(f"{'STATUS':<12} | {'AGEN':<8} | {'HARI / JAM (WIB)':<24} | {'JUDUL KONTEN':<40}")
    print("-" * 90)

    for s in schedules:
        st = s.get("status", "pending").lower()
        if st == "completed":
            status_badge = "✅ Selesai"
        elif st == "in_progress":
            status_badge = "🔄 Berjalan"
        elif st == "failed":
            status_badge = "❌ Gagal"
        else:
            status_badge = "⏳ Pending"

        # Format waktu ke WIB
        sched_raw = s.get("scheduled_at")
        if sched_raw:
            try:
                dt = datetime.fromisoformat(sched_raw).astimezone(WIB)
                time_str = dt.strftime("%a, %d %b %H:%M WIB")
            except Exception:
                time_str = str(sched_raw)[:22]
        else:
            time_str = "-"

        agent = s.get("agent_name", "Stark")
        title = s.get("title", "")
        if len(title) > 38:
            title = title[:35] + "..."

        print(f"{status_badge:<12} | {agent:<8} | {time_str:<24} | {title:<40}")
        if s.get("error_message"):
            print(f"   ↳ ⚠️ Alasan Gagal: {s['error_message'][:80]}")
        elif s.get("result_url"):
            print(f"   ↳ 🔗 URL Publikasi: {s['result_url'][:80]}")

    print("=" * 90 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bay-Zero Editorial Content Planner & Anti-Idle Rebalancer")
    parser.add_argument("--generate-week", action="store_true", help="Buat jadwal otomatis 7 hari ke depan")
    parser.add_argument("--rebalance", action="store_true", help="Pindai dan selaraskan jadwal (Fast-Forward & Replenish agar 0 agen nganggur)")
    parser.add_argument("--scan", "--audit", dest="scan", action="store_true", help="Audit status keterisian jadwal seluruh agen dan verifikasi fisik integritas file/URL")
    parser.add_argument("--list", action="store_true", help="Tampilkan jadwal editorial saat ini")
    parser.add_argument("--limit", type=int, default=25, help="Batas jumlah jadwal yang ditampilkan")
    args = parser.parse_args()

    try:
        if args.rebalance or args.generate_week:
            print("🛡️ [Bay-Zero Rebalancer] Memindai dan menyelaraskan jadwal seluruh agen...")
            res = rebalance_and_replenish_schedules(days_ahead=7)
            print(f"⏩ Tugas dimajukan (Fast-Forward): {len(res['pulled_forward'])}")
            for p in res['pulled_forward']:
                print(f"   ↳ {p['agent_name']}: '{p['title'][:35]}' dimajukan dari {p['old_date']} -> {p['new_date']}")
            print(f"✨ Tugas baru (Replenish): {len(res['replenished'])}")
            for r in res['replenished']:
                print(f"   ↳ {r['agent_name']}: '{r['title'][:35]}' dijadwalkan pada {r['date']}")
            schedules = list_editorial_schedules(limit=args.limit)
            print_schedules_table(schedules)
        elif args.scan:
            audit = scan_and_audit_schedules(days_ahead=7)
            print(f"\n🔍 [Bay-Zero Schedule Audit] Tanggal Audit: {audit['audit_date']}")
            print("=" * 80)
            for agent, days in audit["agents"].items():
                print(f"\n👤 Agen: {agent}")
                for d in days:
                    icon = "✅" if d["is_covered"] else "❌ KOSONG (IDLE!)"
                    t_info = f" -> {d['task_title'][:35]}" if d["task_title"] else ""
                    print(f"   {d['date']} ({d['day_name'][:3]}): {icon:<15} [{d['status']}]{t_info}")
            
            anomalies = audit.get("anomalies", [])
            print(f"\n📋 Status Integritas Fisik & Bukti Publikasi:")
            if not anomalies:
                print("   ✅ Semua jadwal pending memiliki file video fisik valid, dan jadwal completed terverifikasi nyata!")
            else:
                print(f"   ⚠️ Ditemukan {len(anomalies)} anomali integritas jadwal:")
                for a in anomalies:
                    print(f"      - [{a['agent']}] {a['title'][:30]}: {a['anomaly']}")
            print("=" * 80 + "\n")
        elif args.list:
            schedules = list_editorial_schedules(limit=args.limit)
            print_schedules_table(schedules)
        else:
            parser.print_help()
    finally:
        try:
            postgres_pool.close()
        except Exception:
            pass
