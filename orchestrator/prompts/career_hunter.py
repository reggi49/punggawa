"""
career_hunter.py
Core AI Intelligence & Prompt Engine untuk Punggawa Career-Ops Agent.
Mengadopsi Framework Evaluasi A-H, Rubrik Fit Scoring (1-5), Block G Legitimacy Check,
Drafter-Reviewer Agent Loop, dan STAR+R Interview Prep dari Career-Ops.
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
    # Hapus markdown codeblocks jika ada
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception:
        # Coba cari pola {...} pertama dan terakhir
        match = re.search(r"(\{[\s\S]*\})", cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        logger.warning("Gagal mem-parsing output LLM sebagai JSON. Mengembalikan dict kosong.")
        return {}


# ==============================================================================
# 1. EVALUASI MATRIX A-H & FIT SCORING (1-5)
# ==============================================================================
def evaluate_job(job_text: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Mengevaluasi deskripsi lowongan kerja berdasarkan matriks A-H Career-Ops:
    A: Role Summary
    B: Fit Scoring (1-5) & Detail Reasoning
    C: Skills Match Matrix (Matching vs Missing)
    D: Seniority Strategy
    E: Compensation & Location Match
    F: Culture & Red Flags
    G: Block G Legitimacy Check (Aktif vs Ghost Job)
    H: Key Pitch Points
    """
    if profile is None:
        profile = load_career_profile()

    prompt = f"""Kamu adalah Kepala Talent Acquisition & Career Strategist Senior.
Tugasmu adalah menganalisis deskripsi lowongan kerja secara kritis, realistis, dan jujur berdasarkan profil kandidat berikut:

PROFIL KANDIDAT:
Nama: {profile.get('personal', {}).get('name', 'Kandidat')}
Lokasi: {profile.get('personal', {}).get('location', 'Indonesia')}
Target Role: {profile.get('target_preferences', {}).get('target_roles', [])}
Preferensi Kerja: {profile.get('target_preferences', {}).get('preferred_work_modes', ['remote'])}
Bahasa & Tools Utama: {profile.get('core_competencies', {}).get('languages', [])} + {profile.get('core_competencies', {}).get('frameworks_and_tools', [])}
Ringkasan CV:
{profile.get('master_cv_markdown', '')[:2000]}

DESKRIPSI LOWONGAN KERJA:
\"\"\"
{job_text[:8000]}
\"\"\"

Lakukan evaluasi menyeluruh berdasarkan Framework Matriks A-H Career-Ops:
1. Ekstraksi Informasi Dasar: Perusahaan, Posisi/Role, Lokasi, Tipe Kerja (remote/hybrid/onsite), Rentang Gaji (jika ada).
2. Block G Legitimacy Check: Apakah loker ini sah dan sedang aktif? (True jika aktif, False jika terdeteksi expired/tutup/spam/ghost).
3. Fit Scoring (Skala 1 sampai 5):
   - 5 = Sangat Cocok (>85% skill cocok, remote/lokasi sesuai, relevan dengan pengalaman utama).
   - 4 = Cocok Tinggi (Hanya butuh penyesuaian minor, skill esensial terpenuhi).
   - 3 = Cukup Cocok (Ada skill gap yang realistis bisa dipelajari).
   - 2 = Kurang Cocok (Beda domain, butuh tahun pengalaman jauh lebih tinggi, atau kendala lokasi on-site).
   - 1 = Tidak Cocok Sama Sekali.
4. Matriks A-H Evaluasi Lengkap.

KEMBALIKAN HANYA FORMAT JSON MURNI TANPA PENJELASAN LAIN:
{{
  "company_name": "Nama Perusahaan",
  "role_title": "Nama Posisi",
  "location": "Lokasi atau Remote",
  "work_mode": "remote / hybrid / onsite",
  "salary_range": "e.g. $4,000 - $6,000 / month atau Tidak Disebutkan",
  "is_active": true,
  "fit_score": 4,
  "fit_reasoning": "Penjelasan singkat 2-3 kalimat mengapa mendapat skor ini",
  "evaluation_report": {{
    "A_role_summary": "Ringkasan misi utama posisi ini",
    "B_fit_score": 4,
    "C_skills_match": {{
      "matching_skills": ["Skill1", "Skill2"],
      "missing_skills": ["SkillGap1"]
    }},
    "D_seniority_level": "Mid / Senior / Lead",
    "E_compensation_review": "Evaluasi rentang kompensasi dan kecocokan finansial",
    "F_red_flags": "Tanda bahaya atau catatan kultur perusahaan (jika ada, atau 'Aman')",
    "G_legitimacy_block": "Komentar keabsahan loker",
    "H_pitch_points": ["Poin jual 1", "Poin jual 2", "Poin jual 3"]
  }}
}}
"""
    raw = _call_gemini_or_ollama(prompt)
    result = _clean_json_response(raw)

    # Validasi fallback
    if not result.get("role_title"):
        result["role_title"] = "Tech Opportunity"
    if not result.get("company_name"):
        result["company_name"] = "Company"
    if "fit_score" not in result:
        result["fit_score"] = 3
    if not result.get("fit_reasoning"):
        result["fit_reasoning"] = "Evaluasi otomatis dari deskripsi pekerjaan."
    if "is_active" not in result:
        result["is_active"] = True

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
   - TONE: Percaya diri, profesional, bersahabat, tanpa basa-basi klise seperti "I am writing to express my interest...".
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
# 4. STAR+R INTERVIEW PREPARATION
# ==============================================================================
def generate_interview_prep(
    job_text: str, evaluation: dict[str, Any], profile: dict[str, Any] | None = None
) -> list[dict[str, str]]:
    """
    Menghasilkan 3 skenario latihan wawancara STAR+R (Situation, Task, Action, Result, Reflection)
    berdasarkan kebutuhan khusus posisi ini.
    """
    if profile is None:
        profile = load_career_profile()

    prompt = f"""Kamu adalah Executive Interview Coach.
Berdasarkan lowongan kerja dan profil kandidat berikut, buatkan 3 pertanyaan wawancara teknis/perilaku yang paling mungkin ditanyakan, lengkap dengan panduan jawaban berformat STAR+R.

POSISI: {evaluation.get('role_title')} di {evaluation.get('company_name')}
KANDIDAT:
{profile.get('master_cv_markdown', '')[:2000]}

KEMBALIKAN DALAM FORMAT JSON MURNI:
{{
  "scenarios": [
    {{
      "question": "Pertanyaan wawancara...",
      "competency_tested": "Keahlian / kompetensi yang diuji",
      "situation": "Konteks proyek nyata dari CV kandidat",
      "task": "Tantangan atau tanggung jawab yang dihadapi",
      "action": "Langkah nyata yang diambil dengan tools/teknologi",
      "result": "Hasil konkret atau metrik keberhasilan",
      "reflection": "Pelajaran penting yang didapat"
    }}
  ]
}}
"""
    raw = _call_gemini_or_ollama(prompt)
    result = _clean_json_response(raw)
    return result.get("scenarios", [])
