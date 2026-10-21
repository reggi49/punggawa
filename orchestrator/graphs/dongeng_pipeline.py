"""Dongeng Video Ingestion & Publishing Pipeline Graph for Bogorstore CMS."""
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from config.settings import settings
from orchestrator.connections import get_checkpointer
from orchestrator.events import agent_node_tracker, emit_agent_event
from orchestrator.prompts.dongeng import curate_dongeng_video
from orchestrator.state import AgentState
from orchestrator.tools.dongeng_publisher import (
    HARDCODED_CATEGORIES,
    DongengPublishError,
    is_already_in_cms,
    post_to_cms,
)
from orchestrator.tools.dongeng_thumbnail import create_cms_thumbnail
from orchestrator.tools.youtube_client import (
    get_best_youtube_bg,
    get_youtube_metadata,
    is_short_video,
    looks_like_skip,
)

logger = logging.getLogger("DongengGraph")


def extract_video_id(raw_input: str) -> str:
    """Ekstrak video ID dari string biasa atau URL YouTube."""
    if not raw_input:
        return ""
    s = raw_input.strip()
    # 1. Jika URL youtube.com/watch?v=ID
    m = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", s)
    if m:
        return m.group(1)
    # 2. Jika URL youtu.be/ID atau /shorts/ID
    m = re.search(r"(?:youtu\.be/|/shorts/)([a-zA-Z0-9_-]{11})", s)
    if m:
        return m.group(1)
    # 3. Jika langsung 11 karakter ID YouTube
    if re.match(r"^[a-zA-Z0-9_-]{11}$", s):
        return s
    return s


@agent_node_tracker("ingest_node", "Mempersiapkan metadata video YouTube")
def ingest_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    input_data = state.get("input_data", {})
    raw_video = (
        input_data.get("video_id")
        or input_data.get("videoId")
        or input_data.get("query")
        or input_data.get("topic")
        or state.get("video_id")
        or ""
    )
    video_id = extract_video_id(str(raw_video))
    timestamp = datetime.now(timezone.utc).isoformat()

    if not video_id:
        err_msg = "video_id tidak ditemukan pada parameter input."
        logger.error(f"Task {task_id} gagal: {err_msg}")
        return {
            "status": "failed",
            "task_type": "dongeng",
            "video_id": None,
            "error": err_msg,
            "execution_logs": [f"[{timestamp}] Ingest failed: {err_msg}"],
        }

    logger.info(f"[{settings.WORKER_ID}] Ingesting YouTube video: {video_id}")

    # Ambil metadata YouTube
    info = get_youtube_metadata(video_id)
    if not info:
        err_msg = f"Gagal mengambil metadata YouTube untuk videoId: {video_id}"
        logger.error(err_msg)
        return {
            "status": "failed",
            "task_type": "dongeng",
            "video_id": video_id,
            "error": err_msg,
            "execution_logs": [f"[{timestamp}] Ingest failed: {err_msg}"],
        }

    title = info.get("title", "")
    dur = info.get("duration_seconds", 0)

    # 1. Pra-saring kata kunci kompilasi/lagu (gratis)
    kw_hit = looks_like_skip(title)
    if kw_hit:
        skip_msg = f"Video dilewati karena kata kunci kompilasi/lagu: '{kw_hit}'"
        logger.info(f"[SKIP] {video_id}: {skip_msg}")
        return {
            "status": "completed",
            "task_type": "dongeng",
            "video_id": video_id,
            "video_metadata": info,
            "curation_result": {"skip": True, "reason": f"keyword:{kw_hit}", "title": title, "category_id": "0"},
            "execution_logs": [f"[{timestamp}] Pre-filter skipped: {skip_msg}"],
            "error": None,
        }

    # 2. Deteksi YouTube Shorts
    if is_short_video(video_id, dur):
        skip_msg = f"Video dilewati karena terdeteksi sebagai YouTube Shorts ({dur}s)."
        logger.info(f"[SKIP] {video_id}: {skip_msg}")
        return {
            "status": "completed",
            "task_type": "dongeng",
            "video_id": video_id,
            "video_metadata": info,
            "curation_result": {"skip": True, "reason": "shorts", "title": title, "category_id": "0"},
            "execution_logs": [f"[{timestamp}] Pre-filter skipped: {skip_msg}"],
            "error": None,
        }

    return {
        "status": "processing",
        "task_type": "dongeng",
        "video_id": video_id,
        "video_metadata": info,
        "last_processed_by": settings.WORKER_ID,
        "execution_logs": [
            f"[{timestamp}] Task {task_id} ingested in Dongeng Pipeline. Video ID='{video_id}', Title='{title[:60]}'."
        ],
        "error": None,
    }


