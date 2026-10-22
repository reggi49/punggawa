"""
career_hunter.py
Core AI Intelligence & Prompt Engine untuk Punggawa Career-Ops Agent (Scout).
Fitur Unggulan:
1. Knowledge Memory Engine (Context Reuse riwayat perusahaan di PostgreSQL).
2. ATS Intelligence (Greenhouse, Lever, Ashby, Workday, dsb).
3. Dual-Scoring: Fit Score (1-5) & Job Quality Score (1-5).
4. Skill Gap Heatmap dengan estimasi waktu belajar (e.g. Terraform -> 2 minggu).
5. Comprehensive Interview Pack (Riset Perusahaan, Tech Stack, Pertanyaan Kunci, STAR+R, Negosiasi Gaji).
6. Multi-Agent Drafter-Reviewer Loop (Anti-Halusinasi).
7. Automated Follow-Up Generator.
"""
import json
import logging
import os
import re
import time
from typing import Any
from dotenv import load_dotenv
import httpx
import yaml
import google.generativeai as genai

load_dotenv()

logger = logging.getLogger("CareerHunterAI")

DEFAULT_PROFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "career_profile.yml",
)


def load_career_profile(path: str = DEFAULT_PROFILE_PATH) -> dict[str, Any]:
    """Memuat master profil dan preferensi karir kandidat dari YAML."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if data:
                    return data
        except Exception as exc:
            logger.warning(f"Gagal membaca '{path}': {exc}. Menggunakan profil default fallback.")

    return {
        "personal": {
            "name": "Kandidat",
            "email": "kandidat@example.com",
            "location": "Indonesia (Remote / Hybrid)",
        },
        "target_preferences": {
            "target_roles": ["Software Engineer", "Backend Developer", "Fullstack Developer", "AI Engineer"],
            "preferred_work_modes": ["remote", "hybrid"],
            "min_salary_usd_monthly": 1500,
        },
        "core_competencies": {
            "languages": ["Python", "Golang", "TypeScript", "SQL"],
            "frameworks_and_tools": ["FastAPI", "React", "Docker", "PostgreSQL", "Redis", "LangGraph"],
        },
        "master_cv_markdown": "Software Engineer berpengalaman dalam pengembangan backend, AI systems, dan web aplikasi.",
    }


def _call_gemini_or_ollama(prompt: str) -> str:
    """Memanggil Gemini dengan model fallback atau Ollama lokal jika diperlukan."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    ollama_url = os.getenv("OLLAMA_URL")

    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        gemini_models = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
        ]

        for model_name in gemini_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text and len(response.text.strip()) > 30:
                    return response.text.strip()
            except Exception as exc:
                logger.warning(f"Model Gemini '{model_name}' gagal: {exc}")
                time.sleep(1)

    # Fallback ke Ollama jika Gemini gagal atau API key tidak diset
    if ollama_url:
        try:
            payload = {
                "model": "qwen3.5:9b",
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 8192, "temperature": 0.3},
            }
            res = httpx.post(f"{ollama_url.rstrip('/')}/api/generate", json=payload, timeout=120.0)
            res.raise_for_status()
            return res.json().get("response", "").strip()
        except Exception as exc:
            logger.error(f"Fallback Ollama juga gagal: {exc}")

    raise RuntimeError("Gagal mengeksekusi LLM melalui Gemini maupun Ollama.")


def _clean_json_response(raw_text: str) -> dict[str, Any]:
    """Membersihkan output teks LLM menjadi dictionary JSON yang valid."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"(\{[\s\S]*\})", cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        logger.warning("Gagal mem-parsing output LLM sebagai JSON. Mengembalikan dict kosong.")
        return {}


# ==============================================================================
# KNOWLEDGE MEMORY: REUSE CONTEXT RIWAYAT PERUSAHAAN
# ==============================================================================
def get_company_memory(company_name: str) -> dict[str, Any] | None:
    """Mengambil riwayat analisis perusahaan sebelumnya dari PostgreSQL."""
    if not company_name:
        return None
    from orchestrator.connections import postgres_pool
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower().strip()).strip("-")
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, company_name, domain, ats_vendor, avg_quality_score,
                           avg_fit_score, culture_notes, tech_stack, interview_insights, jobs_reviewed_count
                    FROM company_knowledge_memory
                    WHERE id = %s OR company_name ILIKE %s
                    LIMIT 1;
                    """,
                    (slug, f"%{company_name}%"),
                )
                row = cur.fetchone()
                if row:
                    cols = [d[0] for d in cur.description]
                    return dict(zip(cols, row))
    except Exception as exc:
        logger.warning(f"Gagal mengambil memory perusahaan '{company_name}': {exc}")
    return None


