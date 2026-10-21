"""Writer prompts for Dual-Language (ID & EN) article generation and regex parsing."""
import json
import re
import uuid
from typing import Any


def get_id_prompt(topic: str, context: str, url_references: str) -> str:
    """Prompt terstruktur untuk artikel Bahasa Indonesia yang mendalam, anti em-dash, dan berbasis fakta."""
    return f"""Anda adalah jurnalis teknologi senior dan software engineer berpengalaman untuk platform KodePintar.
Tugas Anda adalah menulis artikel analisis mendalam dalam Bahasa Indonesia berdasarkan fakta dari materi referensi di bawah ini.

TOPIK: {topic}

MATERI REFERENSI:
{context}

SUMBER REFERENSI:
{url_references}

ATURAN PENULISAN SANGAT KETAT:
1. ANTI EM-DASH: JANGAN PERNAH menggunakan karakter em-dash (—) atau en-dash (–) di seluruh artikel. Gunakan tanda koma, titik dua, tanda kurung, atau titik.
2. ZERO HALLUCINATION: Hanya tulis fakta, angka, dan fitur yang benar-benar ada di materi referensi. Jangan mengarang fitur.
3. STOPPING-POWER HEADLINE: Judul harus memikat, bernas, dan profesional (maksimal 70 karakter).
4. STRUKTUR ARTIKEL (Gunakan Markdown):
   - Hook pembuka yang kuat
   - Latar belakang & urgensi
   - Rincian fitur teknis / pembaruan utama
   - Tabel perbandingan jika relevan (format Markdown table)
   - Code snippet singkat jika topiknya tentang pemrograman/teknologi
   - Kesimpulan dan dampaknya bagi developer/industri
   - Bagian penutup mencantumkan sumber referensi
5. THUMBNAIL TITLE: Judul pendek 3 sampai 6 kata untuk dicetak pada gambar banner cover.
6. IMAGE KEYWORD: 1 sampai 2 kata kunci bahasa Inggris untuk mencari visual stok (contoh: "software code", "cybersecurity", "cloud server").

FORMAT OUTPUT WAJIB BERUPA BLOK JSON DENGAN STRUKTUR BERIKUT (TANPA PEMBUNGKUS TEKS LAIN):
```json
{{
  "title": "Judul Artikel Lengkap",
  "thumb_title": "Judul Pendek Banner (3-6 Kata)",
  "image_keyword": "keyword english",
  "meta_desc": "Ringkasan meta deskripsi 1-2 kalimat (120-155 karakter).",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "content": "Isi lengkap artikel dalam format Markdown..."
}}
```
"""


def get_en_prompt(topic: str, context: str, url_references: str, id_article: dict) -> str:
    """Prompt terstruktur untuk artikel Bahasa Inggris (adaptasi global)."""
    return f"""You are a senior tech editor and developer advocate for KodePintar Global.
Write a comprehensive, professional English tech article based on the facts provided below.

TOPIC: {topic}

REFERENCE MATERIAL:
{context}

REFERENCE SOURCES:
{url_references}

INDONESIAN COUNTERPART TITLE:
{id_article.get('title')}

STRICT RULES:
1. NO EM-DASH: DO NOT use em-dashes (—) or en-dashes (–). Use commas, colons, parentheses, or periods instead.
2. ZERO HALLUCINATION: Stick strictly to the facts provided in the reference material.
3. COMPELLING HEADLINE: Sharp, authoritative, and engaging (max 75 characters).
4. STRUCTURE (Markdown): Strong lead, technical details, code snippets/tables if applicable, takeaways, and source attribution at the end.
5. THUMBNAIL TITLE: Short punchy 3-6 words banner title.
6. TAGS: 4-6 relevant tech tags in lowercase.

OUTPUT FORMAT MUST BE EXACTLY A JSON BLOCK LIKE THIS (NO EXTRA TEXT):
```json
{{
  "title": "Comprehensive English Title",
  "thumb_title": "Short Banner Title (3-6 Words)",
  "meta_desc": "Concise meta description (120-155 characters).",
  "tags": ["tag1", "tag2", "tag3", "tag4"],
  "content": "Full markdown content..."
}}
```
"""


def parse_json_output(raw_text: str) -> dict[str, Any]:
    """Ekstrak dan parse payload JSON dari response LLM menggunakan regex fallback."""
    cleaned = raw_text.strip()

    # 1. Coba regex ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Coba cari kurung kurawal terluar { ... }
    brace_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Fallback langsung parse
    try:
        return json.loads(cleaned)
    except Exception as e:
        raise ValueError(f"Gagal mem-parsing output JSON dari LLM: {e}\nRaw Response:\n{raw_text[:400]}")

