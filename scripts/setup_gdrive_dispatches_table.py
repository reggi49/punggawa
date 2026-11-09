#!/usr/bin/env python3
"""
Setup table gdrive_media_dispatches di PostgreSQL Supabase.
Mencatat riwayat posting video dari Google Drive ke berbagai channel media sosial.
Mencegah duplikasi posting per channel tanpa mengubah/memindahkan file di Google Drive.
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
logger = logging.getLogger("SetupGDriveDispatchesTable")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS gdrive_media_dispatches (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(100) NOT NULL,          -- ID Channel tujuan (misal: cmw909dnc0013o274l7q4fjc5)
    channel_name VARCHAR(100),                  -- Nama akun (misal: kittengaul, berdongeng)
    gdrive_file_id VARCHAR(120) NOT NULL,       -- ID permanen unik dari Google Drive
    gdrive_file_name VARCHAR(255) NOT NULL,     -- Nama file asli di Google Drive
    file_md5 VARCHAR(64),                       -- Hash MD5 sidik jari file dari metadata Google
    file_size_bytes BIGINT,                     -- Ukuran file dalam bytes
    postiz_post_id VARCHAR(100),                -- ID postingan yang berhasil dibuat di Postiz
    platform VARCHAR(50) DEFAULT 'instagram',   -- 'instagram' | 'tiktok' | 'youtube' | 'threads'
    dispatched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_channel_gdrive_file UNIQUE (channel_id, gdrive_file_id)
);

CREATE INDEX IF NOT EXISTS idx_gdrive_channel_lookup 
ON gdrive_media_dispatches (channel_id, gdrive_file_id);

CREATE INDEX IF NOT EXISTS idx_gdrive_file_md5
ON gdrive_media_dispatches (channel_id, file_md5);
"""


def setup_gdrive_table():
    """Menjalankan DDL skema gdrive_media_dispatches di PostgreSQL Supabase."""
    logger.info("Memulai inisialisasi tabel 'gdrive_media_dispatches' di Supabase...")
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
                logger.info("✅ Tabel 'gdrive_media_dispatches' dan index berhasil dibuat / diverifikasi.")

                # Verifikasi struktur tabel
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'gdrive_media_dispatches'
                    ORDER BY ordinal_position;
                    """
                )
                columns = cur.fetchall()
                logger.info(f"Struktur tabel terverifikasi ({len(columns)} kolom):")
                for col_name, data_type, is_nullable in columns:
                    null_str = "NULL" if is_nullable == "YES" else "NOT NULL"
                    logger.info(f"   • {col_name:20} : {data_type:15} ({null_str})")
        return True
    except Exception as exc:
        logger.error(f"❌ Gagal membuat tabel gdrive_media_dispatches: {exc}", exc_info=True)
        return False
    finally:
        try:
            postgres_pool.close()
        except Exception:
            pass


if __name__ == "__main__":
    success = setup_gdrive_table()
    sys.exit(0 if success else 1)
