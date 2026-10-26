"""
Planner Bay-Zero: Autonomous Content Scheduling & Editorial Calendar.
Mengatur ritme penerbitan konten Stark & Usagi secara otomatis selama 7 hari ke depan,
menghindari penumpukan artikel dalam 1 hari, dan mencatat rencana ke PostgreSQL content_schedules.
"""
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

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
        "target_hour_wib": 9,      # 09:00 WIB (Tech / Coding Deep-Dive)
        "task_type": "trend-article",
        "description": "Tech & Programming Article Specialist",
    },
    "Usagi": {
        "name": "Usagi",
        "target_hour_wib": 19,     # 19:00 WIB (Cerita Rakyat & Dongeng Anak)
        "task_type": "dongeng",
        "description": "Children Folktale & Animation Specialist",
    },
}


def get_existing_scheduled_topics() -> set[str]:
    """Mengambil seluruh judul, nama repo, URL, dan video ID yang sudah ada di database."""
    existing: set[str] = set()
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT title, payload FROM content_schedules;")
                for row in cur.fetchall():
                    raw_title = (row[0] or "").strip().lower()
                    if raw_title:
                        existing.add(raw_title)
                        # Ekstrak nama repo jika format "bedah repositori: owner/name"
                        if "bedah repositori:" in raw_title:
                            existing.add(raw_title.replace("bedah repositori:", "").strip())
                    
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


def delete_editorial_schedule(schedule_id: str) -> bool:
    """Menghapus jadwal spesifik dari PostgreSQL content_schedules."""
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM content_schedules WHERE id = %s;", (schedule_id,))
                deleted = cur.rowcount > 0
                if deleted:
                    logger.info(f"🗑️ [Bay-Zero Planner] Jadwal '{schedule_id}' berhasil dihapus.")
                return deleted
    except Exception as exc:
        logger.error(f"Gagal menghapus jadwal {schedule_id}: {exc}", exc_info=True)
        return False


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


def is_agent_covered_on_date(agent_name: str, target_date: datetime.date) -> tuple[bool, str, list[dict]]:
    """
    Memeriksa apakah seorang agen sudah memiliki jadwal atau telah menyelesaikan tugas pada target_date (WIB).
    Aturan:
    - Hari ini (today): covered jika ada task 'completed' hari ini, 'in_progress' hari ini, atau 'pending' dijadwalkan hari ini.
    - Hari depan (future): covered HANYA jika ada task 'pending' atau 'in_progress' yang dijadwalkan pada hari tersebut.
      Task yang sudah 'completed' di masa lalu TIDAK menutupi hari depan (karena sudah selesai duluan, sehingga hari depan menjadi kosong/nganggur!).
    """
    today_wib = datetime.now(WIB).date()
    tasks: list[dict] = []

    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                if target_date == today_wib:
                    cur.execute("""
                        SELECT id, title, status, scheduled_at, completed_at
                        FROM content_schedules
                        WHERE agent_name = %s
                          AND (
                            (status = 'completed' AND (completed_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')::date = %s)
                            OR status = 'in_progress'
                            OR (status = 'pending' AND (scheduled_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')::date = %s)
                          )
                        ORDER BY scheduled_at ASC;
                    """, (agent_name, target_date, target_date))
                else:
                    cur.execute("""
                        SELECT id, title, status, scheduled_at, completed_at
                        FROM content_schedules
                        WHERE agent_name = %s
                          AND status IN ('pending', 'in_progress')
                          AND (scheduled_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')::date = %s
                        ORDER BY scheduled_at ASC;
                    """, (agent_name, target_date))
                
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


