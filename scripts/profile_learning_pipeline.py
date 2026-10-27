#!/usr/bin/env python3
"""
profile_learning_pipeline.py
Profile Evolution Engine untuk Punggawa Career-Ops (Scout).
Mirip perintah /expand pada ai-job-search & Career-Ops:
Menganalisis repository GitHub, proyek lokal, atau catatan sertifikat baru,
mengekstrak kompetensi teknis & pencapaian kuantitatif,
lalu memperbarui config/career_profile.yml secara otomatis.
"""
import argparse
import json
import logging
import os
import sys
import yaml

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orchestrator.prompts.career_hunter import (
    _call_gemini_or_ollama,
    _clean_json_response,
    load_career_profile,
    DEFAULT_PROFILE_PATH,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ProfileEvolutionEngine")


def enrich_profile_from_text(
    input_text: str, profile_path: str = DEFAULT_PROFILE_PATH
) -> dict:
    """Menganalisis teks baru (proyek, sertifikat, codebase) dan memperkaya career_profile.yml."""
    current_profile = load_career_profile(profile_path)

    prompt = f"""Kamu adalah Career Profile Evolution Engine untuk AI Agent.
Tugasmu adalah menganalisis data proyek baru, pencapaian baru, atau repositori berikut,
lalu memperkaya profil kandidat agar penilaian lowongan kerja tetap akurat dan mutakhir.

PROFIL KANDIDAT SAAT INI:
Languages: {(current_profile.get('core_competencies') or {}).get('languages', [])}
Frameworks/Tools: {(current_profile.get('core_competencies') or {}).get('frameworks_and_tools', [])}
Specialties: {(current_profile.get('core_competencies') or {}).get('specialties', [])}
CV Summary:
{current_profile.get('master_cv_markdown', '')[:1500]}

UPDATE / CATATAN PROYEK BARU:
\"\"\"
{input_text[:6000]}
\"\"\"

INSTRUKSI ENRICHMENT:
1. Ekstraksi bahasa pemrograman, tools, framework, arsitektur baru yang terbukti digunakan.
2. Gabungkan dengan kompetensi yang sudah ada (jangan hapus keahlian lama yang masih relevan).
3. Buat pembaruan ringkasan CV (tambahkan proyek baru dengan poin-poin pencapaian yang terukur).

KEMBALIKAN DALAM FORMAT JSON MURNI:
{{
  "added_languages": ["LangBaru1"],
  "added_tools": ["ToolBaru1", "ToolBaru2"],
  "added_specialties": ["SpecialtyBaru"],
  "updated_languages": ["Daftar gabungan lengkap..."],
  "updated_tools": ["Daftar gabungan lengkap..."],
  "updated_specialties": ["Daftar gabungan lengkap..."],
  "enriched_cv_markdown": "Markdown CV lengkap yang sudah memuat proyek baru..."
}}
"""
    logger.info("🧠 Menjalankan LLM untuk mengevaluasi evolusi profil...")
    raw = _call_gemini_or_ollama(prompt)
    enriched = _clean_json_response(raw)

    if not enriched or not enriched.get("updated_tools"):
        logger.warning("Gagal menghasilkan pembaruan profil yang valid.")
        return current_profile

    # Update current profile structure
    current_profile.setdefault("core_competencies", {})
    if enriched.get("updated_languages"):
        current_profile["core_competencies"]["languages"] = enriched["updated_languages"]
    if enriched.get("updated_tools"):
        current_profile["core_competencies"]["frameworks_and_tools"] = enriched["updated_tools"]
    if enriched.get("updated_specialties"):
        current_profile["core_competencies"]["specialties"] = enriched["updated_specialties"]
    if enriched.get("enriched_cv_markdown"):
        current_profile["master_cv_markdown"] = enriched["enriched_cv_markdown"]

    # Simpan kembali ke file YAML
    try:
        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.dump(current_profile, f, sort_keys=False, allow_unicode=True, indent=2)
        logger.info(f"✅ Profil berhasil diperbarui di: {profile_path}")
        logger.info(f"   + Added Languages: {enriched.get('added_languages', [])}")
        logger.info(f"   + Added Tools: {enriched.get('added_tools', [])}")
    except Exception as exc:
        logger.error(f"Gagal menulis pembaruan profil ke {profile_path}: {exc}")

    return current_profile


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile Evolution Engine (Scout / Career-Ops)")
    parser.add_argument("--text", type=str, help="Catatan teks proyek / sertifikat / portfolio baru")
    parser.add_argument("--file", type=str, help="Path ke file teks/markdown proyek")
    args = parser.parse_args()

    content = ""
    if args.file and os.path.exists(args.file):
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    elif args.text:
        content = args.text
    else:
        # Default demo expansion
        content = """
        Baru saja menyelesaikan implementasi production-ready:
        - Orchestrator multi-agent menggunakan LangGraph, Celery/Redis Distributed Queue, dan SSE Starlette.
        - Kubernetes deployment dengan Helm charts, Terraform IAC untuk AWS ECS, dan Docker multi-stage builds.
        - Automated ATS Detection dan Fit Scoring Engine dengan Playwright dan Scrapling.
        """

    enrich_profile_from_text(content)

