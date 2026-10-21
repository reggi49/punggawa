#!/usr/bin/env python3
"""
Setup table content_schedules di PostgreSQL Supabase.
Mendukung arsitektur Automated Content Scheduling (Bay-Zero Planner) dan
Observability / Error Reporting lifecycle.
"""
import logging
import os
import sys

# Ensure root directory in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orchestrator.connections import postgres_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SetupSchedulesTable")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS content_schedules (
    id VARCHAR(64) PRIMARY KEY,
    agent_name VARCHAR(32) NOT NULL,            -- 'Stark' | 'Usagi' | 'Bay-Zero'
    task_type VARCHAR(64) NOT NULL,             -- 'trend-article' | 'dongeng' | 'article'
    title VARCHAR(255) NOT NULL,                -- Judul artikel atau dongeng
    payload JSONB NOT NULL,                     -- Konfigurasi input LangGraph
    scheduled_at TIMESTAMPTZ NOT NULL,          -- Waktu rencana eksekusi
    status VARCHAR(20) DEFAULT 'pending',       -- 'pending' | 'in_progress' | 'completed' | 'failed'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result_url TEXT,                            -- URL publikasi yang berhasil
    error_message TEXT,                         -- Pesan error lengkap jika gagal
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedules_due ON content_schedules (scheduled_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_schedules_status ON content_schedules (status);
"""


def setup_schedules_table():
    """Menjalankan DDL skema content_schedules."""
    logger.info("Memulai inisialisasi tabel 'content_schedules'...")
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
                logger.info("✅ Tabel 'content_schedules' dan index berhasil dibuat / diverifikasi.")

                # Verifikasi keberadaan tabel
                cur.execute(
                    """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'content_schedules'
                    ORDER BY ordinal_position;
                    """
                )
                columns = cur.fetchall()
                logger.info(f"Struktur tabel terverifikasi ({len(columns)} kolom):")
                for col_name, data_type in columns:
                    logger.info(f"   • {col_name} ({data_type})")
        return True
    except Exception as exc:
        logger.error(f"❌ Gagal membuat tabel content_schedules: {exc}", exc_info=True)
        return False
    finally:
        try:
            postgres_pool.close()
        except Exception:
            pass


if __name__ == "__main__":
    success = setup_schedules_table()
    sys.exit(0 if success else 1)
