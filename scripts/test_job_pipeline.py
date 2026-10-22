#!/usr/bin/env python3
"""
Test End-to-End untuk Career-Ops Job Pipeline (Clara) di Punggawa.
Memvalidasi eksekusi LangGraph, evaluasi A-H, fit scoring, tailoring cover letter,
dan penyimpanan ke PostgreSQL.
"""
import os
import sys

# Ensure root directory in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orchestrator.connections import postgres_pool
from orchestrator.graphs.job_pipeline import job_graph_app

MOCK_JOB_DESC = """
Senior Backend / Agentic Systems Engineer (Remote)
Company: Nexus AI Labs
Location: Worldwide / 100% Remote
Salary: $4,000 - $6,500 / month

About the Role:
Nexus AI Labs is seeking a Senior Backend Engineer to design and scale autonomous agentic systems.
You will architect resilient event-driven pipelines, integrate LLMs (Gemini / Claude / OpenAI),
and manage distributed task queues and state machines.

Requirements:
- Strong experience with Python (FastAPI, asyncio) or Golang.
- Hands-on experience with LangGraph, LangChain, or agentic frameworks.
- Deep understanding of Redis (distributed locks, pub/sub, queues) and PostgreSQL.
- Experience with web scraping and browser automation (Playwright).
- Excellent English communication skills and ability to work asynchronously.

Benefits:
- Fully remote work policy.
- Flexible working hours.
- Health and learning stipend.
"""


def test_job_pipeline():
    print("🚀 [TEST] Memulai pengujian end-to-end Job Pipeline...")
    task_payload = {
        "task_id": "test_job_001",
        "thread_id": "test_job_thread_001",
        "task_type": "job_hunt",
        "input_data": {
            "query": "Senior Backend / Agentic Systems Engineer",
            "job_url": "https://careers.nexusailabs.io/jobs/senior-agentic-engineer",
            "raw_text": MOCK_JOB_DESC,
            "dry_run": False,
        },
    }

    print("▶ Menginvoke LangGraph job_graph_app...")
    final_state = job_graph_app.invoke(task_payload)

    print("\n✅ Eksekusi LangGraph Selesai!")
    print(f"Status: {final_state.get('status')}")
    print(f"Error: {final_state.get('error')}")
    print(f"Company: {final_state.get('company_name')}")
    print(f"Role: {final_state.get('role_title')}")

    eval_res = final_state.get("evaluation_result") or {}
    print(f"Fit Score: {eval_res.get('fit_score')}/5")
    print(f"Fit Reasoning: {eval_res.get('fit_reasoning')}")

    saved_id = final_state.get("saved_job_id")
    print(f"Saved DB ID: {saved_id}")

    reviewed = final_state.get("reviewed_application") or final_state.get("tailored_draft") or {}
    cl = reviewed.get("cover_letter", "")
    print(f"Cover Letter Length: {len(cl)} characters")
    if cl:
        print("\n--- Preview Tailored Cover Letter ---")
        print(cl[:350] + "...\n-------------------------------------")

    # Verifikasi langsung ke database PostgreSQL
    print("\n🔍 Memverifikasi data di tabel PostgreSQL 'job_opportunities'...")
    with postgres_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, company_name, role_title, fit_score, is_active, status, created_at
                FROM job_opportunities
                WHERE id = %s;
                """,
                (saved_id,),
            )
            row = cur.fetchone()
            print(f"Row di DB: {row}")
            assert row is not None, "Data loker harus tersimpan di database!"
            assert row[3] >= 3, "Fit score harus >= 3 untuk posisi yang sangat cocok ini!"
            print("🎉 Verifikasi DB Sukses 100%!")


if __name__ == "__main__":
    test_job_pipeline()