def fetch_candidate_for_stark(existing_topics: set[str]) -> tuple[str, str, dict[str, Any]]:
    """Mengambil 1 topik teknologi baru yang belum pernah dikerjakan Stark (GitHub Trending -> Google News -> Fallback)."""
    # 1. GitHub Trending
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

    # 2. Google News Tech RSS
    try:
        raw_news = get_google_news_topics(keyword="technology", max_items=15, lang="en")
        for item in raw_news:
            t = item.get("title", "").strip().lower()
            u = item.get("url", "").strip().lower()
            if t and t not in existing_topics and u not in existing_topics:
                title = item.get("title", "Google News Tech Update")
                existing_topics.add(t)
                existing_topics.add(u)
                existing_topics.add(title.lower())
                from orchestrator.tools.kodepintar_publisher import determine_article_category
                cat = determine_article_category(title)
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

    uid = uuid.uuid4().hex[:6]
    fallback_title = f"Analisis Arsitektur Software Modern: Series #{uid}"
    existing_topics.add(fallback_title.lower())
    return fallback_title, "trend-article", {
        "query": fallback_title,
        "topic": fallback_title,
        "task_type": "article",
        "action": "trend-article",
        "source": "autonomous",
        "category": "technology",
        "dry_run": False,
    }


def fetch_candidate_for_usagi(existing_topics: set[str]) -> tuple[str, str, dict[str, Any]]:
    """Mengambil 1 cerita dongeng anak baru yang belum pernah dikerjakan Usagi (YouTube Channels -> Folk Lore Fallback)."""
    # 1. YouTube Dongeng Channels
    try:
        from orchestrator.tools.youtube_client import list_channel_videos
        for ch_id in settings.DONGENG_TARGET_CHANNELS:
            vids = list_channel_videos(ch_id, max_results=10)
            for v in vids:
                v_id = str(v.get("id") or v.get("video_id") or "").strip().lower()
                v_title = str(v.get("title") or "").strip().lower()
                if v_id and v_id not in existing_topics and v_title not in existing_topics:
                    title = v.get("title") or f"Dongeng Anak {v_id}"
                    existing_topics.add(v_id)
                    existing_topics.add(v_title)
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

    # 2. Classic Folktale Fallbacks
    dongeng_catalog = [
        ("dongeng_kancil_buaya_sungai", "Kisah Si Kancil dan Buaya yang Cerdik Menyeberang Sungai"),
        ("dongeng_sangkuriang_tangkuban", "Legenda Sangkuriang dan Terciptanya Gunung Tangkuban Perahu"),
        ("dongeng_timun_mas_raksasa_ijo", "Petualangan Berani Timun Mas Mengalahkan Raksasa Jahat"),
        ("dongeng_malin_kundang_pantai_air", "Kisah Pengorbanan Ibu dan Pelajaran Hidup Malin Kundang"),
        ("dongeng_keong_mas_candra_kirana", "Misteri Keong Mas dan Putri Candra Kirana yang Bijaksana"),
        ("dongeng_bawang_merah_putih_danau", "Kisah Bawang Merah dan Bawang Putih: Kebaikan Berbuah Manis"),
        ("dongeng_danau_toba_ikan_ajaib", "Asal Usul Danau Toba dan Sumpah Ikan Mas Ajaib"),
        ("dongeng_ciung_wanara_pajajaran", "Legenda Ciung Wanara dan Ayam Jago Sakti Kerajaan Galuh"),
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

    uid = uuid.uuid4().hex[:6]
    f_title = f"Kisah Dongeng Nusantara: Petualangan Sahabat Rimba #{uid}"
    existing_topics.add(f_title.lower())
    return f_title, "dongeng", {
        "video_id": f"dongeng_{uid}",
        "query": f_title,
        "topic": f_title,
        "task_type": "dongeng",
        "action": "start",
        "dry_run": False,
    }


def replenish_task_for_agent(
    agent_name: str, target_date: datetime.date, target_hour: int, existing_topics: set[str]
) -> dict[str, Any]:
    """Mencari/menghasilkan pekerjaan baru dari web/feed dan menjadwalkannya pada target_date (Auto-Replenish)."""
    schedule_id = f"sched_{uuid.uuid4().hex[:10]}"
    task_id = f"task_{schedule_id[6:]}"

    if agent_name == "Stark":
        title, task_type, input_data = fetch_candidate_for_stark(existing_topics)
    else:
        title, task_type, input_data = fetch_candidate_for_usagi(existing_topics)

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
        target_hour = cfg["target_hour_wib"]

        for day_offset in range(days_ahead):
            target_date = today_wib + timedelta(days=day_offset)
            date_str = target_date.strftime("%Y-%m-%d")

            is_covered, status_reason, tasks = is_agent_covered_on_date(agent_name, target_date)

            if is_covered:
                coverage_summary[agent_name][date_str] = f"OK ({tasks[0]['title'][:25]}...)"
                continue

            # Agen terdeteksi kosong/nganggur pada hari ini!
            logger.warning(
                f"⚠️ [Bay-Zero Audit] Agen {agent_name} terdeteksi KOSONG pada {date_str}! Mengisi slot..."
            )

            # Langkah 1: Coba majukan tugas pending dari hari berikutnya (Fast-Forward)
            pulled = pull_earliest_future_task_forward(agent_name, target_date, target_hour)
            if pulled:
                pulled_forward.append(pulled)
                coverage_summary[agent_name][date_str] = f"Pulled from {pulled['old_date']}"

                try:
                    from orchestrator.events import emit_agent_event
                    emit_agent_event(
                        thread_id="system",
                        node="bayzero_schedule_audit",
                        status="in_progress",
                        message=(
                            f"⏩ Bay-Zero memajukan jadwal '{pulled['title'][:35]}...' milik {agent_name} "
                            f"ke {date_str} agar agen tidak menganggur."
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
                # Langkah 2: Jika tidak ada tugas masa depan yang bisa dimajukan, cari tugas baru (Replenish)
                new_task = replenish_task_for_agent(agent_name, target_date, target_hour, existing_topics)
                replenished.append(new_task)
                coverage_summary[agent_name][date_str] = f"Replenished ({new_task['title'][:25]}...)"

                try:
                    from orchestrator.events import emit_agent_event
                    emit_agent_event(
                        thread_id="system",
                        node="bayzero_schedule_audit",
                        status="in_progress",
                        message=(
                            f"✨ Bay-Zero menemukan tugas baru '{new_task['title'][:35]}...' untuk {agent_name} "
                            f"pada {date_str} agar kuota harian terpenuhi."
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


def scan_and_audit_schedules(days_ahead: int = 7) -> dict[str, Any]:
    """Pemeriksaan non-destruktif untuk melihat status keterisian jadwal seluruh agen."""
    today_wib = datetime.now(WIB).date()
    report: dict[str, list[dict[str, Any]]] = {}

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

    return {
        "audit_date": today_wib.strftime("%Y-%m-%d"),
        "agents": report,
    }


def generate_weekly_editorial_plan(days_ahead: int = 7) -> list[dict[str, Any]]:
    """Membangun / menyempurnakan kalender editorial mingguan dengan jaminan setiap agen memiliki pekerjaan setiap hari."""
    rebalance_and_replenish_schedules(days_ahead=days_ahead)
    return list_editorial_schedules(limit=days_ahead * 3, status="pending")


def list_editorial_schedules(limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    """Mengambil daftar jadwal konten dari PostgreSQL content_schedules setelah auto-deduplikasi."""
    # Selalu jalankan auto-cleanup terlebih dahulu agar data yang dikembalikan ke API 100% bebas duplikat!
    cleanup_duplicate_schedules()

    query = """
        SELECT id, agent_name, task_type, title, payload, scheduled_at, status, 
               started_at, completed_at, result_url, error_message, created_at
        FROM content_schedules
    """
    params: list[Any] = []
    if status:
        query += " WHERE status = %s"
        params.append(status)

    query += " ORDER BY scheduled_at ASC LIMIT %s;"
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
    parser.add_argument("--scan", action="store_true", help="Audit status keterisian jadwal seluruh agen hari ini dan 7 hari ke depan")
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
