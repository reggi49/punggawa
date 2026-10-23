"""
job_pipeline.py
LangGraph Sequential Assembly Line Pipeline untuk Career Intelligence Lead (Scout).
Fitur Unggulan:
1. ATS Intelligence (Greenhouse, Lever, Ashby, Workday, dsb).
2. Dual-Scoring: Candidate Fit Score (1-5) & Job Quality Score (1-5).
3. Skill Gap Heatmap dengan estimasi waktu belajar (e.g. Terraform -> 2 minggu).
4. Multi-Agent Drafter-Reviewer Loop (Anti-Halusinasi).
5. Comprehensive Interview Pack (Riset Perusahaan, Tech Stack, STAR+R, Negosiasi Gaji).
6. Automated Follow-Up Generator.
7. Knowledge Memory Integration (PostgreSQL context reuse).
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Literal, TypedDict
from langgraph.graph import END, StateGraph

from config.settings import settings
from orchestrator.connections import postgres_pool
from orchestrator.events import agent_node_tracker
from orchestrator.prompts.career_hunter import (
    draft_application,
    evaluate_job,
    generate_interview_pack,
    generate_follow_up_email,
    load_career_profile,
    review_application,
)
from orchestrator.tools.job_scraper import (
    detect_ats_vendor,
    fetch_job_from_url,
    generate_job_hash,
    search_remote_jobs,
)

logger = logging.getLogger("JobPipeline")


class JobAgentState(TypedDict, total=False):
    task_id: str
    thread_id: str
    task_type: str
    status: str
    input_data: dict[str, Any]
    error: str | None
    execution_logs: list[str]

    # Career-Ops & Scout Payload
    job_url: str | None
    raw_content: str | None
    company_name: str | None
    role_title: str | None
    ats_vendor: str | None
    evaluation_result: dict[str, Any] | None
    tailored_draft: dict[str, Any] | None
    reviewed_application: dict[str, Any] | None
    interview_pack: dict[str, Any] | None
    follow_up_draft: str | None
    saved_job_id: str | None
    result: dict[str, Any] | None


@agent_node_tracker("ingest_job_node", "Mempersiapkan target analisis lowongan kerja")
def ingest_job_node(state: JobAgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    input_data = state.get("input_data") or {}
    timestamp = datetime.now(timezone.utc).isoformat()

    url = (
        input_data.get("job_url")
        or input_data.get("url")
        or input_data.get("query")
        or state.get("job_url")
        or ""
    )
    raw_text = input_data.get("raw_text") or input_data.get("job_description") or ""
    detected_ats = detect_ats_vendor(url, raw_text)

    logger.info(f"[{settings.WORKER_ID}] Scout ingesting job: {task_id} (URL='{url}', ATS='{detected_ats}')")

    return {
        "status": "processing",
        "task_type": "job_hunt",
        "job_url": url.strip() if url.startswith("http") else None,
        "raw_content": raw_text.strip() if raw_text else None,
        "ats_vendor": detected_ats,
        "execution_logs": [f"[{timestamp}] Scout menerima target loker: {task_id}. ATS terdeteksi: '{detected_ats}'."],
        "error": None,
    }


@agent_node_tracker("fetch_job_node", "Mengunduh dan mengekstrak deskripsi lowongan kerja")
def fetch_job_node(state: JobAgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    url = state.get("job_url")
    raw_content = state.get("raw_content")
    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Jika pengguna memberikan teks langsung
    if raw_content and len(raw_content) > 100:
        logger.info(f"Menggunakan deskripsi loker dari teks input langsung ({len(raw_content)} karakter).")
        return {
            "execution_logs": [f"[{timestamp}] Deskripsi pekerjaan langsung dimuat dari input data ({len(raw_content)} karakter)."],
            "error": None,
        }

    # 2. Jika ada URL langsung, scrape URL tersebut
    if url and url.startswith("http"):
        try:
            scraped = fetch_job_from_url(url, job_id=task_id)
            if scraped.get("hitl_triggered"):
                blocker = scraped.get("blocker_type", "UNKNOWN_BLOCKER")
                logger.warning(f"[{task_id}] Clara dijeda karena butuh intervensi manusia: {blocker}")
                return {
                    "status": "PAUSED_HITL",
                    "error": f"Task dijeda: Terdeteksi {blocker}. Membutuhkan intervensi pengguna.",
                    "execution_logs": [
                        f"[{timestamp}] 🚨 HITL TRIGGERED: Terdeteksi {blocker}. Notifikasi bantuan dikirim. Task dijeda."
                    ],
                }

            text = scraped.get("raw_text", "")
            ats = scraped.get("ats_vendor") or state.get("ats_vendor") or "Direct / Unknown"
            if len(text) < 100:
                raise ValueError("Konten teks dari URL terlalu pendek atau diproteksi bot.")

            logger.info(f"Berhasil scrape lowongan dari URL ({len(text)} karakter, ATS={ats}).")
            return {
                "raw_content": text,
                "ats_vendor": ats,
                "execution_logs": [f"[{timestamp}] Berhasil scrape URL '{url}' (ATS: {ats}, {len(text)} karakter)."],
                "error": None,
            }
        except Exception as exc:
            err_msg = f"Gagal mengekstrak deskripsi dari URL '{url}': {exc}"
            logger.error(err_msg)
            return {
                "status": "failed",
                "error": err_msg,
                "execution_logs": [f"[{timestamp}] Scrape gagal: {err_msg}"],
            }

    # 3. Jika tidak ada URL langsung, jalankan auto-scout remote jobs
    logger.info("URL tidak diberikan, menjalankan auto-scouting lowongan remote via RemoteOK...")
    profile = load_career_profile()
    keywords = profile.get("core_competencies", {}).get("languages", ["python", "golang", "react"])
    remote_jobs = search_remote_jobs(keywords=keywords, limit=1)

    if not remote_jobs:
        err_msg = "Tidak ada URL lowongan yang diberikan dan pencarian remote tidak menghasilkan data."
        logger.error(err_msg)
        return {
            "status": "failed",
            "error": err_msg,
            "execution_logs": [f"[{timestamp}] {err_msg}"],
        }

    first_job = remote_jobs[0]
    return {
        "job_url": first_job.get("job_url"),
        "raw_content": first_job.get("description"),
        "company_name": first_job.get("company_name"),
        "role_title": first_job.get("role_title"),
        "ats_vendor": "RemoteOK Board",
        "execution_logs": [
            f"[{timestamp}] Auto-scout menemukan loker: '{first_job.get('role_title')}' di {first_job.get('company_name')}."
        ],
        "error": None,
    }


@agent_node_tracker("evaluate_fit_node", "Menganalisis matriks A-H, dual scoring, dan skill gap heatmap")
def evaluate_fit_node(state: JobAgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    raw_content = state.get("raw_content") or ""
    detected_ats = state.get("ats_vendor") or "Direct / Unknown"
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(f"[{settings.WORKER_ID}] Scout mengevaluasi kecocokan loker dengan profil kandidat...")
    profile = load_career_profile()
    eval_res = evaluate_job(raw_content, profile, detected_ats=detected_ats)

    fit_score = eval_res.get("fit_score", 1)
    job_quality = eval_res.get("job_quality_score", 3)
    is_active = eval_res.get("is_active", True)
    company = eval_res.get("company_name", "Company")
    role = eval_res.get("role_title", "Position")

    logger.info(
        f"✅ Hasil Evaluasi Scout: {company} - {role} | Fit Score: {fit_score}/5 | Job Quality: {job_quality}/5 | ATS: {detected_ats}"
    )

    return {
        "company_name": company,
        "role_title": role,
        "ats_vendor": eval_res.get("ats_vendor", detected_ats),
        "evaluation_result": eval_res,
        "execution_logs": [
            f"[{timestamp}] Evaluasi A-H selesai: Fit Score {fit_score}/5, Job Quality {job_quality}/5 (ATS: {eval_res.get('ats_vendor')}). Active={is_active}."
        ],
        "error": None,
    }


def route_after_fetch(state: JobAgentState) -> Literal["evaluate_fit_node", "complete_node"]:
    """Conditional Edge: Memilih rute setelah fetch. Jika HITL terpicu atau scrape gagal, langsung ke complete_node."""
    if state.get("status") in ["PAUSED_HITL", "failed"] or state.get("error"):
        return "complete_node"
    return "evaluate_fit_node"


def route_after_evaluation(state: JobAgentState) -> Literal["draft_application_node", "save_job_node", "complete_node"]:
    """Conditional Edge: Memilih rute berdasarkan keaktifan dan skor kecocokan."""
    if state.get("status") == "failed" or state.get("error"):
        return "complete_node"

    eval_res = state.get("evaluation_result") or {}
    is_active = eval_res.get("is_active", True)
    fit_score = eval_res.get("fit_score", 1)

    if not is_active:
        logger.info(f"Loker terdeteksi tidak aktif (Block G: expired/ghost job). Melewati tailoring.")
        return "complete_node"

    if fit_score < 3:
        logger.info(f"Fit score ({fit_score}/5) di bawah batas minimum (3). Melewati pembuatan draf.")
        return "save_job_node"

    return "draft_application_node"


@agent_node_tracker("draft_application_node", "Drafter Agent: Menulis cover letter dan poin pencapaian tailored")
def draft_application_node(state: JobAgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    raw_content = state.get("raw_content") or ""
    eval_res = state.get("evaluation_result") or {}
    company = state.get("company_name") or eval_res.get("company_name", "Company")
    role = state.get("role_title") or eval_res.get("role_title", "Position")
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(f"[{settings.WORKER_ID}] Drafter Agent menyusun Cover Letter & CV points...")
    profile = load_career_profile()
    draft = draft_application(raw_content, eval_res, profile)

    follow_up = generate_follow_up_email(
        company_name=company,
        role_title=role,
        candidate_name=profile.get("personal", {}).get("name", "Reggi"),
        days_elapsed=14,
    )

    return {
        "tailored_draft": draft,
        "follow_up_draft": follow_up,
        "execution_logs": [
            f"[{timestamp}] Drafter Agent selesai menyusun draf Cover Letter ({len(draft.get('cover_letter', ''))} karakter) dan Follow-up template."
        ],
        "error": None,
    }


@agent_node_tracker("review_critique_node", "Reviewer Agent: Mengaudit draf terhadap CV asli (anti-halusinasi)")
def review_critique_node(state: JobAgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    raw_content = state.get("raw_content") or ""
    draft = state.get("tailored_draft") or {}
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(f"[{settings.WORKER_ID}] Reviewer Agent memvalidasi draf aplikasi...")
    profile = load_career_profile()
    reviewed = review_application(raw_content, draft, profile)

    return {
        "reviewed_application": reviewed,
        "execution_logs": [
            f"[{timestamp}] Reviewer Agent memvalidasi draf: {reviewed.get('review_notes', 'Approved')}."
        ],
        "error": None,
    }


@agent_node_tracker("generate_prep_node", "Menyusun Comprehensive Interview Pack & Taktik Negosiasi")
def generate_prep_node(state: JobAgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    raw_content = state.get("raw_content") or ""
    eval_res = state.get("evaluation_result") or {}
    fit_score = eval_res.get("fit_score", 1)
    timestamp = datetime.now(timezone.utc).isoformat()

    pack = {}
    if fit_score >= 3:
        logger.info(f"[{settings.WORKER_ID}] Menyusun Comprehensive Interview Pack (Riset, Arsitektur, STAR+R, Gaji)...")
        profile = load_career_profile()
        pack = generate_interview_pack(raw_content, eval_res, profile)

    return {
        "interview_pack": pack,
        "execution_logs": [
            f"[{timestamp}] Interview Pack siap: {len(pack.get('likely_questions', []))} pertanyaan prediksi, {len(pack.get('star_scenarios', []))} STAR+R skenario."
        ],
        "error": None,
    }


@agent_node_tracker("save_job_node", "Menyimpan data lowongan, dual scoring, dan materi ke PostgreSQL")
def save_job_node(state: JobAgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    job_url = state.get("job_url") or f"https://manual-entry/{task_id}"
    company = state.get("company_name") or "Company"
    role = state.get("role_title") or "Position"
    raw_content = state.get("raw_content") or ""
    eval_res = state.get("evaluation_result") or {}
    reviewed = state.get("reviewed_application") or state.get("tailored_draft") or {}
    interview_pack = state.get("interview_pack") or {}
    follow_up_draft = state.get("follow_up_draft")
    timestamp = datetime.now(timezone.utc).isoformat()

    job_id = generate_job_hash(company, role, job_url)
    fit_score = eval_res.get("fit_score", 1)
    job_quality_score = eval_res.get("job_quality_score", 3)
    fit_reasoning = eval_res.get("fit_reasoning", "Evaluasi otomatis Career-Ops")
    work_mode = eval_res.get("work_mode", "remote")
    location = eval_res.get("location", "Remote")
    salary = eval_res.get("salary_range", "Tidak Disebutkan")
    ats_vendor = state.get("ats_vendor") or eval_res.get("ats_vendor", "Direct / Unknown")
    is_active = eval_res.get("is_active", True)
    cover_letter = reviewed.get("cover_letter")
    cv_points = reviewed.get("tailored_cv_points") or []
    quality_breakdown = eval_res.get("quality_breakdown", {})
    skill_gaps = eval_res.get("skill_gap_analysis", [])

    status_app = "shortlisted" if fit_score >= 4 else "evaluated"

    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO job_opportunities (
                        id, job_url, company_name, role_title, location, work_mode, salary_range,
                        job_description, fit_score, fit_reasoning, evaluation_report, is_active,
                        tailored_cover_letter, tailored_cv_points, interview_star_prep, status,
                        ats_vendor, job_quality_score, quality_breakdown, skill_gap_analysis,
                        interview_pack, follow_up_draft, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s::jsonb, %s,
                        %s, %s::jsonb, %s::jsonb, %s,
                        %s, %s, %s::jsonb, %s::jsonb,
                        %s::jsonb, %s, NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        fit_score = EXCLUDED.fit_score,
                        job_quality_score = EXCLUDED.job_quality_score,
                        fit_reasoning = EXCLUDED.fit_reasoning,
                        evaluation_report = EXCLUDED.evaluation_report,
                        is_active = EXCLUDED.is_active,
                        tailored_cover_letter = EXCLUDED.tailored_cover_letter,
                        tailored_cv_points = EXCLUDED.tailored_cv_points,
                        interview_star_prep = EXCLUDED.interview_star_prep,
                        ats_vendor = EXCLUDED.ats_vendor,
                        quality_breakdown = EXCLUDED.quality_breakdown,
                        skill_gap_analysis = EXCLUDED.skill_gap_analysis,
                        interview_pack = EXCLUDED.interview_pack,
                        follow_up_draft = EXCLUDED.follow_up_draft,
                        status = EXCLUDED.status,
                        updated_at = NOW();
                    """,
                    (
                        job_id,
                        job_url,
                        company,
                        role,
                        location,
                        work_mode,
                        salary,
                        raw_content[:8000],
                        fit_score,
                        fit_reasoning,
                        json.dumps(eval_res.get("evaluation_report", {})),
                        is_active,
                        cover_letter,
                        json.dumps(cv_points),
                        json.dumps(interview_pack.get("star_scenarios", [])),
                        status_app,
                        ats_vendor,
                        job_quality_score,
                        json.dumps(quality_breakdown),
                        json.dumps(skill_gaps),
                        json.dumps(interview_pack),
                        follow_up_draft,
                    ),
                )
                conn.commit()
                logger.info(f"✅ Lowongan '{job_id}' berhasil disimpan di PostgreSQL (Fit: {fit_score}/5, Quality: {job_quality_score}/5, ATS: {ats_vendor}).")
    except Exception as exc:
        logger.error(f"Gagal menyimpan lowongan ke database: {exc}", exc_info=True)

    return {
        "saved_job_id": job_id,
        "execution_logs": [f"[{timestamp}] Lowongan berhasil disimpan ke PostgreSQL dengan ID='{job_id}'."],
        "error": None,
    }


