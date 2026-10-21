#!/usr/bin/env python3
"""
Database Capacity & Retention Cleanup Module for Punggawa.
Periodically purges LangGraph checkpoints, writes, and blobs older than N days
from PostgreSQL to ensure long-term stability within resource limits.
"""
import argparse
import logging
import os
import sys
from typing import Any

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger("DatabaseCleanup")


def clean_old_checkpoints(days: int = 3) -> dict[str, Any]:
    """
    Safely and transactionally deletes thread history and checkpoints older than `days` days.
    Execution order:
      1. Find thread_ids whose latest checkpoint timestamp is older than `days`.
      2. Delete from checkpoint_writes
      3. Delete from checkpoint_blobs
      4. Delete from checkpoints
    """
    from orchestrator.connections import postgres_pool
    if days < 0:
        raise ValueError("Parameter 'days' must be a non-negative integer.")

    logger.info(f"Memulai pembersihan thread & checkpoints dengan retensi > {days} hari...")

    try:
        from orchestrator.events import emit_agent_event
        emit_agent_event(
            thread_id="system",
            node="housekeeping",
            status="in_progress",
            message="Janitor Bot aktif: Menyapu sisa checkpoint & memangkas data...",
        )
    except Exception:
        pass

    result: dict[str, Any] = {
        "status": "success",
        "days": days,
        "deleted_threads_count": 0,
        "deleted_threads": [],
        "deleted_writes": 0,
        "deleted_blobs": 0,
        "deleted_checkpoints": 0,
        "error": None,
    }

    try:
        with postgres_pool.connection() as conn:
            # 1. Cari kandidat thread_id yang seluruh aktivitas checkpoint-nya lebih tua dari `days` hari
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT thread_id, max((checkpoint->>'ts')::timestamptz) as latest_ts
                    FROM checkpoints
                    GROUP BY thread_id
                    HAVING max((checkpoint->>'ts')::timestamptz) < NOW() - (%s * INTERVAL '1 day');
                    """,
                    (days,),
                )
                rows = cur.fetchall()

            if not rows:
                logger.info(f"Tidak ada riwayat checkpoint yang lebih tua dari {days} hari.")
                return result

            thread_ids = [row[0] for row in rows]
            result["deleted_threads_count"] = len(thread_ids)
            result["deleted_threads"] = thread_ids

            # 2. Hapus secara transaksional: writes -> blobs -> checkpoints
            with conn.transaction():
                with conn.cursor() as cur:
                    # 2a. Delete writes
                    cur.execute(
                        "DELETE FROM checkpoint_writes WHERE thread_id = ANY(%s);",
                        (thread_ids,),
                    )
                    result["deleted_writes"] = cur.rowcount

                    # 2b. Delete blobs
                    cur.execute(
                        "DELETE FROM checkpoint_blobs WHERE thread_id = ANY(%s);",
                        (thread_ids,),
                    )
                    result["deleted_blobs"] = cur.rowcount

                    # 2c. Delete checkpoints
                    cur.execute(
                        "DELETE FROM checkpoints WHERE thread_id = ANY(%s);",
                        (thread_ids,),
                    )
                    result["deleted_checkpoints"] = cur.rowcount

            logger.info(
                f"✅ Pembersihan selesai! {result['deleted_threads_count']} thread dihapus "
                f"({result['deleted_checkpoints']} checkpoints, {result['deleted_blobs']} blobs, "
                f"{result['deleted_writes']} writes)."
            )

            try:
                from orchestrator.events import emit_agent_event
                emit_agent_event(
                    thread_id="system",
                    node="housekeeping",
                    status="completed",
                    message="Pembersihan tuntas. Kembali ke docking station.",
                )
            except Exception:
                pass

    except Exception as exc:
        logger.error(f"❌ Gagal membersihkan checkpoint lama: {exc}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(exc)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Pembersihan Otomatis Retensi Checkpoint PostgreSQL Punggawa",
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=3,
        help="Batas umur data thread/checkpoint dalam hari (default: 3 hari)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    )

    try:
        res = clean_old_checkpoints(days=args.days)
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
            postgres_pool.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