def save_company_memory(
    company_name: str,
    domain: str | None,
    ats_vendor: str | None,
    quality_score: int,
    fit_score: int,
    culture_notes: str,
    tech_stack: list[str],
    interview_insights: dict[str, Any],
):
    """Menyimpan atau memperbarui memory perusahaan di PostgreSQL."""
    if not company_name:
        return
    from orchestrator.connections import postgres_pool
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower().strip()).strip("-")
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO company_knowledge_memory (
                        id, company_name, domain, ats_vendor, avg_quality_score,
                        avg_fit_score, culture_notes, tech_stack, interview_insights, jobs_reviewed_count, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, 1, NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        avg_quality_score = (company_knowledge_memory.avg_quality_score + EXCLUDED.avg_quality_score) / 2,
                        avg_fit_score = (company_knowledge_memory.avg_fit_score + EXCLUDED.avg_fit_score) / 2,
                        culture_notes = EXCLUDED.culture_notes,
                        tech_stack = EXCLUDED.tech_stack,
                        interview_insights = EXCLUDED.interview_insights,
                        jobs_reviewed_count = company_knowledge_memory.jobs_reviewed_count + 1,
                        updated_at = NOW();
                    """,
                    (
                        slug,
                        company_name,
                        domain or f"{slug}.com",
                        ats_vendor or "Custom / Career Portal",
                        quality_score,
                        fit_score,
                        culture_notes,
                        json.dumps(tech_stack),
                        json.dumps(interview_insights),
                    ),
                )
                conn.commit()
                logger.info(f"🧠 [KNOWLEDGE MEMORY] Memory perusahaan '{company_name}' berhasil disimpan/diperbarui.")
    except Exception as exc:
        logger.warning(f"Gagal menyimpan company memory '{company_name}': {exc}")


# ==============================================================================
# 1. EVALUASI MATRIX A-H, DUAL-SCORING, & SKILL GAP HEATMAP
# ==============================================================================
def evaluate_job(
    job_text: str,
    profile: dict[str, Any] | None = None,
    detected_ats: str = "Direct / Unknown",
) -> dict[str, Any]:
    """
    Mengevaluasi deskripsi lowongan kerja:
    - Dual-Scoring: Fit Score (1-5) & Job Quality Score (1-5).
    - Skill Gap Heatmap dengan estimasi waktu belajar.
    - ATS Platform Intelligence.
    - Block G Legitimacy Check.
    """
    if profile is None:
        profile = load_career_profile()

    # Ekstraksi nama perusahaan secara cepat dari teks
    comp_match = re.search(r"Company:\s*([^\n]+)", job_text, re.IGNORECASE)
    comp_name_guess = comp_match.group(1).strip() if comp_match else ""
    existing_memory = get_company_memory(comp_name_guess) if comp_name_guess else None

    memory_prompt_part = ""
    if existing_memory:
        memory_prompt_part = f"""
KNOWLEDGE MEMORY SEBELUMNYA TENTANG PERUSAHAAN INI:
- Nama: {existing_memory.get('company_name')}
- ATS Vendor Terdeteksi: {existing_memory.get('ats_vendor')}
- Kualitas Perusahaan Sebelumnya: {existing_memory.get('avg_quality_score')}/5
- Catatan Kultur & Tech: {existing_memory.get('culture_notes')}
Gunakan informasi memory di atas sebagai konteks tambahan!
"""

    prompt = f"""Kamu adalah Kepala Talent Acquisition & Career Intelligence Strategist Senior (Scout).
Tugasmu adalah menganalisis lowongan kerja secara kritis, realistis, dan jujur berdasarkan profil kandidat dan data riwayat berikut:

PROFIL KANDIDAT:
Nama: {profile.get('personal', {}).get('name', 'Kandidat')}
Lokasi: {profile.get('personal', {}).get('location', 'Indonesia')}
Target Role: {profile.get('target_preferences', {}).get('target_roles', [])}
Bahasa & Tools Utama: {profile.get('core_competencies', {}).get('languages', [])} + {profile.get('core_competencies', {}).get('frameworks_and_tools', [])}
Ringkasan CV:
{profile.get('master_cv_markdown', '')[:2000]}

ATS VENDOR TERDETEKSI: {detected_ats}
{memory_prompt_part}

DESKRIPSI LOWONGAN KERJA:
\"\"\"
{job_text[:8000]}
\"\"\"

INSTRUKSI ANALISIS:
1. INFORMASI DASAR: Perusahaan, Posisi/Role, Lokasi, Tipe Kerja (remote/hybrid/onsite), Gaji.
2. DUAL SCORING:
   a. Fit Score (1-5): Seberapa cocok profil kandidat dengan kualifikasi pekerjaan.
   b. Job Quality Score (1-5): Seberapa kredibel, stabil, dan bermutu perusahaannya (funding, reputasi, kejelasan benefit, bukan startup fiktif).
3. SKILL GAP HEATMAP:
   Daftar setiap skill teknis utama dari deskripsi loker, beri status 'matched' jika kandidat menguasai, atau 'missing' jika belum, BESERTA ESTIMASI WAKTU BELAJAR yang realistis (contoh: "1 minggu", "2-3 minggu", "1 bulan").
4. BLOCK G LEGITIMACY CHECK: Apakah loker aktif dan valid (True) atau expired/spam/ghost (False).

KEMBALIKAN HANYA FORMAT JSON MURNI:
{{
  "company_name": "Nama Perusahaan",
  "role_title": "Nama Posisi",
  "location": "Lokasi atau Remote",
  "work_mode": "remote / hybrid / onsite",
  "salary_range": "e.g. $4,000 - $6,000 / month atau Tidak Disebutkan",
  "ats_vendor": "{detected_ats}",
  "is_active": true,
  "fit_score": 4,
  "fit_reasoning": "Penjelasan 2-3 kalimat mengenai kecocokan kandidat",
  "job_quality_score": 4,
  "quality_breakdown": {{
    "company_maturity": "Mature / Well-funded Startup / Public",
    "stability_rating": "High / Medium / Low",
    "culture_summary": "Ringkasan kultur kerja dan transparansi benefit"
  }},
  "skill_gap_analysis": [
    {{
      "skill": "Python / FastAPI",
      "status": "matched",
      "importance": "high"
    }},
    {{
      "skill": "Terraform",
      "status": "missing",
      "importance": "medium",
      "estimated_learning": "2 minggu"
    }}
  ],
  "evaluation_report": {{
    "A_role_summary": "Ringkasan misi utama posisi ini",
    "B_fit_score": 4,
    "C_skills_match": {{
      "matching_skills": ["Skill1", "Skill2"],
      "missing_skills": ["SkillGap1"]
    }},
    "D_seniority_level": "Mid / Senior / Lead",
    "E_compensation_review": "Evaluasi rentang kompensasi dan kecocokan finansial",
    "F_red_flags": "Tanda bahaya kultur perusahaan (atau 'Aman')",
    "G_legitimacy_block": "Komentar keabsahan loker",
    "H_pitch_points": ["Poin jual 1", "Poin jual 2", "Poin jual 3"]
  }}
}}
"""
    raw = _call_gemini_or_ollama(prompt)
    result = _clean_json_response(raw)

    if not result.get("role_title"):
        result["role_title"] = "Tech Opportunity"
    if not result.get("company_name"):
        result["company_name"] = comp_name_guess or "Company"
    if "fit_score" not in result:
        result["fit_score"] = 3
    if "job_quality_score" not in result:
        result["job_quality_score"] = 3
    if not result.get("fit_reasoning"):
        result["fit_reasoning"] = "Evaluasi otomatis dari deskripsi pekerjaan."
    if "is_active" not in result:
        result["is_active"] = True
    if not result.get("ats_vendor"):
        result["ats_vendor"] = detected_ats

    # Simpan ke Knowledge Memory untuk context reuse masa depan
    save_company_memory(
        company_name=result.get("company_name", "Company"),
        domain=None,
        ats_vendor=result.get("ats_vendor"),
        quality_score=result.get("job_quality_score", 3),
        fit_score=result.get("fit_score", 3),
        culture_notes=result.get("quality_breakdown", {}).get("culture_summary", ""),
        tech_stack=result.get("evaluation_report", {}).get("C_skills_match", {}).get("matching_skills", []),
        interview_insights=result.get("evaluation_report", {}),
    )

    return result


# ==============================================================================
# 2. DRAFTER AGENT: TAILORED COVER LETTER & CV BULLET POINTS
# ==============================================================================
def draft_application(
    job_text: str, evaluation: dict[str, Any], profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Drafter Agent: Menghasilkan draf Cover Letter dan 3-5 bullet point resume
    yang disesuaikan dengan posisi tanpa over-claiming (anti-halusinasi).
    """
    if profile is None:
        profile = load_career_profile()

    prompt = f"""Kamu adalah Professional Resume & Cover Letter Writer kelas dunia.
Tugasmu adalah menyusun aplikasi lamaran kerja yang tajam, persuasif, to-the-point, dan ATS-optimized.

KANDIDAT:
Nama: {profile.get('personal', {}).get('name', 'Kandidat')}
CV & Pengalaman:
{profile.get('master_cv_markdown', '')[:2500]}

INFORMASI LOKER:
Posisi: {evaluation.get('role_title')} di {evaluation.get('company_name')}
Matching Skills: {evaluation.get('evaluation_report', {}).get('C_skills_match', {}).get('matching_skills', [])}
Key Pitch: {evaluation.get('evaluation_report', {}).get('H_pitch_points', [])}

DESKRIPSI LOKER:
\"\"\"
{job_text[:4000]}
\"\"\"

ATURAN PENULISAN:
1. COVER LETTER:
   - Maksimal 3-4 paragraf padat (Hook pembuka kuat, bukti pencapaian relevan, alasan tertarik pada perusahaan, call-to-action percaya diri).
   - TONE: Percaya diri, profesional, bersahabat, tanpa basa-basi klise.
   - BAHASA: Sesuaikan dengan bahasa loker (Gunakan Bahasa Inggris jika deskripsi berbahasa Inggris).
   - JANGAN MENGARANG: Jangan mengklaim pengalaman yang tidak ada di profil kandidat.
2. TAILORED CV POINTS:
   - 3 sampai 4 poin bullet pencapaian berorientasi dampak (Impact-oriented with metrics / tech stack).

KEMBALIKAN DALAM FORMAT JSON MURNI:
{{
  "cover_letter": "Isi lengkap cover letter...",
  "tailored_cv_points": [
    "Poin pencapaian 1...",
    "Poin pencapaian 2...",
    "Poin pencapaian 3..."
  ]
}}
"""
    raw = _call_gemini_or_ollama(prompt)
    result = _clean_json_response(raw)

    return {
        "cover_letter": result.get("cover_letter", "").strip(),
        "tailored_cv_points": result.get("tailored_cv_points", []),
    }


# ==============================================================================
# 3. REVIEWER AGENT: AUDIT & CRITIQUE (ANTI-HALUSINASI)
# ==============================================================================
def review_application(
    job_text: str, draft: dict[str, Any], profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Adversarial Reviewer Agent: Mengaudit draf dari Drafter Agent terhadap CV asli.
    Menghilangkan klaim palsu, memperkuat tone, dan memvalidasi keakuratan.
    """
    if profile is None:
        profile = load_career_profile()

    prompt = f"""Kamu adalah Reviewer Kritis & Auditor Lamaran Kerja.
Tugasmu adalah menguji draf cover letter dan bullet points berikut terhadap profil asli kandidat.

PROFIL KANDIDAT ASLI:
{profile.get('master_cv_markdown', '')[:2500]}

DRAF DARI DRAFTER:
Cover Letter:
{draft.get('cover_letter', '')}

Bullet Points:
{json.dumps(draft.get('tailored_cv_points', []))}

TUGAS AUDIT:
1. Cek apakah ada klaim berlebihan atau teknologi fiktif yang tidak ada di profil kandidat.
2. Perbaiki kalimat yang terdengar terlalu kaku, sombong, atau klise.
3. Pastikan tone profesional, tajam, dan siap kirim ke HR/Hiring Manager.

KEMBALIKAN HASIL VERIFIKASI AKHIR DALAM FORMAT JSON MURNI:
{{
  "reviewed_cover_letter": "Isi cover letter yang sudah diaudit dan dipoles...",
  "reviewed_cv_points": [
    "Poin terverifikasi 1",
    "Poin terverifikasi 2",
    "Poin terverifikasi 3"
  ],
  "review_notes": "Catatan singkat review (misal: 'Semua klaim akurat dan selaras dengan CV')"
}}
"""
    raw = _call_gemini_or_ollama(prompt)
    result = _clean_json_response(raw)

    return {
        "cover_letter": result.get("reviewed_cover_letter") or draft.get("cover_letter", ""),
        "tailored_cv_points": result.get("reviewed_cv_points") or draft.get("tailored_cv_points", []),
        "review_notes": result.get("review_notes", "Verified by Reviewer Agent"),
    }


# ==============================================================================
# 4. COMPREHENSIVE INTERVIEW PACK & NEGOTIATION
# ==============================================================================
def generate_interview_pack(
    job_text: str, evaluation: dict[str, Any], profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Menghasilkan Comprehensive Interview Pack:
    1. Riset Mendalam Perusahaan & Produk.
    2. Bedah Tech Stack & Arsitektur yang Dibutuhkan.
    3. Pertanyaan Teknis & Kultural yang Paling Mungkin Ditanyakan.
    4. 3 Skenario Latihan STAR+R.
    5. Panduan & Taktik Negosiasi Gaji (Salary Benchmark).
    """
    if profile is None:
        profile = load_career_profile()

    prompt = f"""Kamu adalah Executive Interview Coach & Salary Negotiation Strategist.
Berdasarkan lowongan kerja dan profil kandidat berikut, buatkan paket persiapan wawancara komprehensif:

POSISI: {evaluation.get('role_title')} di {evaluation.get('company_name')}
KANDIDAT:
{profile.get('master_cv_markdown', '')[:2000]}

DESKRIPSI LOWONGAN:
\"\"\"
{job_text[:4000]}
\"\"\"

KEMBALIKAN DALAM FORMAT JSON MURNI:
{{
  "company_research": "Ringkasan model bisnis perusahaan, produk unggulan, dan arah teknologinya",
  "tech_stack_breakdown": ["Komponen arsitektur 1", "Komponen 2", "Komponen 3"],
  "salary_negotiation_notes": "Strategi negosiasi gaji berdasarkan pasar, baseline target kandidat, dan nilai tawar",
  "likely_questions": [
    "Pertanyaan teknis/arsitektur 1...",
    "Pertanyaan teknis/arsitektur 2...",
    "Pertanyaan cultural/leadership 3..."
  ],
  "star_scenarios": [
    {{
      "question": "Pertanyaan wawancara...",
      "competency_tested": "Keahlian yang diuji",
      "situation": "Konteks proyek nyata dari CV",
      "task": "Tantangan yang dihadapi",
      "action": "Langkah nyata yang diambil",
      "result": "Hasil atau metrik keberhasilan",
      "reflection": "Pelajaran yang didapat"
    }}
  ]
}}
"""
    raw = _call_gemini_or_ollama(prompt)
    result = _clean_json_response(raw)
    return result


# ==============================================================================
# 5. AUTOMATED FOLLOW-UP EMAIL GENERATOR
# ==============================================================================
def generate_follow_up_email(
    company_name: str,
    role_title: str,
    candidate_name: str = "Reggi",
    days_elapsed: int = 14,
) -> str:
    """Menghasilkan draf email follow-up yang sopan, profesional, dan efektif."""
    prompt = f"""Buatkan draf email follow-up lamaran kerja yang sopan, percaya diri, dan profesional.
Kandidat: {candidate_name}
Posisi yang dilamar: {role_title}
Perusahaan: {company_name}
Waktu berlalu sejak lamaran/interview terakhir: {days_elapsed} hari tanpa kabar.

Format yang diharapkan:
Subject: ...
Body: ... (Maksimal 2-3 paragraf ringkas, menunjukkan antusiasme, menegaskan nilai tambah kandidat, dan menanyakan kabar proses rekrutmen secara elegan).
Gunakan Bahasa Inggris jika posisi umumnya internasional, atau sesuaikan dengan gaya profesional."""
    return _call_gemini_or_ollama(prompt)