@agent_node_tracker("check_duplicate_node", "Memeriksa duplikasi video di CMS")
def check_duplicate_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    video_id = state.get("video_id") or ""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        already_in_cms = is_already_in_cms(video_id)
        if already_in_cms:
            msg = f"Video '{video_id}' sudah pernah diterbitkan di CMS Bogorstore."
            logger.info(f"[SKIP-DUPLICATE] {msg}")
            return {
                "status": "completed",
                "curation_result": {"skip": True, "reason": "already_in_cms"},
                "execution_logs": [f"[{timestamp}] Duplicate detected: {msg}"],
                "error": None,
            }

        return {
            "execution_logs": [f"[{timestamp}] Duplicate check passed: Video '{video_id}' belum ada di CMS."],
            "error": None,
        }
    except Exception as exc:
        err_msg = f"Fail-closed: pemeriksaan duplikat gagal demi keamanan data: {exc}"
        logger.error(err_msg)
        return {
            "status": "failed",
            "error": err_msg,
            "execution_logs": [f"[{timestamp}] Duplicate check failed: {err_msg}"],
        }


@agent_node_tracker("curate_video_node", "Kurasi AI judul dan kategori cerita")
def curate_video_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    video_id = state.get("video_id", "")
    info = state.get("video_metadata") or {}
    title = info.get("title", "")
    desc = info.get("description", "")
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(f"[{settings.WORKER_ID}] Curating video '{video_id}' with AI: '{title[:50]}'")
    curation = curate_dongeng_video(title, desc)

    if curation.get("skip"):
        reason = curation.get("reason", "Dilewati oleh kurator AI")
        logger.info(f"[SKIP-AI] Video '{video_id}' dilewati: {reason}")
        return {
            "status": "completed",
            "curation_result": curation,
            "execution_logs": [f"[{timestamp}] AI Curation SKIPPED: {reason}."],
            "error": None,
        }

    clean_title = curation.get("title") or title
    cat_id = curation.get("category_id", "3")
    cat_name = HARDCODED_CATEGORIES.get(cat_id, "Fabel")

    logger.info(f"✅ AI Curation SUCCESS: Title='{clean_title}', Category={cat_id} ({cat_name})")
    return {
        "curation_result": curation,
        "execution_logs": [
            f"[{timestamp}] AI Curation approved: Clean Title='{clean_title}', Category={cat_id} ({cat_name})."
        ],
        "error": None,
    }


@agent_node_tracker("thumbnail_portrait_node", "Membuat thumbnail portrait 200x300")
def thumbnail_portrait_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    video_id = state.get("video_id", "")
    curation = state.get("curation_result") or {}
    clean_title = curation.get("title", "Cerita Rakyat")
    timestamp = datetime.now(timezone.utc).isoformat()

    bg_url = get_best_youtube_bg(video_id)
    logger.info(f"[{settings.WORKER_ID}] Creating portrait thumbnail for '{video_id}' (Title: '{clean_title}')")

    thumb_path = create_cms_thumbnail(bg_url, clean_title)
    if not thumb_path or not os.path.exists(thumb_path):
        err_msg = "Gagal membuat gambar thumbnail portrait 200x300."
        logger.error(err_msg)
        return {
            "status": "failed",
            "error": err_msg,
            "execution_logs": [f"[{timestamp}] Thumbnail creation failed."],
        }

    return {
        "thumbnail_path": thumb_path,
        "execution_logs": [f"[{timestamp}] Thumbnail portrait created successfully: {thumb_path}."],
        "error": None,
    }


@agent_node_tracker("sop_validator_node", "Validasi SOP kualitas konten dongeng")
def sop_validator_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    video_id = state.get("video_id")
    curation = state.get("curation_result") or {}
    thumb_path = state.get("thumbnail_path")
    timestamp = datetime.now(timezone.utc).isoformat()

    violations = []
    if not video_id:
        violations.append("video_id kosong.")
    if not curation.get("title"):
        violations.append("Judul dongeng kosong.")
    cat_id = str(curation.get("category_id", ""))
    if cat_id not in HARDCODED_CATEGORIES:
        violations.append(f"Kategori '{cat_id}' tidak valid (wajib 1-7).")
    if not thumb_path or not os.path.exists(thumb_path) or os.path.getsize(thumb_path) < 500:
        violations.append("File thumbnail rusak atau tidak ada di disk.")

    if violations:
        err_msg = "SOP_VIOLATIONS: " + " | ".join(violations)
        logger.warning(f"❌ [SOP VALIDATOR] {err_msg}")
        return {
            "status": "failed",
            "error": err_msg,
            "execution_logs": [f"[{timestamp}] SOP Validation REJECTED: {err_msg}"],
        }

    logger.info(f"✅ [SOP VALIDATOR] Task {task_id} lolos semua standar SOP.")
    return {
        "execution_logs": [f"[{timestamp}] SOP Validation APPROVED all quality criteria."],
        "error": None,
    }