def complete_node(state: JobAgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    timestamp = datetime.now(timezone.utc).isoformat()

    # Periksa jika task sedang dijeda untuk Human-in-the-Loop (HITL)
    if state.get("status") == "PAUSED_HITL":
        logger.info(f"[{task_id}] Job pipeline memasuki status PAUSED_HITL.")
        return {
            "status": "PAUSED_HITL",
            "result": {
                "job_id": state.get("task_id"),
                "status": "PAUSED_HITL",
                "summary": state.get("error", "Task dijeda untuk intervensi manusia (HITL)."),
            },
            "execution_logs": [f"[{timestamp}] Job Task {task_id} dijeda (PAUSED_HITL). Menunggu sinyal resume."],
        }

    status = "completed" if not state.get("error") else "failed"
    company = state.get("company_name", "Unknown")
    role = state.get("role_title", "Job")
    eval_res = state.get("evaluation_result") or {}
    fit_score = eval_res.get("fit_score", 1)
    quality_score = eval_res.get("job_quality_score", 3)
    ats = state.get("ats_vendor", "Direct")
    saved_id = state.get("saved_job_id")

    summary = (
        f"Scout Career Intelligence Selesai: {company} - {role} "
        f"(Fit: {fit_score}/5, Quality: {quality_score}/5, ATS: {ats}). "
        f"Tersimpan di DB: {saved_id or 'N/A'}."
    )
    if state.get("error"):
        summary = f"Scout Gagal: {state.get('error')}"

    return {
        "status": status,
        "result": {
            "job_id": saved_id,
            "company_name": company,
            "role_title": role,
            "fit_score": fit_score,
            "job_quality_score": quality_score,
            "ats_vendor": ats,
            "fit_reasoning": eval_res.get("fit_reasoning"),
            "summary": summary,
            "status": status,
        },
        "execution_logs": [f"[{timestamp}] Job Task {task_id} selesai dengan status={status}."],
    }


def build_job_graph() -> StateGraph:
    """Merakit alur sekuensial LangGraph untuk kurasi dan analisis Career Intelligence (Scout)."""
    workflow = StateGraph(JobAgentState)

    workflow.add_node("ingest_job_node", ingest_job_node)
    workflow.add_node("fetch_job_node", fetch_job_node)
    workflow.add_node("evaluate_fit_node", evaluate_fit_node)
    workflow.add_node("draft_application_node", draft_application_node)
    workflow.add_node("review_critique_node", review_critique_node)
    workflow.add_node("generate_prep_node", generate_prep_node)
    workflow.add_node("save_job_node", save_job_node)
    workflow.add_node("complete_node", complete_node)

    workflow.set_entry_point("ingest_job_node")
    workflow.add_edge("ingest_job_node", "fetch_job_node")
    workflow.add_conditional_edges(
        "fetch_job_node",
        route_after_fetch,
        {
            "evaluate_fit_node": "evaluate_fit_node",
            "complete_node": "complete_node",
        },
    )

    workflow.add_conditional_edges(
        "evaluate_fit_node",
        route_after_evaluation,
        {
            "draft_application_node": "draft_application_node",
            "save_job_node": "save_job_node",
            "complete_node": "complete_node",
        },
    )

    workflow.add_edge("draft_application_node", "review_critique_node")
    workflow.add_edge("review_critique_node", "generate_prep_node")
    workflow.add_edge("generate_prep_node", "save_job_node")
    workflow.add_edge("save_job_node", "complete_node")
    workflow.add_edge("complete_node", END)

    return workflow


job_graph_app = build_job_graph().compile()
