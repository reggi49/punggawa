import os
import re
import time
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

try:
    from core.logger import get_logger
    log = get_logger()
except Exception:
    import logging
    log = logging.getLogger("Writer")


def make_translation_key(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = re.sub(r'[^a-z0-9]+', '-', cleaned)
    return cleaned.strip('-')[:60]


def get_id_prompt(topic: str, combined_clean_text: str, url_references: str) -> str:
    # PROMPT ASLI BAHASA INDONESIA (100% UNTOUCHED)
    return f"""Kamu adalah seorang Jurnalis Teknologi Senior dan Tech-Blogger veteran Indonesia. Gayamu tajam, kritis, pragmatis, dan sangat paham konteks industri (seperti PC gaming, hardware, atau software development). Tugasmu adalah menulis artikel blog MENDALAM yang panjang dan komprehensif berdasarkan referensi.

    REFERENSI:
    {combined_clean_text}

    TOPIK UTAMA (KEYWORD): {topic}
    
    ========================
    ATURAN COPYWRITING & JUDUL (STOPPING POWER)
    ========================
    1. JUDUL (TITLE): Harus memancing klik dengan 'Curiosity Gap' atau opini berani, tanpa clickbait murahan (bohong). 
       - BURUK: "Update Video2X V6 Rilis" atau "Realita Steam Chart Agustus"
       - BAGUS: "Video2X V6 Rombak Total Mesin C++: Upscale Video Sekarang Jauh Lebih Ngebut" atau "Steam Chart Agustus: Rilis Game Banyak, Tapi Kok Gini Realitanya?"
    2. HOOK PARAGRAF 1: Langsung pukul pembaca dengan keresahan utama (pain point), fakta paling menarik dari referensi, atau pertanyaan menohok. JANGAN ada kalimat pembuka klise.
    3. TONE & VIBE: Pragmatis, to-the-point dalam artian tidak bertele-tele, tapi tetap mendalam saat membahas esensi teknis. Gunakan bahasa tongkrongan IT/Gamer (setup, ngelag, bottleneck, hype, codebase).
    4. Gunakan istilah campur bahasa Inggris-Indonesia yang wajar jangan memaksakan translate kata inggris ke indonesia (contoh: setup, ngelag, build, bug).
    5. TRANSISI NATURAL: Jangan gunakan transisi kaku seperti "Pertama-tama,", "Selain itu,", atau "Di sisi lain,". Biarkan kalimat mengalir lewat konteks cerita.
    6. PACING (RITME) dan DILARANG menggunakan em-dash (—): Variasikan panjang kalimat. Campur kalimat pendek (4-5 kata) untuk penekanan, dengan kalimat panjang untuk penjelasan agar tidak terdengar monoton seperti mesin.
    
    ========================
    KREATIVITAS PENYAMPAIAN vs FAKTA (WAJIB DIPATUHI)
    ========================
    1. KREATIF DI GAYA BAHASA, KAKU DI FAKTA: Kamu WAJIB menulis dengan gaya yang asik, menggunakan analogi kehidupan sehari-hari, pertanyaan retoris, dan opini skeptis ala tech-reviewer. TAPI, semua spesifikasi, nama software, angka, klaim performa, dan entitas WAJIB 100% bersumber dari teks REFERENSI.
    2. CARA MEMPERPANJANG ARTIKEL TANPA HALUSINASI:
       - Eksplorasi "MENGAPA" dan "BAGAIMANA": Jangan hanya menyebutkan fiturnya (APA). Jelaskan bagaimana fitur/update tersebut bekerja atau mengapa itu penting, menggunakan murni logika dari informasi yang ada di referensi.
       - Gunakan Analogi: Untuk menjelaskan hal teknis dari referensi, gunakan analogi sehari-hari (misal: "Ibarat jalan tol yang tadinya macet, sekarang ditambah 4 lajur..."). Ini menambah volume dan kreativitas tulisan tanpa menambah fakta palsu.
       - Bermain dengan Ekspektasi vs Realita: Bahas apakah pembaruan/berita di referensi ini sesuai dengan ekspektasi komunitas, murni berdasarkan sentimen di dalam referensi.
    3. ISOLASI ENTITAS (ZERO HALLUCINATION): DILARANG KERAS menyebutkan nama game, framework, software, perusahaan, atau tokoh lain yang TIDAK ADA di dalam teks referensi dengan dalih "memberikan konteks". Gunakan HANYA bahan baku yang disuapkan kepadamu.

    ========================
    ATURAN SEO & STRUKTUR KONTEN
    ========================
    - Gunakan struktur Markdown (##, ###) untuk subjudul. Buat subjudul yang menarik dan mengundang rasa ingin tahu (contoh: "Kenapa Fitur Ini Penting?" BUKAN "Pendahuluan" atau "Kesimpulan").
    - Gunakan **bold** HANYA untuk istilah teknis atau poin yang benar-benar penting.
    - Keyword "{topic}" WAJIB muncul secara natural (tidak terkesan dipaksakan) di paragraf pertama.
    - TABEL: Jika referensi mengandung perbandingan data, harga, atau spesifikasi teknis, WAJIB buatkan dalam bentuk Markdown Table.
    - KODE: Jika ada script, gunakan Markdown Code Fences (```bash atau ```javascript). DILARANG pakai tag HTML <pre> atau <code>.
    - JANGAN menyertakan format kutipan kaku seperti [REF 1]. Lebur informasinya menjadi kalimat utuh.
    - Di bagian paling bawah CONTENT, tambahkan "## Referensi" dan cantumkan link ini:
    {url_references}

    ========================
    FORMAT OUTPUT MUTLAK (SYSTEM RULES)
    ========================
    1. JANGAN gunakan bintang/bold (**) pada baris TITLE, META_DESC, TAGS, dan IMAGE_PROMPT.
    2. META_DESC WAJIB berupa teks murni (plain text), 1-2 kalimat UTUH yang SELESAI, tanpa clickbait murahan.

    Keluarkan output dengan format persis seperti ini:
    TITLE: [Judul Artikel dengan STOPPING POWER]
    THUMB_TITLE: [Judul Gambar Sangat Singkat, Maks 40 Karakter]
    META_DESC: [Deskripsi SEO utuh]
    TAGS: [Tag1, Tag2, Tag3]
    IMAGE_PROMPT: [Deskripsi visual spesifik dalam bahasa Inggris]
    IMAGE_KEYWORD: [Ekstrak 1-3 kata kunci benda utama dalam bahasa Inggris]
    CONTENT: [Isi artikel Markdown sesuai semua aturan di atas]"""


def get_en_prompt(topic: str, combined_clean_text: str, url_references: str, id_article: dict | None = None) -> str:
    # PROMPT MIRROR BAHASA INGGRIS (HACKERNEWS / SILICON VALLEY TECH JOURNALISM)
    return f"""You are a Principal Systems Engineer and Veteran Tech Columnist. Your writing style is sharp, pragmatic, highly engaging, and deeply attuned to developer workflows and systems architecture. Write an IN-DEPTH, comprehensive technical blog post based strictly on the provided reference material.

    REFERENCE:
    {combined_clean_text}

    MAIN TOPIC (KEYWORD): {topic}
    
    ========================
    COPYWRITING & HEADLINE RULES
    ========================
    1. TITLE: Must be highly compelling with a strong 'Curiosity Gap' or bold engineering take, without shallow clickbait.
       - POOR: "Gortex Vertex AI Proxy Released"
       - GREAT: "Google Vertex AI Rate Limits Crushing Your Backend? Gortex Fixes It with a Native Go Proxy"
    2. HOOK (PARAGRAPH 1): Immediately hit the reader with the core architectural bottleneck, high-impact benchmark, or a provocative systems question. NO generic or cliché openings ("In the fast-evolving world of AI...").
    3. TONE & VIBE: Pragmatic, authoritative, zero-fluff, technically rigorous yet conversational (HackerNews front-page style).
    4. NATURAL FLOW: Avoid robotic transitions ("First of all,", "Moreover,", "In conclusion,"). Let the technical narrative flow seamlessly.
    5. PACING & NO EM-DASH (—): Dynamically vary sentence length. Do not use em-dashes (—).
    
    ========================
    ZERO HALLUCINATION & FACT ISOLATION
    ========================
    1. STRICT FACTS: All benchmarks, library names, architectures, API endpoints, and performance metrics MUST 100% originate from the REFERENCE material.
    2. ZERO ENTITY INJECTION: NEVER introduce frameworks, libraries, companies, or tools that are not explicitly present in the reference text.
    3. EXPLAIN WHY & HOW: Dive deep into how features work and why they matter using pure technical logic from the source.
    4. STRUCTURE: Use Markdown headings (##, ###). Format comparison data into Markdown Tables. Format code snippets using proper fences (```go, ```bash).
    5. At the bottom of CONTENT, add "## References" followed by:
    {url_references}

    ========================
    STRICT OUTPUT FORMAT
    ========================
    1. Do NOT use markdown bold (**) on TITLE, THUMB_TITLE, META_DESC, TAGS, or IMAGE lines.
    2. META_DESC must be 1-2 complete, engaging plain text sentences.

    OUTPUT FORMAT EXACTLY LIKE THIS:
    TITLE: [English Title with Stopping Power]
    THUMB_TITLE: [Concise Thumbnail Title, Max 40 Characters]
    META_DESC: [Complete SEO Description]
    TAGS: [Tag1, Tag2, Tag3]
    IMAGE_PROMPT: [Visual prompt in English]
    IMAGE_KEYWORD: [1-3 physical object keywords in English]
    CONTENT: [Full Markdown Content based on all rules above]"""


def _call_gemini_or_ollama(prompt: str) -> str:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OLLAMA_URL = os.getenv("OLLAMA_URL")
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY tidak ditemukan di file .env")

    genai.configure(api_key=GEMINI_API_KEY)
    gemini_models = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite"
    ]
    
    for idx, model_name in enumerate(gemini_models, 1):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response.text and len(response.text.strip()) > 200:
                log.info(f"   ✅ [Gemini] Berhasil generate konten menggunakan model: {model_name}")
                return response.text
        except Exception as e:
            log.warning(f"   ⚠️ Model {model_name} gagal: {e}")
            time.sleep(3)

    # Fallback ke Ollama lokal
    ollama_payload = {
        "model": "qwen3.5:9b",
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 8192, "temperature": 0.5}
    }
    res = httpx.post(OLLAMA_URL or "http://localhost:11434/api/generate", json=ollama_payload, timeout=300.0)
    res.raise_for_status()
    return res.json().get("response", "")


