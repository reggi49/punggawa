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


def cleanup_duplicate_pending_schedules() -> int:
    """
    Menghapus jadwal berstatus 'pending' yang duplikat (judul konten sama),
    hanya menyisakan satu jadwal pending per judul.
    """
    deleted_count = 0
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM content_schedules
                    WHERE id IN (
                        SELECT id
                        FROM (
                            SELECT id,
                                   ROW_NUMBER() OVER (PARTITION BY LOWER(TRIM(title)) ORDER BY scheduled_at ASC) as rnum
                            FROM content_schedules
                            WHERE status = 'pending'
                        ) t
                        WHERE t.rnum > 1
                    );
                """)
                deleted_count = cur.rowcount
                if deleted_count > 0:
                    logger.info(f"🧹 [Bay-Zero Planner] Berhasil membersihkan {deleted_count} jadwal pending yang duplikat.")
    except Exception as exc:
        logger.error(f"Gagal membersihkan jadwal duplikat: {exc}", exc_info=True)
    return deleted_count


def generate_weekly_editorial_plan() -> list[dict[str, Any]]:
    """
    Menghasilkan rencana editorial mingguan pintar tanpa bentrok (Smart Conflict-Free Merging):
    1. Membersihkan duplikat pending yang tidak sengaja terbuat sebelumnya.
    2. Memeriksa tugas yang sudah ada di database agar tidak terjadi duplikasi topik/judul.
    3. Menghindari tabrakan waktu: memeriksa slot jam 09.00 & 19.00 WIB yang sudah terisi jadwal pending.
    4. Menggabungkan jadwal baru ke slot hari berikutnya yang masih kosong secara harmonis.
    """
    logger.info("🧠 [Bay-Zero Planner] Menginisialisasi kurasi cerdas tanpa duplikasi...")

    # Bersihkan duplikat pending lama jika ada
    cleanup_duplicate_pending_schedules()

    existing_topics = get_existing_scheduled_topics()
    occupied_slots = get_occupied_time_slots()
    logger.info(f"Ditemukan {len(existing_topics)} topik terdahulu dan {len(occupied_slots)} slot waktu terisi.")

    # 1. Tarik Kandidat dari GitHub Trending Weekly (Filter duplikat)
    github_items: list[dict[str, Any]] = []
    try:
        raw_gh = get_github_trending_weekly(language="", max_items=10)
        for item in raw_gh:
            r_name = item.get("repo_name", "").strip().lower()
            r_url = item.get("repo_url", "").strip().lower()
            if r_name and r_name not in existing_topics and r_url not in existing_topics:
                github_items.append(item)
        logger.info(f"GitHub Trending: {len(github_items)} kandidat baru yang belum pernah dikerjakan.")
    except Exception as exc:
        logger.warning(f"Gagal mengambil GitHub Trending: {exc}")

    # Fallback repositori jika habis / duplikat semua
    fallback_repos = [
        {"repo_name": "astral-sh/uv", "repo_url": "https://github.com/astral-sh/uv", "description": "Extremely fast Python package installer and resolver."},
        {"repo_name": "langchain-ai/langgraph", "repo_url": "https://github.com/langchain-ai/langgraph", "description": "Build resilient language agents as graphs."},
        {"repo_name": "ollama/ollama", "repo_url": "https://github.com/ollama/ollama", "description": "Get up and running with large language models locally."},
        {"repo_name": "vllm-project/vllm", "repo_url": "https://github.com/vllm-project/vllm", "description": "High-throughput and memory-efficient LLM inference engine."},
        {"repo_name": "fastapi/fastapi", "repo_url": "https://github.com/fastapi/fastapi", "description": "Modern, fast web framework for building APIs with Python."},
    ]
    for fb in fallback_repos:
        if len(github_items) < 2 and fb["repo_name"].lower() not in existing_topics:
            github_items.append(fb)

    # 2. Tarik Kandidat dari Google News RSS International (Filter duplikat)
    gnews_items: list[dict[str, Any]] = []
    try:
        raw_news = get_google_news_topics(keyword="technology", max_items=12, lang="en")
        for item in raw_news:
            t = item.get("title", "").strip().lower()
            u = item.get("url", "").strip().lower()
            if t and t not in existing_topics and u not in existing_topics:
                gnews_items.append(item)
        logger.info(f"Google News RSS: {len(gnews_items)} kandidat baru yang belum pernah dikerjakan.")
    except Exception as exc:
        logger.warning(f"Gagal mengambil Google News: {exc}")

    fallback_news = [
        {"title": "Quantum Computing Milestones and Post-Quantum Cryptography in 2026", "url": "https://techcrunch.com/category/enterprise/", "source": "TechCrunch"},
        {"title": "Open Source AI Weights versus Proprietary Cloud Gateways Benchmark", "url": "https://theverge.com/tech", "source": "The Verge"},
        {"title": "Decentralized Edge Intelligence and Low-Power Microcontroller AI Models", "url": "https://wired.com/category/gear/", "source": "Wired"},
    ]
    for fb in fallback_news:
        if len(gnews_items) < 2 and fb["title"].lower() not in existing_topics:
            gnews_items.append(fb)

    # 3. Tarik Kandidat dari YouTube Dongeng (Filter duplikat)
    dongeng_items: list[dict[str, Any]] = []
    try:
        from orchestrator.tools.youtube_client import list_channel_videos
        for ch_id in settings.DONGENG_TARGET_CHANNELS:
            vids = list_channel_videos(ch_id, max_results=5)
            for v in vids:
                v_id = str(v.get("id") or v.get("video_id") or "").strip().lower()
                v_title = str(v.get("title") or "").strip().lower()
                if v_id and v_id not in existing_topics and v_title not in existing_topics:
                    if v not in dongeng_items:
                        dongeng_items.append(v)
            if len(dongeng_items) >= 3:
                break
    except Exception as exc:
        logger.warning(f"Gagal memindai YouTube Dongeng: {exc}")

    fallback_dongeng = [
        {"id": "dongeng_kancil_buaya_2026", "title": "Kisah Si Kancil dan Buaya yang Cerdik Menyeberang Sungai"},
        {"id": "dongeng_sangkuriang_tangkuban", "title": "Legenda Sangkuriang dan Terciptanya Gunung Tangkuban Perahu"},
        {"id": "dongeng_timun_mas_raksasa", "title": "Petualangan Berani Timun Mas Mengalahkan Raksasa Jahat"},
        {"id": "dongeng_malin_kundang_pantai", "title": "Kisah Pengorbanan Ibu dan Pelajaran Hidup Malin Kundang"},
        {"id": "dongeng_keong_mas_candra", "title": "Misteri Keong Mas dan Putri Candra Kirana yang Bijaksana"},
    ]
    for fb in fallback_dongeng:
        if len(dongeng_items) < 3 and fb["title"].lower() not in existing_topics and fb["id"].lower() not in existing_topics:
            dongeng_items.append(fb)

    # 4. Susun Alokasi Jadwal Pintar (Smart Merging)
    # Jadwal bergantian antara Stark (Tech @ 09:00 WIB) dan Usagi (Dongeng @ 19:00 WIB)
    now_wib = datetime.now(WIB)
    planned_slots: list[dict[str, Any]] = []

    # Susun antrean 7 konten baru:
    task_definitions = [
        ("stark", "trend-article", github_items[0] if len(github_items) > 0 else fallback_repos[0], 9),
        ("usagi", "dongeng", dongeng_items[0] if len(dongeng_items) > 0 else fallback_dongeng[0], 19),
        ("stark", "trend-article", gnews_items[0] if len(gnews_items) > 0 else fallback_news[0], 9),
        ("usagi", "dongeng", dongeng_items[1] if len(dongeng_items) > 1 else fallback_dongeng[1], 19),
        ("stark", "trend-article", github_items[1] if len(github_items) > 1 else fallback_repos[1], 9),
        ("usagi", "dongeng", dongeng_items[2] if len(dongeng_items) > 2 else fallback_dongeng[2], 19),
        ("stark", "trend-article", gnews_items[1] if len(gnews_items) > 1 else fallback_news[1], 9),
    ]

    for agent, t_type, item, target_hour in task_definitions:
        # Cari slot hari dan jam berikutnya yang BENAR-BENAR MASIH KOSONG
        check_day = 1
        sched_time_wib = None
        sched_time_utc = None

        while check_day <= 30: # Cari slot kosong hingga 30 hari ke depan
            candidate_wib = (now_wib + timedelta(days=check_day)).replace(
                hour=target_hour, minute=0, second=0, microsecond=0
            )
            slot_key = candidate_wib.strftime("%Y-%m-%d-%H")
            if slot_key not in occupied_slots:
                # Slot kosong ditemukan!
                occupied_slots.add(slot_key)
                sched_time_wib = candidate_wib
                sched_time_utc = candidate_wib.astimezone(timezone.utc)
                break
            check_day += 1

        if not sched_time_wib or not sched_time_utc:
            # Fallback darurat
            sched_time_wib = (now_wib + timedelta(days=len(planned_slots) + 1)).replace(
                hour=target_hour, minute=0, second=0, microsecond=0
            )
            sched_time_utc = sched_time_wib.astimezone(timezone.utc)

        schedule_id = f"sched_{uuid.uuid4().hex[:10]}"
        task_id = f"task_{schedule_id[6:]}"

        if agent == "stark":
            agent_name = "Stark"
            if "repo_name" in item:
                title = f"Bedah Repositori: {item['repo_name']}"
                payload = {
                    "schedule_id": schedule_id,
                    "task_id": task_id,
                    "thread_id": task_id,
                    "task_type": "article",
                    "action": "trend-article",
                    "input_data": {
                        "schedule_id": schedule_id,
                        "query": item.get("description") or item["repo_name"],
                        "topic": title,
                        "task_type": "article",
                        "action": "trend-article",
                        "source": "github",
                        "target_urls": item["repo_url"],
                        "category": "programming",
                        "dry_run": False,
                    },
                }
            else:
                title = item.get("title", "Google News Tech Update")
                payload = {
                    "schedule_id": schedule_id,
                    "task_id": task_id,
                    "thread_id": task_id,
                    "task_type": "article",
                    "action": "trend-article",
                    "input_data": {
                        "schedule_id": schedule_id,
                        "query": title,
                        "topic": title,
                        "task_type": "article",
                        "action": "trend-article",
                        "source": "gnews",
                        "target_urls": item.get("url", ""),
                        "category": "technology",
                        "dry_run": False,
                    },
                }
        else:
            agent_name = "Usagi"
            vid_id = item.get("id") or item.get("video_id")
            title = item.get("title") or f"Dongeng Anak {vid_id}"
            payload = {
                "schedule_id": schedule_id,
                "task_id": task_id,
                "thread_id": task_id,
                "task_type": "dongeng",
                "action": "start",
                "video_id": vid_id,
                "input_data": {
                    "schedule_id": schedule_id,
                    "video_id": vid_id,
                    "query": title,
                    "topic": title,
                    "task_type": "dongeng",
                    "dry_run": False,
                },
            }

        planned_slots.append({
            "id": schedule_id,
            "agent_name": agent_name,
            "task_type": t_type,
            "title": title[:250],
            "payload": payload,
            "scheduled_at": sched_time_utc,
            "scheduled_at_wib": sched_time_wib.strftime("%A, %d %b %Y %H:%M WIB"),
            "status": "pending",
        })

    # 5. Simpan ke database PostgreSQL (content_schedules)
    saved_count = 0
    with postgres_pool.connection() as conn:
        with conn.cursor() as cur:
            for s in planned_slots:
                cur.execute(
                    """
                    INSERT INTO content_schedules (
                        id, agent_name, task_type, title, payload, scheduled_at, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        payload = EXCLUDED.payload,
                        scheduled_at = EXCLUDED.scheduled_at,
                        status = EXCLUDED.status;
                    """,
                    (
                        s["id"],
                        s["agent_name"],
                        s["task_type"],
                        s["title"],
                        json.dumps(s["payload"]),
                        s["scheduled_at"],
                        s["status"],
                    ),
                )
                saved_count += 1

    logger.info(f"✅ [Bay-Zero Planner] Berhasil menggabungkan {saved_count} jadwal baru tanpa bentrok!")
    return planned_slots

    logger.info(f"✅ [Bay-Zero Planner] Berhasil menyimpan {saved_count} jadwal konten ke database!")
    return planned_slots


def list_editorial_schedules(limit: int = 20, status: str | None = None) -> list[dict[str, Any]]:
    """Mengambil daftar jadwal konten dari PostgreSQL content_schedules."""
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

    parser = argparse.ArgumentParser(description="Bay-Zero Editorial Content Planner")
    parser.add_argument("--generate-week", action="store_true", help="Buat jadwal otomatis 7 hari ke depan")
    parser.add_argument("--list", action="store_true", help="Tampilkan jadwal editorial saat ini")
    args = parser.parse_args()

    try:
        if args.generate_week:
            generate_weekly_editorial_plan()
            schedules = list_editorial_schedules(limit=20)
            print_schedules_table(schedules)
        elif args.list:
            schedules = list_editorial_schedules(limit=20)
            print_schedules_table(schedules)
        else:
            parser.print_help()
    finally:
        try:
            postgres_pool.close()
        except Exception:
            pass
