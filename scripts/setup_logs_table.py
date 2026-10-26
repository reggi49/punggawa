#!/usr/bin/env python3
"""
Setup table agent_execution_logs di PostgreSQL Supabase.
Mendukung persistensi riwayat live log aktivitas agen antar-sesi,
sehingga pengelola dapat meninjau eksekusi tugas kapan pun (misal malam hari)
meskipun browser baru dibuka.
"""
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure root directory in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orchestrator.connections import postgres_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SetupLogsTable")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_execution_logs (
    id VARCHAR(64) PRIMARY KEY,
    thread_id VARCHAR(128) NOT NULL,
    agent_name VARCHAR(64) NOT NULL,
    node VARCHAR(128) NOT NULL,
    status VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_execution_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_execution_logs (agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_logs_thread ON agent_execution_logs (thread_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_status ON agent_execution_logs (status);
"""


def setup_logs_table() -> bool:
    """Menjalankan DDL skema agent_execution_logs dan memverifikasi tabel."""
    logger.info("Memulai inisialisasi tabel 'agent_execution_logs'...")
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
                logger.info("✅ Tabel 'agent_execution_logs' dan index berhasil dibuat / diverifikasi.")

                # Verifikasi kolom
                cur.execute(
                    """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'agent_execution_logs'
                    ORDER BY ordinal_position;
                    """
                )
                columns = cur.fetchall()
                logger.info(f"Struktur tabel terverifikasi ({len(columns)} kolom):")
                for col_name, data_type in columns:
                    logger.info(f"   • {col_name} ({data_type})")
        return True
    except Exception as exc:
        logger.error(f"❌ Gagal membuat tabel agent_execution_logs: {exc}", exc_info=True)
        return False


def backfill_logs_from_schedules():
    """
    Mengisi data riwayat awal ke agent_execution_logs berdasarkan
    task yang sudah selesai, gagal, atau berjalan di content_schedules.
    """
    logger.info("Memeriksa riwayat content_schedules untuk backfill awal...")
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                # Periksa apakah tabel logs sudah ada isinya
                cur.execute("SELECT COUNT(*) FROM agent_execution_logs;")
                existing_count = cur.fetchone()[0]
                if existing_count > 0:
                    logger.info(f"Tabel agent_execution_logs sudah memiliki {existing_count} data. Melewati backfill.")
                    return

                # Ambil seluruh jadwal yang pernah jalan
                cur.execute(
                    """
                    SELECT id, agent_name, task_type, title, status, started_at, completed_at, result_url, error_message, scheduled_at
                    FROM content_schedules
                    WHERE started_at IS NOT NULL OR completed_at IS NOT NULL OR status IN ('completed', 'failed', 'in_progress')
                    ORDER BY COALESCE(started_at, scheduled_at) ASC;
                    """
                )
                rows = cur.fetchall()
                logger.info(f"Menemukan {len(rows)} entri riwayat schedule untuk di-backfill...")

                inserted = 0
                for r in rows:
                    s_id, agent_name, task_type, title, status, started_at, completed_at, result_url, error_message, scheduled_at = r
                    
                    # 1. Log mulai pengerjaan
                    start_time = started_at or scheduled_at or datetime.now(timezone.utc)
                    start_log_id = f"log_start_{s_id}"
                    cur.execute(
                        """
                        INSERT INTO agent_execution_logs (
                            id, thread_id, agent_name, node, status, message, details, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING;
                        """,
                        (
                            start_log_id,
                            s_id,
                            agent_name,
                            "task_start",
                            "in_progress",
                            f"Memulai pengerjaan jadwal: '{title}'",
                            json.dumps({
                                "schedule_id": s_id,
                                "agent_name": agent_name,
                                "task_type": task_type,
                                "title": title,
                            }),
                            start_time,
                        ),
                    )
                    inserted += 1

                    # 2. Log selesai / gagal
                    if status == "completed":
                        done_time = completed_at or start_time
                        done_log_id = f"log_done_{s_id}"
                        cur.execute(
                            """
                            INSERT INTO agent_execution_logs (
                                id, thread_id, agent_name, node, status, message, details, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING;
                            """,
                            (
                                done_log_id,
                                s_id,
                                agent_name,
                                "publish_node",
                                "completed",
                                f"Sukses menerbitkan: '{title}'",
                                json.dumps({
                                    "schedule_id": s_id,
                                    "agent_name": agent_name,
                                    "title": title,
                                    "result_url": result_url,
                                }),
                                done_time,
                            ),
                        )
                        inserted += 1
                    elif status == "failed":
                        fail_time = completed_at or start_time
                        fail_log_id = f"log_fail_{s_id}"
                        cur.execute(
                            """
                            INSERT INTO agent_execution_logs (
                                id, thread_id, agent_name, node, status, message, details, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING;
                            """,
                            (
                                fail_log_id,
                                s_id,
                                agent_name,
                                "failed_node",
                                "failed",
                                f"❌ Gagal memproses '{title}'. Alasan: {error_message or 'Unknown error'}",
                                json.dumps({
                                    "schedule_id": s_id,
                                    "agent_name": agent_name,
                                    "title": title,
                                    "error": error_message,
                                }),
                                fail_time,
                            ),
                        )
                        inserted += 1

                logger.info(f"✅ Berhasil mem-backfill {inserted} entri log riwayat ke agent_execution_logs.")
    except Exception as exc:
        logger.warning(f"Gagal melakukan backfill log: {exc}")


if __name__ == "__main__":
    try:
        ok = setup_logs_table()
        if ok:
            backfill_logs_from_schedules()
    finally:
        try:
            postgres_pool.close()
        except Exception:
            pass

