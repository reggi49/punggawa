"""Article Publishing Pipeline Graph (Assembly Line Pattern for KodePintar)."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from config.settings import settings
from orchestrator.connections import get_checkpointer, postgres_pool
from orchestrator.events import agent_node_tracker, emit_agent_event
from orchestrator.llm import llm_client
from orchestrator.prompts.writer import generate_content, get_en_prompt, get_id_prompt, parse_json_output
from orchestrator.state import AgentState
from orchestrator.tools.image_generator import generate_dual_thumbnails
from orchestrator.tools.kodepintar_publisher import PublishError, publish_article, resolve_category
from orchestrator.tools.scraper import scrape_data
from orchestrator.tools.google_news import get_google_news_topics
from orchestrator.tools.github_trending import get_github_trending_weekly

logger = logging.getLogger("ArticleGraph")


@agent_node_tracker("ingest_node", "Mempersiapkan parameter artikel")
def ingest_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    input_data = state.get("input_data", {})
    topic = input_data.get("query") or input_data.get("topic") or "Teknologi Terkini"
    target_urls = input_data.get("target_urls") or input_data.get("urls") or ""
    category = input_data.get("category") or "technology"

    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "status": "processing",
        "task_type": "article",
        "target_urls": target_urls,
        "category": category,
        "last_processed_by": settings.WORKER_ID,
        "execution_logs": [
            f"[{timestamp}] Task {task_id} ingested in Article Pipeline. Topic='{topic}', Category='{category}'."
        ],
        "error": None,
    }


@agent_node_tracker("ingest_trend_node", "Kurasi topik tren dari Google News RSS & GitHub Trending Weekly")
def ingest_trend_node(state: AgentState) -> dict[str, Any]:
    """
    Menarik kandidat topik viral secara otomatis dari Google News atau GitHub Trending Weekly.
    Jika input menyertakan source='github' atau source='gnews', mengambil top kandidat untuk diteliti.
    """
    task_id = state.get("task_id", "unknown")
    input_data = state.get("input_data", {})
    source = str(input_data.get("source") or "").lower().strip()
    action = str(input_data.get("action") or input_data.get("action_type") or "").lower().strip()
    task_type = str(state.get("task_type") or input_data.get("task_type") or "").lower().strip()
    timestamp = datetime.now(timezone.utc).isoformat()

    is_trend_task = (
        source in ("github", "gnews", "google_news")
        or action in ("trend-article", "article-trend", "auto_curate_tech")
        or task_type in ("trend-article", "article-trend")
    )

    if not is_trend_task:
        return {
            "execution_logs": [f"[{timestamp}] Standard article mode: bypassing trend discovery."],
            "error": None,
        }

    trend_items: list[dict[str, Any]] = []
    source_used = ""

    if source == "github" or (not source and (input_data.get("lang") or action == "auto_curate_tech")):
        source_used = "GitHub Trending Weekly"
        lang = input_data.get("lang") or input_data.get("language") or ""
        logger.info(f"[{settings.WORKER_ID}] Fetching GitHub Trending Weekly (lang='{lang}')...")
        trend_items = get_github_trending_weekly(language=lang, max_items=5)

    elif source in ("gnews", "google_news") or (not source and input_data.get("query")):
        source_used = "Google News RSS"
        query = input_data.get("query") or input_data.get("topic") or "technology"
        news_lang = input_data.get("lang") or input_data.get("language") or "en"
        logger.info(f"[{settings.WORKER_ID}] Fetching Google News RSS (query='{query}', lang='{news_lang}')...")
        trend_items = get_google_news_topics(keyword=query, max_items=5, lang=news_lang)

    else:
        source_used = "GitHub Trending Weekly"
        logger.info(f"[{settings.WORKER_ID}] Defaulting to GitHub Trending Weekly...")
        trend_items = get_github_trending_weekly(language="", max_items=5)

    if not trend_items:
        logger.warning(f"Tidak ada kandidat tren ditemukan dari {source_used}. Melanjutkan dengan prompt awal.")
        return {
            "trend_source_data": [],
            "trend_selected_item": None,
            "execution_logs": [
                f"[{timestamp}] Trend search in {source_used} found 0 items. Continuing with base prompt."
            ],
            "error": None,
        }

    # Filter kandidat tren agar tidak memilih topik yang sudah pernah terbit sebelumnya
    top_item = trend_items[0]
    for cand in trend_items:
        cand_id = cand.get("repo_name") or cand.get("title") or ""
        if not cand_id:
            continue
        try:
            with postgres_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM content_schedules WHERE status = 'completed' AND title ILIKE %s LIMIT 1",
                        (f"%{cand_id[:35]}%",),
                    )
                    if cur.fetchone():
                        logger.info(
                            f"⏭️ [AUTO-DEDUPLICATE] Kandidat tren '{cand_id}' sudah pernah terbit. Memilih kandidat alternatif berikutnya..."
                        )
                        continue
        except Exception:
            pass
        top_item = cand
        break

    logger.info(f"🎯 Kandidat tren terpilih dari {source_used}: {top_item}")

    updates: dict[str, Any] = {
        "trend_source_data": trend_items,
        "trend_selected_item": top_item,
    }

    if "repo_name" in top_item:
        repo_name = top_item["repo_name"]
        repo_url = top_item["repo_url"]
        desc = top_item.get("description", "")
        lang = top_item.get("language", "General")
        stars = top_item.get("stars_this_week", 0)

        curated_topic = f"Bedah Repositori Trending: {repo_name} - {desc}" if desc else f"Eksplorasi Repositori GitHub: {repo_name}"
        updates["target_urls"] = repo_url
        updates["category"] = input_data.get("category") or "programming"
        updates["execution_logs"] = [
            f"[{timestamp}] Curated GitHub Trending repo '{repo_name}' (+{stars} stars this week, {lang}). URL={repo_url}"
        ]
        new_input = dict(input_data)
        new_input["topic"] = curated_topic
        new_input["query"] = curated_topic
        new_input["target_urls"] = repo_url
        updates["input_data"] = new_input

    else:
        title = top_item.get("title", "")
        news_url = top_item.get("url", "")
        news_src = top_item.get("source", "Google News")

        updates["target_urls"] = news_url
        updates["category"] = input_data.get("category") or "technology"
        updates["execution_logs"] = [
            f"[{timestamp}] Curated Google News topic '{title}' (Source: {news_src}). URL={news_url}"
        ]
        new_input = dict(input_data)
        new_input["topic"] = title
        new_input["query"] = title
        new_input["target_urls"] = news_url
        updates["input_data"] = new_input

    return updates


@agent_node_tracker("scrape_node", "Scraping referensi materi web")
def scrape_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    target_urls = state.get("target_urls") or ""
    timestamp = datetime.now(timezone.utc).isoformat()

    if not target_urls:
        logger.warning(f"Task {task_id} tidak menyertakan target URLs, melewati tahap scrape.")
        return {
            "scraped_content": "Tidak ada URL referensi eksternal. Gunakan pengetahuan AI internal.",
            "url_references": "- Pengetahuan Internal AI\n",
            "execution_logs": [f"[{timestamp}] Scrape skipped (no URLs provided)."],
        }

    try:
        logger.info(f"[{settings.WORKER_ID}] Scraping target URLs: {target_urls}")
        combined_text, url_refs = scrape_data(target_urls)
        return {
            "scraped_content": combined_text,
            "url_references": url_refs,
            "execution_logs": [
                f"[{timestamp}] Scraped successfully ({len(combined_text)} chars from {target_urls})."
            ],
            "error": None,
        }
    except Exception as exc:
        logger.warning(f"Scrape URL eksternal gagal: {exc}. Mengaktifkan fallback pengetahuan AI internal.")
        topic = (
            state.get("input_data", {}).get("topic")
            or state.get("input_data", {}).get("query")
            or "Topik Terkini"
        )
        fallback_content = (
            f"Catatan Referensi: Akses URL eksternal gagal ({exc}).\n"
            f"Gunakan pemahaman analitis mendalam dan pengetahuan AI komprehensif mengenai: '{topic}'."
        )
        return {
            "scraped_content": fallback_content,
            "url_references": f"- Pengetahuan Analisis Internal AI (Fallback dari {target_urls})\n",
            "execution_logs": [
                f"[{timestamp}] Scrape warning: {str(exc)}. Beralih ke fallback pengetahuan AI internal."
            ],
            "error": None,
        }


@agent_node_tracker("draft_node", "Menulis konten dwibahasa ID & EN")
def draft_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    input_data = state.get("input_data", {})
    topic = input_data.get("query") or input_data.get("topic") or "Teknologi Terkini"
    scraped_content = state.get("scraped_content", "")
    url_references = state.get("url_references", "")

    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(f"[{settings.WORKER_ID}] Generating dual-language content for topic: '{topic}'")

    # Batasi materi referensi hingga 4000 karakter agar cepat diproses LLM dan mencegah timeout
    clean_context = scraped_content[:4000] if len(scraped_content) > 4000 else scraped_content

    # Sisipkan konteks tren primer (GitHub Trending / Google News) jika ada
    trend_selected_item = state.get("trend_selected_item")
    if trend_selected_item:
        if "repo_name" in trend_selected_item:
            trend_prefix = (
                f"### [SUMBER VIRAL: GITHUB TRENDING REPO]\n"
                f"- Nama Proyek: {trend_selected_item.get('repo_name')}\n"
                f"- URL: {trend_selected_item.get('repo_url')}\n"
                f"- Bahasa Pemrograman: {trend_selected_item.get('language')}\n"
                f"- Bintang Baru Minggu Ini: +{trend_selected_item.get('stars_this_week')} stars\n"
                f"- Ringkasan: {trend_selected_item.get('description')}\n\n"
            )
            clean_context = (trend_prefix + clean_context)[:4500]
            if not url_references or url_references.strip().startswith("- Pengetahuan Internal"):
                url_references = f"- {trend_selected_item.get('repo_url')}\n"
        elif "title" in trend_selected_item:
            trend_prefix = (
                f"### [SUMBER BERITA TERKINI: GOOGLE NEWS]\n"
                f"- Judul Berita: {trend_selected_item.get('title')}\n"
                f"- Sumber Media: {trend_selected_item.get('source')}\n"
                f"- Waktu Terbit: {trend_selected_item.get('published_at')}\n"
                f"- URL Berita: {trend_selected_item.get('url')}\n\n"
            )
            clean_context = (trend_prefix + clean_context)[:4500]
            if not url_references or url_references.strip().startswith("- Pengetahuan Internal"):
                url_references = f"- {trend_selected_item.get('url')}\n"

    try:
        # Generate konten dwibahasa ID & EN via Google AI Studio Gemini 3.8/3.7/...
        dual_content = generate_content(topic, clean_context, url_references)
        data_id = dual_content["id"]
        data_en = dual_content["en"]
        translation_key = dual_content["translation_key"]

        logger.info(f"✅ Draft berhasil dibuat: ID='{data_id.get('title')}' | EN='{data_en.get('title')}'")
        return {
            "dual_content": dual_content,
            "execution_logs": [
                f"[{timestamp}] Drafted dual content (ID: '{data_id.get('title')[:40]}...', EN: '{data_en.get('title')[:40]}...')."
            ],
            "error": None,
        }

    except Exception as exc:
        logger.error(f"Drafting gagal: {exc}", exc_info=True)
        return {
            "status": "failed",
            "error": f"DraftError: {str(exc)}",
            "execution_logs": [f"[{timestamp}] Drafting failed: {str(exc)}"],
        }


@agent_node_tracker("thumbnail_node", "Merender visual thumbnail dwibahasa")
def thumbnail_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    dual_content = state.get("dual_content", {})
    timestamp = datetime.now(timezone.utc).isoformat()

    data_id = dual_content.get("id", {})
    data_en = dual_content.get("en", {})

    id_title = data_id.get("thumb_title") or data_id.get("title", "Update Teknologi")
    en_title = data_en.get("thumb_title") or data_en.get("title", "Tech Update")
    keyword = data_id.get("image_keyword") or "modern technology"

    try:
        logger.info(f"[{settings.WORKER_ID}] Rendering dual thumbnails with keyword: '{keyword}'")
        img_id, img_en = generate_dual_thumbnails(id_title=id_title, en_title=en_title, keyword=keyword)
        return {
            "dual_images": {
                "id": img_id,
                "en": img_en,
            },
            "execution_logs": [f"[{timestamp}] Rendered dual localized thumbnails successfully."],
            "error": None,
        }
    except Exception as exc:
        logger.error(f"Thumbnail render gagal: {exc}", exc_info=True)
        return {
            "status": "failed",
            "error": f"ThumbnailError: {str(exc)}",
            "execution_logs": [f"[{timestamp}] Thumbnail rendering failed: {str(exc)}"],
        }


@agent_node_tracker("sop_validator_node", "Memeriksa kesesuaian SOP editorial & aset visual")
def sop_validator_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    dual_content = state.get("dual_content") or {}
    dual_images = state.get("dual_images") or {}
    category = state.get("category") or "technology"

    violations = []
    timestamp = datetime.now(timezone.utc).isoformat()

    resolved_cat = resolve_category(category)
    if not resolved_cat:
        violations.append(f"Kategori '{category}' tidak valid di CATEGORY_MAP.")

    id_data = dual_content.get("id") or {}
    if not id_data.get("title"):
        violations.append("Versi ID tidak memiliki title.")
    if len(id_data.get("content", "")) < 200:
        violations.append(f"Konten ID terlalu pendek ({len(id_data.get('content', ''))} chars, min 200).")
    if not id_data.get("meta_desc"):
        violations.append("Versi ID tidak memiliki meta_desc.")
    if not id_data.get("tags"):
        violations.append("Versi ID tidak memiliki tags.")

    en_data = dual_content.get("en") or {}
    if not en_data.get("title"):
        violations.append("Versi EN tidak memiliki title.")
    if len(en_data.get("content", "")) < 200:
        violations.append(f"Konten EN terlalu pendek ({len(en_data.get('content', ''))} chars, min 200).")
    if not en_data.get("meta_desc"):
        violations.append("Versi EN tidak memiliki meta_desc.")
    if not en_data.get("tags"):
        violations.append("Versi EN tidak memiliki tags.")

    if not dual_content.get("translation_key") or id_data.get("translationKey") != en_data.get("translationKey"):
        violations.append("TranslationKey ID dan EN tidak sinkron atau hilang.")

    for lang in ("id", "en"):
        b64 = dual_images.get(lang, "")
        if not b64 or not b64.startswith("data:image/jpeg;base64,") or len(b64) < 1000:
            violations.append(f"Image base64 [{lang}] tidak valid atau rusak.")

    if violations:
        logger.warning(f"❌ [SOP VALIDATOR] Pelanggaran SOP pada task {task_id}: {violations}")
        return {
            "status": "failed",
            "error": "SOP_VIOLATION: " + " | ".join(violations),
            "execution_logs": [
                f"[{timestamp}] SOP Validator REJECTED: {len(violations)} violations detected."
            ],
        }

    logger.info(f"✅ [SOP VALIDATOR] Task {task_id} memenuhi seluruh standar SOP.")
    return {
        "execution_logs": [f"[{timestamp}] SOP Validator APPROVED all quality criteria."],
        "error": None,
    }


@agent_node_tracker("publish_node", "Mempublikasikan artikel ke platform KodePintar Lucy")
def publish_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    dual_content = state.get("dual_content", {})
    dual_images = state.get("dual_images", {})
    category = state.get("category") or "technology"

    id_data = dual_content["id"]
    en_data = dual_content["en"]
    timestamp = datetime.now(timezone.utc).isoformat()
    input_data = state.get("input_data", {})
    dry_run = (
        input_data.get("dry_run", False)
        or not settings.API_ENDPOINT
        or not settings.SECRET_KEY
        or settings.SECRET_KEY.startswith("your_")
    )

    if dry_run:
        logger.info(f"[{settings.WORKER_ID}] 🧪 [DRY-RUN] Melewati HTTP publish (dry_run aktif atau kredensial API belum diset).")
        article_id_id = f"dry_run_{uuid.uuid4().hex[:8]}"
        article_id_en = f"dry_run_{uuid.uuid4().hex[:8]}"
        return {
            "published_ids": {
                "id": article_id_id,
                "en": article_id_en,
            },
            "execution_logs": [
                f"[{timestamp}] [DRY-RUN] Pipeline completed up to thumbnail render & SOP validation without publishing to remote API."
            ],
            "error": None,
        }

    try:
        logger.info(f"[{settings.WORKER_ID}] Publishing ID article: '{id_data['title']}'...")
        res_id = publish_article(id_data, category, dual_images["id"])
        article_id_id = res_id.get("article_id")

        logger.info(f"[{settings.WORKER_ID}] Publishing EN article: '{en_data['title']}'...")
        res_en = publish_article(en_data, category, dual_images["en"])
        article_id_en = res_en.get("article_id")

        logger.info(f"🎉 [PUBLISH SUCCESS] ID: {article_id_id} | EN: {article_id_en}")
        return {
            "published_ids": {
                "id": article_id_id,
                "en": article_id_en,
            },
            "execution_logs": [
                f"[{timestamp}] Published successfully. Article ID [ID]={article_id_id}, [EN]={article_id_en}."
            ],
            "error": None,
        }

    except PublishError as pe:
        logger.error(f"Publish gagal: {pe}")
        return {
            "status": "failed",
            "error": f"PublishError: {str(pe)}",
            "execution_logs": [f"[{timestamp}] Publish failed: {str(pe)}"],
        }
    except Exception as exc:
        logger.error(f"Publish fatal error: {exc}", exc_info=True)
        return {
            "status": "failed",
            "error": f"FatalPublishError: {str(exc)}",
            "execution_logs": [f"[{timestamp}] Publish failed: {str(exc)}"],
        }


@agent_node_tracker("failed_node", "Menangani kegagalan pipeline")
def failed_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    error_msg = state.get("error", "Unknown validation failure")
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.error(f"[{settings.WORKER_ID}] Task {task_id} gagal di Article Pipeline: {error_msg}")
    return {
        "status": "failed",
        "execution_logs": [f"[{timestamp}] Article pipeline terminated: {error_msg}"],
    }


@agent_node_tracker("complete_node", "Menyelesaikan eksekusi task pipeline")
def complete_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    status = state.get("status", "completed")
    published = state.get("published_ids") or {}
    dual_content = state.get("dual_content") or {}
    timestamp = datetime.now(timezone.utc).isoformat()

    if status == "failed":
        summary = f"Article Pipeline Gagal: {state.get('error')}"
    else:
        status = "completed"
        id_title = dual_content.get("id", {}).get("title", "")
        en_title = dual_content.get("en", {}).get("title", "")
        summary = (
            f"Dual-Language Artikel Resmi Terbit!\n"
            f"- [ID] {id_title} (ID: {published.get('id')})\n"
            f"- [EN] {en_title} (ID: {published.get('en')})\n"
            f"- Translation Key: {dual_content.get('translation_key')}"
        )

    return {
        "status": status,
        "result": {
            "summary": summary,
            "published_ids": published,
            "executed_by": settings.WORKER_ID,
        },
        "last_processed_by": settings.WORKER_ID,
        "execution_logs": [f"[{timestamp}] Article task {task_id} finalized with status={status}."],
    }


def route_after_step(state: AgentState) -> Literal["continue", "failed"]:
    if state.get("status") == "failed" or state.get("error"):
        return "failed"
    return "continue"


def route_after_sop(state: AgentState) -> Literal["publish", "failed"]:
    if state.get("status") == "failed" or state.get("error"):
        return "failed"
    return "publish"


def create_article_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("ingest", ingest_node)
    workflow.add_node("ingest_trend", ingest_trend_node)
    workflow.add_node("scrape", scrape_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("thumbnail", thumbnail_node)
    workflow.add_node("sop_validator", sop_validator_node)
    workflow.add_node("publish", publish_node)
    workflow.add_node("failed", failed_node)
    workflow.add_node("complete", complete_node)

    workflow.add_edge(START, "ingest")

    workflow.add_conditional_edges("ingest", route_after_step, {"continue": "ingest_trend", "failed": "failed"})
    workflow.add_conditional_edges("ingest_trend", route_after_step, {"continue": "scrape", "failed": "failed"})
    workflow.add_conditional_edges("scrape", route_after_step, {"continue": "draft", "failed": "failed"})
    workflow.add_conditional_edges("draft", route_after_step, {"continue": "thumbnail", "failed": "failed"})
    workflow.add_conditional_edges("thumbnail", route_after_step, {"continue": "sop_validator", "failed": "failed"})
    workflow.add_conditional_edges("sop_validator", route_after_sop, {"publish": "publish", "failed": "failed"})

    workflow.add_edge("publish", "complete")
    workflow.add_edge("failed", "complete")
    workflow.add_edge("complete", END)

    checkpointer = get_checkpointer()
    return workflow.compile(checkpointer=checkpointer)


article_graph_app = create_article_graph()
