"""Dongeng AI curation prompt and parsing using 9Router / LLMRouter."""
import json
import logging
import re
from typing import Any

from orchestrator.llm import llm_client
from orchestrator.tools.dongeng_publisher import HARDCODED_CATEGORIES

logger = logging.getLogger("DongengPrompt")

DONGENG_SYSTEM_PROMPT = (
    "Anda kurator cerita rakyat Nusantara untuk CMS. Dari judul+deskripsi video, putuskan:\n"
    "1. skip: true jika KOMPILASI/kumpulan banyak cerita, LAGU/musik, atau bukan satu dongeng utuh; false jika satu dongeng utuh.\n"
    "2. title: judul ringkas; buang embel-embel setelah '|' atau '-'. "
    "Contoh: 'Asal Usul Kota Kendal | Cerita Rakyat' -> 'Asal Usul Kota Kendal'.\n"
    "3. category_id (string): 1=Legenda 2=Mite 3=Fabel 4=Hikayat 5=Sage 6=Parabel 7=Jenaka.\n"
    'Jawab HANYA JSON: {"skip":bool,"reason":"...","title":"...","category_id":"3"}'
)


def fallback_title(title: str) -> str:
    """Membersihkan judul secara heuristik jika LLM gagal."""
    if not title:
        return ""
    for sep in ["|", " - ", "–", "—"]:
        if sep in title:
            return title.split(sep)[0].strip()
    return title.strip()


def parse_json_loose(text: str) -> dict[str, Any] | None:
    """Parse JSON dari respon LLM dengan regex fallback."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
    return None


def curate_dongeng_video(
    title: str,
    description: str = "",
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Meminta keputusan kurasi video dari AI:
    - Apakah video single story vs kompilasi (skip: bool)
    - Judul yang telah dirapikan (title)
    - Kategori 1..7 (category_id)
    """
    clean_desc = (description or "")[:1000]
    user_content = json.dumps({"title": title, "description": clean_desc}, ensure_ascii=False)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[DONGENG-AI] Menjalankan kurasi AI (attempt {attempt}/{max_retries}) untuk '{title[:50]}'")
            resp = llm_client.generate(
                messages=[
                    {"role": "system", "content": DONGENG_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
            )

            raw_text = resp.get("content", "")
            parsed = parse_json_loose(raw_text)

            if not parsed:
                logger.warning(f"Respon AI bukan JSON valid: {repr(raw_text)[:150]}")
                continue

            skip = bool(parsed.get("skip", False))
            clean_title = str(parsed.get("title") or "").strip() or fallback_title(title)

            # Jika skip, kategori tidak perlu dipaksakan
            if skip:
                return {
                    "skip": True,
                    "reason": str(parsed.get("reason", "Kompilasi/musik terdeteksi")),
                    "title": clean_title,
                    "category_id": "0",
                    "category_name": "None",
                }

            cat_id = str(parsed.get("category_id", "3")).strip()
            if cat_id not in HARDCODED_CATEGORIES:
                cat_id = "3"  # Default Fabel jika di luar 1..7

            return {
                "skip": False,
                "reason": str(parsed.get("reason", "Dongeng utuh valid")),
                "title": clean_title,
                "category_id": cat_id,
                "category_name": HARDCODED_CATEGORIES[cat_id],
            }

        except Exception as exc:
            logger.warning(f"Panggilan kurasi LLM gagal pada attempt {attempt}: {exc}")

    # Fallback heuristik jika LLM gagal setelah retry
    logger.warning(f"Menggunakan fallback kurasi heuristik untuk '{title}'")
    return {
        "skip": False,
        "reason": "Fallback kurasi heuristik otomatis",
        "title": fallback_title(title),
        "category_id": "3",
        "category_name": HARDCODED_CATEGORIES["3"],
    }