@agent_node_tracker("publish_node", "Mengunggah video dan thumbnail ke Bogorstore CMS")
def publish_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    video_id = state.get("video_id", "")
    info = state.get("video_metadata") or {}
    curation = state.get("curation_result") or {}
    thumb_path = state.get("thumbnail_path", "")
    input_data = state.get("input_data", {})
    dry_run = input_data.get("dry_run", False) or not settings.DONGENG_CMS_POST_URL
    timestamp = datetime.now(timezone.utc).isoformat()

    final_title = curation.get("title") or info.get("title", "")
    category_id = curation.get("category_id", "3")

    try:
        post_resp = post_to_cms(
            video_id=video_id,
            info=info,
            final_title=final_title,
            category_id=category_id,
            thumbnail_path=thumb_path,
            dry_run=dry_run,
        )

        # Hapus thumbnail sementara jika berhasil
        if thumb_path and os.path.exists(thumb_path) and not dry_run:
            try:
                os.remove(thumb_path)
            except Exception:
                pass

        logger.info(f"🎉 [PUBLISH SUCCESS] Video '{video_id}' berhasil diterbitkan ke CMS Bogorstore!")
        return {
            "cms_post_result": post_resp,
            "status": "completed",
            "execution_logs": [
                f"[{timestamp}] Published to Bogorstore CMS successfully. Title='{final_title}', Category={category_id}."
            ],
            "error": None,
        }

    except Exception as exc:
        logger.error(f"Publish ke CMS Bogorstore gagal: {exc}")
        return {
            "status": "failed",
            "error": f"PublishError: {str(exc)}",
            "execution_logs": [f"[{timestamp}] CMS Publish failed: {str(exc)}"],
        }


def complete_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    status = state.get("status", "completed")
    video_id = state.get("video_id")
    curation = state.get("curation_result") or {}
    cms_res = state.get("cms_post_result") or {}
    error = state.get("error")
    timestamp = datetime.now(timezone.utc).isoformat()

    summary_text = (
        f"Dongeng Pipeline Selesai (Status: {status.upper()}). "
        f"Video ID: {video_id or 'N/A'}. "
        f"Title: {curation.get('title', 'N/A')}. "
        f"Category: {curation.get('category_name', 'N/A')}."
    )
    if error:
        summary_text += f" Error: {error}"

    logger.info(f"[{settings.WORKER_ID}] Finalizing dongeng task: {task_id} with status={status}")
    return {
        "status": status,
        "result": {
            "video_id": video_id,
            "title": curation.get("title"),
            "category_id": curation.get("category_id"),
            "category_name": curation.get("category_name"),
            "cms_result": cms_res,
            "summary": summary_text,
            "status": status,
        },
        "execution_logs": [f"[{timestamp}] Dongeng task {task_id} finalized with status={status}."],
    }


def route_after_node(state: AgentState) -> Literal["complete_node", "continue"]:
    """Conditional edge: Jika state sudah skipped atau failed, langsung lompat ke complete_node."""
    status = state.get("status")
    curation = state.get("curation_result") or {}
    if status in ("failed", "completed") or curation.get("skip"):
        return "complete_node"
    return "continue"


def build_dongeng_graph() -> StateGraph:
    """Merakit alur sekuensial Assembly Line untuk kurasi dan publikasi video Dongeng."""
    workflow = StateGraph(AgentState)

    # 1. Tambahkan node
    workflow.add_node("ingest_node", ingest_node)
    workflow.add_node("check_duplicate_node", check_duplicate_node)
    workflow.add_node("curate_video_node", curate_video_node)
    workflow.add_node("thumbnail_portrait_node", thumbnail_portrait_node)
    workflow.add_node("sop_validator_node", sop_validator_node)
    workflow.add_node("publish_node", publish_node)
    workflow.add_node("complete_node", complete_node)

    # 2. Rangkai edge dengan conditional bypass
    workflow.add_edge(START, "ingest_node")

    workflow.add_conditional_edges(
        "ingest_node",
        route_after_node,
        {"complete_node": "complete_node", "continue": "check_duplicate_node"},
    )
    workflow.add_conditional_edges(
        "check_duplicate_node",
        route_after_node,
        {"complete_node": "complete_node", "continue": "curate_video_node"},
    )
    workflow.add_conditional_edges(
        "curate_video_node",
        route_after_node,
        {"complete_node": "complete_node", "continue": "thumbnail_portrait_node"},
    )
    workflow.add_conditional_edges(
        "thumbnail_portrait_node",
        route_after_node,
        {"complete_node": "complete_node", "continue": "sop_validator_node"},
    )
    workflow.add_conditional_edges(
        "sop_validator_node",
        route_after_node,
        {"complete_node": "complete_node", "continue": "publish_node"},
    )

    workflow.add_edge("publish_node", "complete_node")
    workflow.add_edge("complete_node", END)

    return workflow


# Kompilasi graph dengan PostgresSaver checkpointer
checkpointer = get_checkpointer()
dongeng_graph_app = build_dongeng_graph().compile(checkpointer=checkpointer)

__all__ = ["dongeng_graph_app", "build_dongeng_graph"]

