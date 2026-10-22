#!/usr/bin/env python3
"""
Setup table job_opportunities di PostgreSQL Supabase.
Mendukung penyimpanan hasil evaluasi Career-Ops A-H, fit scoring,
dan dokumen aplikasi yang ditailor (Cover Letter, STAR+R prep).
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
logger = logging.getLogger("SetupJobTables")

CREATE_JOB_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS job_opportunities (
    id VARCHAR(64) PRIMARY KEY,
    job_url TEXT NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    role_title VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    work_mode VARCHAR(50) DEFAULT 'remote',
    salary_range VARCHAR(100),
    job_description TEXT NOT NULL,
    
    fit_score INT NOT NULL DEFAULT 1,
    fit_reasoning TEXT NOT NULL,
    evaluation_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    
    tailored_cover_letter TEXT,
    tailored_cv_points JSONB DEFAULT '[]'::jsonb,
    interview_star_prep JSONB DEFAULT '[]'::jsonb,
    
    status VARCHAR(50) DEFAULT 'evaluated',
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_opp_score ON job_opportunities(fit_score DESC);
CREATE INDEX IF NOT EXISTS idx_job_opp_status ON job_opportunities(status);
CREATE INDEX IF NOT EXISTS idx_job_opp_url ON job_opportunities(job_url);
"""


def setup_job_tables():
    """Menjalankan DDL skema job_opportunities."""
    logger.info("Memulai inisialisasi tabel 'job_opportunities'...")
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_JOB_TABLE_SQL)
                conn.commit()
                logger.info("✅ Tabel 'job_opportunities' dan index berhasil dibuat / diverifikasi.")

                # Verifikasi kolom yang terbentuk
                cur.execute(
                    """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'job_opportunities'
                    ORDER BY ordinal_position;
                    """
                )
                columns = cur.fetchall()
                logger.info(f"Daftar kolom ({len(columns)}):")
                for col_name, data_type in columns:
                    logger.info(f" - {col_name}: {data_type}")
    except Exception as exc:
        logger.error(f"❌ Gagal membuat tabel 'job_opportunities': {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    setup_job_tables()

