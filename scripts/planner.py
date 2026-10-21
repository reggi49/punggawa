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


def generate_weekly_editorial_plan() -> list[dict[str, Any]]:
    """
    Menghasilkan rencana editorial mingguan (7 konten untuk 7 hari ke depan):
    - 2 Repositori open-source teratas dari GitHub Trending Weekly (Stark)
    - 2 Berita teknologi global terhangat dari Google News RSS (Stark)
    - 3 Video cerita rakyat/fabel dari YouTube Dongeng (Usagi)
    Alokasi:
    - Stark: Pukul 09.00 WIB
    - Usagi: Pukul 19.00 WIB
    """
    logger.info("🧠 [Bay-Zero Planner] Menginisialisasi kurasi konten 7 hari ke depan...")

    # 1. Tarik 2 Topik dari GitHub Trending Weekly
    github_items: list[dict[str, Any]] = []
    try:
        github_items = get_github_trending_weekly(language="", max_items=2)
        logger.info(f"GitHub Trending: Mendapatkan {len(github_items)} kandidat.")
    except Exception as exc:
        logger.warning(f"Gagal mengambil GitHub Trending: {exc}")

    # Fallback jika GitHub tidak merespons
    if len(github_items) < 2:
        github_items.append({
            "repo_name": "langchain-ai/langgraph",
            "repo_url": "https://github.com/langchain-ai/langgraph",
            "description": "Build resilient language agents as graphs with human-in-the-loop and memory.",
            "language": "Python",
            "stars_this_week": 4200,
        })
        github_items.append({
            "repo_name": "astral-sh/uv",
            "repo_url": "https://github.com/astral-sh/uv",
            "description": "An extremely fast Python package and project manager, written in Rust.",
            "language": "Rust",
            "stars_this_week": 3500,
        })

    # 2. Tarik 2 Berita dari Google News RSS International
    gnews_items: list[dict[str, Any]] = []
    try:
        gnews_items = get_google_news_topics(keyword="technology", max_items=2, lang="en")
        logger.info(f"Google News RSS: Mendapatkan {len(gnews_items)} kandidat.")
    except Exception as exc:
        logger.warning(f"Gagal mengambil Google News: {exc}")

    if len(gnews_items) < 2:
        gnews_items.append({
            "title": "Next-Gen AI Reasoning Models Redefine Software Architecture",
            "url": "https://techcrunch.com/category/artificial-intelligence/",
            "source": "TechCrunch",
            "published_at": datetime.now(timezone.utc).isoformat(),
        })
        gnews_items.append({
            "title": "Autonomous Coding Agents and Multi-Agent Orchestration in 2026",
            "url": "https://theverge.com/tech",
            "source": "The Verge",
            "published_at": datetime.now(timezone.utc).isoformat(),
        })

    # 3. Tarik 3 Video Dongeng YouTube
    dongeng_items: list[dict[str, Any]] = []
    try:
        from orchestrator.tools.youtube_client import list_channel_videos
        for ch_id in settings.DONGENG_TARGET_CHANNELS:
            vids = list_channel_videos(ch_id, max_results=2)
            for v in vids:
                if v not in dongeng_items and len(dongeng_items) < 3:
                    dongeng_items.append(v)
            if len(dongeng_items) >= 3:
                break
    except Exception as exc:
        logger.warning(f"Gagal memindai YouTube Dongeng: {exc}")

    # Fallback kurasi dongeng jika API offline / kuota habis
    fallback_dongeng = [
        {"id": "UC7GZguUCh8gdEs-VKhWqkWA", "title": "Kisah Si Kancil dan Buaya yang Cerdik"},
        {"id": "UCaMrqakJglh9VQItR50pQwA", "title": "Legenda Sangkuriang dan Gunung Tangkuban Perahu"},
        {"id": "UC0y73P4z4V89w3P9K1K1K1A", "title": "Petualangan Timun Mas Melawan Raksasa"},
    ]
    for fb in fallback_dongeng:
        if len(dongeng_items) < 3:
            dongeng_items.append(fb)

    # 4. Susun Alokasi Jadwal 7 Hari ke Depan (Hari ke-1 s.d. Hari ke-7)
    # Jadwal bergantian antara Stark (Tech, 09:00 WIB) dan Usagi (Dongeng, 19:00 WIB)
    now_wib = datetime.now(WIB)
    planned_slots: list[dict[str, Any]] = []

    # Susun antrean 7 konten:
    # Day 1: Stark (GitHub Trending 1) @ 09:00 WIB
    # Day 2: Usagi (Dongeng 1)          @ 19:00 WIB
    # Day 3: Stark (Google News 1)      @ 09:00 WIB
    # Day 4: Usagi (Dongeng 2)          @ 19:00 WIB
    # Day 5: Stark (GitHub Trending 2) @ 09:00 WIB
    # Day 6: Usagi (Dongeng 3)          @ 19:00 WIB
    # Day 7: Stark (Google News 2)      @ 09:00 WIB

    task_definitions = [
        ("stark", "trend-article", github_items[0], 9),
        ("usagi", "dongeng", dongeng_items[0], 19),
        ("stark", "trend-article", gnews_items[0], 9),
        ("usagi", "dongeng", dongeng_items[1], 19),
        ("stark", "trend-article", github_items[1], 9),
        ("usagi", "dongeng", dongeng_items[2], 19),
        ("stark", "trend-article", gnews_items[1], 9),
    ]

    for day_offset, (agent, t_type, item, target_hour) in enumerate(task_definitions, start=1):
        sched_time_wib = (now_wib + timedelta(days=day_offset)).replace(
            hour=target_hour, minute=0, second=0, microsecond=0
        )
        # Convert ke UTC untuk penyimpanan database
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