def _parse_ai_output(raw_text: str, fallback_topic: str = "Technology") -> dict:
    title_match = re.search(r'TITLE:\s*(.*)', raw_text, re.IGNORECASE)
    title = title_match.group(1).replace('*', '').replace('"', '').replace('#', '').strip() if title_match else fallback_topic

    thumb_match = re.search(r'THUMB_TITLE:\s*(.*)', raw_text, re.IGNORECASE)
    thumb_title = thumb_match.group(1).replace('*', '').replace('"', '').replace('#', '').strip() if thumb_match else title

    meta_match = re.search(r'META_DESC:\s*(.*)', raw_text, re.IGNORECASE)
    meta_desc = meta_match.group(1).replace('*', '').replace('"', '').replace('#', '').strip() if meta_match else ""

    tags_match = re.search(r'TAGS:\s*(.*)', raw_text, re.IGNORECASE)
    tags = tags_match.group(1).replace('*', '').strip() if tags_match else "Technology, Go, Cloud"

    visual_match = re.search(r'IMAGE_PROMPT:\s*(.*)', raw_text, re.IGNORECASE)
    visual_prompt = visual_match.group(1).strip() if visual_match else fallback_topic

    keyword_match = re.search(r'IMAGE_KEYWORD:\s*(.*)', raw_text, re.IGNORECASE)
    image_keyword = keyword_match.group(1).strip() if keyword_match else "server technology"

    content_match = re.search(r'CONTENT:([\s\S]*)', raw_text, re.IGNORECASE)
    content = content_match.group(1).strip() if content_match else raw_text

    content = content.replace('—', ', ')
    content = re.sub(r'\[REF\s*\d+\]', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<pre>|</pre>|<code>|</code>', '', content, flags=re.IGNORECASE)

    return {
        "title": title,
        "thumb_title": thumb_title,
        "meta_desc": meta_desc,
        "tags": tags,
        "image_prompt": visual_prompt,
        "image_keyword": image_keyword,
        "content": content
    }


def generate_content(topic: str, combined_clean_text: str, url_references: str) -> dict:
    translation_key = make_translation_key(topic)

    log.info("🧠 [AI-ID] Menulis artikel orisinal Bahasa Indonesia...")
    id_raw = _call_gemini_or_ollama(get_id_prompt(topic, combined_clean_text, url_references))
    id_data = _parse_ai_output(id_raw, topic)
    id_data["locale"] = "id"
    id_data["translationKey"] = translation_key

    log.info("🧠 [AI-EN] Menulis artikel orisinal Bahasa Inggris (Mirror Native)...")
    en_raw = _call_gemini_or_ollama(get_en_prompt(topic, combined_clean_text, url_references, id_data))
    en_data = _parse_ai_output(en_raw, topic)
    en_data["locale"] = "en"
    en_data["translationKey"] = translation_key

    return {
        "translation_key": translation_key,
        "id": id_data,
        "en": en_data
    }


# Alias backward-compatibility
parse_json_output = _parse_ai_output
