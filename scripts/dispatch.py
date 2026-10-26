#!/usr/bin/env python3
"""
Punggawa Command Center (CLI)
Kirim task, pantau riwayat eksekusi langsung dari Supabase, dan berikan persetujuan (approval)
tanpa memerlukan akses SSH ke server VPS.
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Pastikan module punggawa dapat diimport
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import settings
import redis
import psycopg


def get_redis_client():
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=15.0,
        socket_connect_timeout=10.0,
    )


def cmd_send(args):
    """Kirim task atau prompt baru ke antrean Redis Cloud."""
    r = get_redis_client()
    action = getattr(args, "action", None)
    task_type = getattr(args, "type", None) or "chat"
    video_id = getattr(args, "video_id", None)

    # 1. Kasus Routine Scan Channel YouTube Dongeng
    if action == "dongeng-scan":
        from orchestrator.tools.youtube_client import list_channel_videos
        max_count = getattr(args, "max", 10) or 10
        print(f"🔍 [SCANNING CHANNELS] Memindai {len(settings.DONGENG_TARGET_CHANNELS)} target channel (max {max_count} per channel)...")
        enqueued_count = 0
        for ch_id in settings.DONGENG_TARGET_CHANNELS:
            vids = list_channel_videos(ch_id, max_results=max_count)
            print(f"   • Channel {ch_id}: Menemukan {len(vids)} video.")
            for v in vids:
                t_id = f"dongeng_{v['id']}"
                payload = {
                    "task_id": t_id,
                    "thread_id": t_id,
                    "task_type": "dongeng",
                    "action": "start",
                    "video_id": v["id"],
                    "input_data": {
                        "video_id": v["id"],
                        "query": v.get("title", ""),
                        "topic": v.get("title", ""),
                        "task_type": "dongeng",
                        "dry_run": getattr(args, "dry_run", False),
                    },
                }
                r.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))
                enqueued_count += 1
        print(f"\n🚀 [SCAN COMPLETE] Berhasil memasukkan {enqueued_count} video ke antrean '{settings.TASK_QUEUE_NAME}'.")
        return

    # 2. Kasus Single Video Dongeng
    if action == "dongeng" or task_type == "dongeng" or video_id:
        target_video_id = video_id or args.prompt
        if not target_video_id:
            print("❌ Masukkan --video-id atau --prompt dengan ID / URL YouTube.")
            return

        task_id = args.thread_id or f"task_{uuid.uuid4().hex[:8]}"
        payload = {
            "task_id": task_id,
            "thread_id": task_id,
            "task_type": "dongeng",
            "action": "start",
            "video_id": target_video_id,
            "input_data": {
                "video_id": target_video_id,
                "query": args.prompt or f"Dongeng {target_video_id}",
                "topic": args.prompt or f"Dongeng {target_video_id}",
                "task_type": "dongeng",
                "dry_run": getattr(args, "dry_run", False),
            },
        }
        r.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))
        print(f"🚀 [ENQUEUE SUCCESS]")
        print(f"   Task ID   : {task_id}")
        print(f"   Type      : 'dongeng'")
        print(f"   Video ID  : '{target_video_id}'")
        print(f"   Dry Run   : {getattr(args, 'dry_run', False)}")
        print(f"   Queue     : {settings.TASK_QUEUE_NAME}")
        print(f"\nUntuk memantau proses: python -m scripts.dispatch status --thread-id {task_id}")
        return

    # 3. Kasus Penarikan Tren Otomatis (GitHub Trending / Google News)
    source = getattr(args, "source", None)
    lang = getattr(args, "lang", "")
    query = getattr(args, "query", "")
    is_trend_action = action in ("trend-article", "article-trend", "auto_curate_tech") or (source in ("github", "gnews", "google_news"))

    if is_trend_action:
        source_val = source or ("github" if lang else "gnews")
        task_id = args.thread_id or f"task_{uuid.uuid4().hex[:8]}"
        prompt_val = args.prompt or query or (f"GitHub Trending ({lang or 'All'})" if source_val == "github" else f"Google News: {query or 'Tech'}")

        payload = {
            "task_id": task_id,
            "thread_id": task_id,
            "task_type": "article",
            "action": action or "trend-article",
            "input_data": {
                "query": query or args.prompt or "",
                "topic": prompt_val,
                "task_type": "article",
                "action": action or "trend-article",
                "source": source_val,
                "lang": lang,
                "category": args.category if args.category != "technology" else ("programming" if source_val == "github" else "technology"),
                "urls": args.urls,
                "target_urls": args.urls,
                "dry_run": getattr(args, "dry_run", False),
            },
        }

        r.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))
        print(f"🚀 [ENQUEUE SUCCESS]")
        print(f"   Task ID   : {task_id}")
        print(f"   Action    : 'trend-article'")
        print(f"   Source    : {source_val.upper()} ({f'Lang: {lang}' if source_val == 'github' else f'Query: {query or prompt_val}'})")
        print(f"   Dry Run   : {getattr(args, 'dry_run', False)}")
        print(f"   Queue     : {settings.TASK_QUEUE_NAME}")
        print(f"\nUntuk memantau proses: python -m scripts.dispatch status --thread-id {task_id}")
        return

    # 4. Kasus Chat Agent atau Article Pipeline Biasa
    if not args.prompt:
        print("❌ Masukkan parameter --prompt untuk task chat/article, atau gunakan --action trend-article.")
        return

    task_id = args.thread_id or f"task_{uuid.uuid4().hex[:8]}"
    payload = {
        "task_id": task_id,
        "thread_id": task_id,
        "task_type": task_type,
        "action": "start",
        "input_data": {
            "query": args.prompt,
            "topic": args.prompt,
            "task_type": task_type,
            "category": args.category,
            "urls": args.urls,
            "target_urls": args.urls,
            "dry_run": getattr(args, "dry_run", False),
        },
    }

    r.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))
    print(f"🚀 [ENQUEUE SUCCESS]")
    print(f"   Task ID   : {task_id}")
    print(f"   Type      : '{task_type}'")
    print(f"   Prompt    : '{args.prompt}'")
    print(f"   Category  : {args.category}")
    print(f"   URLs      : {args.urls or '(tidak ada)'}")
    print(f"   Queue     : {settings.TASK_QUEUE_NAME}")
    print(f"\nUntuk memantau proses: python -m scripts.dispatch status --thread-id {task_id}")


def cmd_status(args):
    """Membaca status checkpoint, response, dan riwayat pesan langsung dari LangGraph Checkpointer."""
    thread_id = args.thread_id
    if not thread_id:
        print("❌ Masukkan parameter --thread-id")
        return

    print(f"🔍 Mengambil status & hasil dari Supabase untuk thread: '{thread_id}'...")

    try:
        from orchestrator.graph import agent_app
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = agent_app.get_state(config)

        if not state_snapshot or not state_snapshot.values:
            print(f"⚠️  Belum ada data checkpoint untuk thread_id '{thread_id}'.")
            print("   Pastikan worker aktif dan task telah diproses.")
            return

        values = state_snapshot.values
        status = values.get("status", "unknown")
        last_worker = values.get("last_processed_by", "unknown")
        logs = values.get("execution_logs", [])
        result = values.get("result", {})
        pending_tool = values.get("pending_tool_call")
        messages = values.get("messages", [])

        print("\n" + "=" * 60)
        print(f"📌 THREAD STATUS : {status.upper()}")
        print(f"   Thread ID     : {thread_id}")
        print(f"   Last Worker   : {last_worker}")
        if pending_tool:
            print(f"   ⚠️  PENDING TOOL : {pending_tool.get('name')} (Memerlukan Approval)")
            print(f"      Arguments    : {pending_tool.get('args')}")
        print("=" * 60)

        # Tampilkan Hasil Akhir / Response AI / Artikel Terbit / Dongeng Video
        dual_content = values.get("dual_content")
        published_ids = values.get("published_ids")
        dual_images = values.get("dual_images")
        curation = values.get("curation_result")
        video_id = values.get("video_id")
        cms_post = values.get("cms_post_result")

        if curation or video_id:
            print("\n🎬 DONGENG YOUTUBE CMS PUBLICATION:")
            print(f"   Video ID    : {video_id or 'N/A'}")
            if curation:
                print(f"   Judul Bersih: {curation.get('title', 'N/A')}")
                print(f"   Kategori    : {curation.get('category_name', 'N/A')} (ID: {curation.get('category_id', 'N/A')})")
                print(f"   Status Skip : {curation.get('skip', False)} (Alasan: {curation.get('reason', '-')})")
            if cms_post:
                print(f"   CMS Result  : {cms_post}")
        elif dual_content:
            id_data = dual_content.get("id", {})
            en_data = dual_content.get("en", {})
            pub_id = published_ids.get("id") if published_ids else "N/A"
            pub_en = published_ids.get("en") if published_ids else "N/A"
            print("\n📰 DUAL-LANGUAGE ARTIKEL PUBLISHED:")
            print(f"   🇮🇩 [ID] Judul   : {id_data.get('title')}")
            print(f"        Meta    : {id_data.get('meta_desc')}")
            print(f"        Tags    : {', '.join(id_data.get('tags', []))}")
            print(f"        Post ID : {pub_id}")
            print(f"        Panjang : {len(id_data.get('content', ''))} karakter")
            print()
            print(f"   🇬🇧 [EN] Title   : {en_data.get('title')}")
            print(f"        Meta    : {en_data.get('meta_desc')}")
            print(f"        Tags    : {', '.join(en_data.get('tags', []))}")
            print(f"        Post ID : {pub_en}")
            print(f"        Length  : {len(en_data.get('content', ''))} characters")
            if dual_images:
                id_ok = "Rendered (Base64 JPEG)" if dual_images.get("id") else "None"
                en_ok = "Rendered (Base64 JPEG)" if dual_images.get("en") else "None"
                print(f"\n🎨 THUMBNAILS: [ID] {id_ok} | [EN] {en_ok}")
        elif result and result.get("summary"):
            print("\n💬 HASIL / JAWABAN AKHIR:")
            print(f"   {result.get('summary')}")
        else:
            print("\n💬 HASIL / JAWABAN AKHIR:")
            # Ambil dari pesan AI terakhir jika summary belum terisi
            last_ai = next((m.content for m in reversed(messages) if getattr(m, "type", "") == "ai" and m.content), None)
            if last_ai:
                print(f"   {last_ai}")
            else:
                print("   (Belum ada output teks)")

        # Riwayat Percakapan / Tool Message
        if len(messages) > 1:
            print("\n🔄 RIWAYAT INTERAKSI / TOOL CALLS:")
            for msg in messages:
                role = getattr(msg, "type", "unknown")
                if role == "human":
                    print(f"   👤 [USER] : {msg.content}")
                elif role == "ai":
                    tc = getattr(msg, "tool_calls", None)
                    if tc:
                        print(f"   🤖 [AI Tool Call] : {[call['name'] for call in tc]}")
                    elif msg.content:
                        print(f"   🤖 [AI Response]  : {msg.content}")
                elif role == "tool":
                    print(f"   ⚙️  [Tool Result] : {msg.content[:150]}...")

        if logs:
            print("\n📜 EXECUTION LOGS:")
            for log_entry in logs[-6:]:
                print(f"   • {log_entry}")

        if status == "waiting_approval":
            print(f"\n💡 Task sedang menunggu approval! Berikan konfirmasi dengan:")
            print(f"   python -m scripts.dispatch approve --thread-id {thread_id} --yes")
        print()

    except Exception as exc:
        print(f"❌ Gagal membaca Supabase: {exc}")
    finally:
        try:
            from orchestrator.connections import postgres_pool
            postgres_pool.close()
        except Exception:
            pass


def cmd_approve(args):
    """Melanjutkan (resume) task yang sedang ditahan di checkpoint approval."""
    r = get_redis_client()
    thread_id = args.thread_id
    is_approved = not args.reject

    payload = {
        "task_id": thread_id,
        "thread_id": thread_id,
        "action": "resume",
        "approved": is_approved,
        "input_data": {"action": "approval_response"},
    }

    r.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))
    status_str = "DISETUJUI (APPROVED)" if is_approved else "DITOLAK (REJECTED)"
    print(f"✅ [APPROVAL DISPATCHED] Thread '{thread_id}' telah {status_str}.")
    print(f"   Worker akan melanjutkan eksekusi dari checkpoint PostgreSQL.")


def cmd_cleanup(args):
    """Membersihkan riwayat checkpoints dan thread di PostgreSQL yang berumur lebih dari N hari."""
    from scripts.cleanup import clean_old_checkpoints
    days = getattr(args, "days", 3)
    print(f"🧹 Menjalankan pembersihan database untuk data lebih tua dari {days} hari...")
    try:
        res = clean_old_checkpoints(days=days)
        print("\n============================================================")
        print("📌 DATABASE RETENTION CLEANUP REPORT")
        print("============================================================")
        print(f"Status           : {res['status'].upper()}")
        print(f"Retensi          : > {res['days']} hari")
        print(f"Thread Dihapus   : {res['deleted_threads_count']}")
        print(f"Checkpoints      : {res['deleted_checkpoints']}")
        print(f"Blobs            : {res['deleted_blobs']}")
        print(f"Writes           : {res['deleted_writes']}")
        if res["deleted_threads"]:
            print(f"Thread IDs       : {', '.join(res['deleted_threads'][:10])}{' ...' if len(res['deleted_threads']) > 10 else ''}")
        if res["error"]:
            print(f"Error            : {res['error']}")
        print("============================================================\n")
    finally:
        try:
            from orchestrator.connections import postgres_pool
            postgres_pool.close()
        except Exception:
            pass


def cmd_plan(args):
    """Mengelola kalender editorial mingguan Bay-Zero Planner & Anti-Idle Rebalancer."""
    from scripts.planner import (
        generate_weekly_editorial_plan,
        rebalance_and_replenish_schedules,
        scan_and_audit_schedules,
        list_editorial_schedules,
        print_schedules_table,
    )
    from orchestrator.connections import postgres_pool
    days = getattr(args, "days", 7) or 7
    limit = getattr(args, "limit", 25) or 25
    try:
        if getattr(args, "scan", False):
            audit = scan_and_audit_schedules(days_ahead=days)
            print(f"\n🔍 [Bay-Zero Schedule Audit] Tanggal Audit: {audit['audit_date']}")
            print("=" * 80)
            for agent, agent_days in audit["agents"].items():
                print(f"\n👤 Agen: {agent}")
                for d in agent_days:
                    icon = "✅" if d["is_covered"] else "❌ KOSONG (IDLE!)"
                    t_info = f" -> {d['task_title'][:35]}" if d["task_title"] else ""
                    print(f"   {d['date']} ({d['day_name'][:3]}): {icon:<15} [{d['status']}]{t_info}")
            print("=" * 80 + "\n")
        elif getattr(args, "rebalance", False):
            print("🛡️ [Bay-Zero Rebalancer] Memindai, memajukan jadwal (fast-forward), dan mengisi slot kosong...")
            res = rebalance_and_replenish_schedules(days_ahead=days)
            print(f"⏩ Tugas dimajukan (Fast-Forward): {len(res['pulled_forward'])}")
            for p in res['pulled_forward']:
                print(f"   ↳ {p['agent_name']}: '{p['title'][:35]}' dimajukan dari {p['old_date']} -> {p['new_date']}")
            print(f"✨ Tugas baru (Replenish): {len(res['replenished'])}")
            for r in res['replenished']:
                print(f"   ↳ {r['agent_name']}: '{r['title'][:35]}' dijadwalkan pada {r['date']}")
            schedules = list_editorial_schedules(limit=limit)
            print_schedules_table(schedules)
        elif getattr(args, "generate_week", False):
            print("🧠 [Bay-Zero Planner] Menyelaraskan dan melengkapi jadwal konten untuk 7 hari ke depan...")
            res = rebalance_and_replenish_schedules(days_ahead=days)
            print(f"✨ Tugas baru dijadwalkan: {len(res['replenished'])}, dimajukan: {len(res['pulled_forward'])}")
            schedules = list_editorial_schedules(limit=limit)
            print_schedules_table(schedules)
        else:
            schedules = list_editorial_schedules(limit=limit)
            print_schedules_table(schedules)
    finally:
        try:
            postgres_pool.close()
        except Exception:
            pass


def cmd_health(args):
    """Pemeriksaan ketersediaan microservice eksternal & server (Bay-Zero Inspector - Zero LLM Cost)."""
    from orchestrator.tools.uptime_checker import run_all_health_checks
    print("\n🔍 [Bay-Zero Inspector] Memeriksa ketersediaan microservice eksternal & kesehatan server...\n")
    data = run_all_health_checks()
    services = data.get("services", [])
    overall = data.get("overall_status", "healthy").upper()

    col_w = [22, 10, 14, 12]
    border_top = f"┌{'─' * (col_w[0] + 2)}┬{'─' * (col_w[1] + 2)}┬{'─' * (col_w[2] + 2)}┬{'─' * (col_w[3] + 2)}┐"
    border_mid = f"├{'─' * (col_w[0] + 2)}┼{'─' * (col_w[1] + 2)}┼{'─' * (col_w[2] + 2)}┼{'─' * (col_w[3] + 2)}┤"
    border_bot = f"└{'─' * (col_w[0] + 2)}┴{'─' * (col_w[1] + 2)}┴{'─' * (col_w[2] + 2)}┴{'─' * (col_w[3] + 2)}┘"

    print(border_top)
    print(f"│ {'Service':<{col_w[0]}} │ {'Status':<{col_w[1]}} │ {'HTTP Code':<{col_w[2]}} │ {'Latency':<{col_w[3]}} │")
    print(border_mid)

    for s in services:
        name = s["name"][:col_w[0]]
        is_ok = s["status"] == "healthy"
        status_str = "HEALTHY" if is_ok else "DOWN"
        http_code = f"{s['status_code']} OK" if is_ok else (s.get("error") or "Error")[:col_w[2]]
        latency = f"{s['latency_ms']} ms" if s.get("latency_ms") is not None else "-"
        print(f"│ {name:<{col_w[0]}} │ {status_str:<{col_w[1]}} │ {http_code:<{col_w[2]}} │ {latency:<{col_w[3]}} │")

    print(border_bot)
    print(f"\nStatus Keseluruhan: {'🟢 NORMAL (HEALTHY)' if overall == 'HEALTHY' else '🔴 TERGANGGU (DEGRADED)'}")
    print(f"Waktu Pengecekan: {datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S WIB')}\n")

    try:
        from orchestrator.connections import postgres_pool
        postgres_pool.close()
    except Exception:
        pass
    os._exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Punggawa CLI Command Center - Autonomous AI Orchestrator Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: send
    p_send = subparsers.add_parser("send", help="Kirim task/prompt baru ke worker")
    p_send.add_argument("--prompt", "-p", default=None, help="Instruksi, topik, atau query untuk agent")
    p_send.add_argument(
        "--action",
        "-a",
        default=None,
        choices=["chat", "article", "dongeng", "dongeng-scan", "trend-article", "article-trend", "auto_curate_tech"],
        help="Aksi spesifik: 'trend-article' (kurasi berita/trending), 'dongeng' (single video), 'dongeng-scan', 'article', 'chat'",
    )
    p_send.add_argument(
        "--source",
        "-s",
        default=None,
        choices=["github", "gnews", "google_news"],
        help="Sumber kurasi tren: 'github' (trending weekly) atau 'gnews' (Google News RSS)",
    )
    p_send.add_argument(
        "--lang",
        "-l",
        default="",
        help="Bahasa pemrograman untuk filter GitHub Trending (misal: python, typescript, go, rust)",
    )
    p_send.add_argument(
        "--query",
        "-q",
        default="",
        help="Kata kunci topik pencarian Google News (misal: 'artificial intelligence', 'WebAssembly')",
    )
    p_send.add_argument(
        "--type",
        "-T",
        default="chat",
        choices=["chat", "article", "dongeng"],
        help="Jenis graf: 'chat', 'article', atau 'dongeng'",
    )
    p_send.add_argument("--video-id", "-v", default=None, help="ID Video YouTube untuk pipeline dongeng")
    p_send.add_argument("--max", "-m", type=int, default=10, help="Jumlah maksimal video per channel saat scan")
    p_send.add_argument("--category", "-c", default="technology", help="Kategori artikel (tech, programming, etc)")
    p_send.add_argument("--urls", "-u", default="", help="Daftar URL referensi (pisahkan dengan koma)")
    p_send.add_argument("--thread-id", "-t", default=None, help="Thread ID kustom (opsional)")
    p_send.add_argument("--dry-run", action="store_true", help="Jalankan hingga render image tanpa publish ke API")
    p_send.set_defaults(func=cmd_send)

    # Subcommand: status
    p_status = subparsers.add_parser("status", help="Pantau status thread langsung dari Supabase")
    p_status.add_argument("--thread-id", "-t", required=True, help="Thread ID yang ingin dipantau")
    p_status.set_defaults(func=cmd_status)

    # Subcommand: approve
    p_approve = subparsers.add_parser("approve", help="Setujui atau tolak aksi sensitif yang tertahan")
    p_approve.add_argument("--thread-id", "-t", required=True, help="Thread ID yang menunggu approval")
    p_approve.add_argument("--yes", "-y", action="store_true", help="Setujui eksekusi tool")
    p_approve.add_argument("--reject", "-r", action="store_true", help="Tolak eksekusi tool")
    p_approve.set_defaults(func=cmd_approve)

    # Subcommand: cleanup
    p_cleanup = subparsers.add_parser("cleanup", help="Bersihkan riwayat checkpoint PostgreSQL yang kedaluwarsa")
    p_cleanup.add_argument("--days", "-d", type=int, default=3, help="Batas umur data dalam hari (default: 3)")
    p_cleanup.set_defaults(func=cmd_cleanup)

    # Subcommand: plan
    p_plan = subparsers.add_parser("plan", help="Kalender editorial dan otomasi jadwal konten (Bay-Zero Planner)")
    p_plan.add_argument("--rebalance", action="store_true", help="Pindai dan selaraskan jadwal (Fast-Forward & Replenish agar 0 agen nganggur)")
    p_plan.add_argument("--scan", action="store_true", help="Audit status keterisian jadwal seluruh agen hari ini dan 7 hari ke depan")
    p_plan.add_argument("--generate-week", action="store_true", help="Buat/lengkapi jadwal otomatis 7 hari ke depan (Stark & Usagi)")
    p_plan.add_argument("--days", "-d", type=int, default=7, help="Horizon perencanaan dalam hari (default: 7)")
    p_plan.add_argument("--list", action="store_true", help="Tampilkan daftar jadwal editorial saat ini")
    p_plan.add_argument("--limit", type=int, default=25, help="Jumlah baris jadwal yang ditampilkan (default: 25)")
    p_plan.set_defaults(func=cmd_plan)

    # Subcommand: health
    p_health = subparsers.add_parser("health", help="Pantau status ketersediaan microservice & server (Bay-Zero Inspector)")
    p_health.set_defaults(func=cmd_health)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

