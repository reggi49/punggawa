"""Central Graph Registry for Polymorphic Worker Invocation."""
import logging
from typing import Any
from orchestrator.graphs.article_pipeline import article_graph_app
from orchestrator.graphs.chat_agent import chat_graph_app
from orchestrator.graphs.dongeng_pipeline import dongeng_graph_app

logger = logging.getLogger("GraphRegistry")

# Peta seluruh graf aplikasi yang didukung sistem
GRAPH_REGISTRY: dict[str, Any] = {
    "article": article_graph_app,
    "article_publisher": article_graph_app,
    "writer": article_graph_app,
    "trend-article": article_graph_app,
    "article-trend": article_graph_app,
    "auto_curate_tech": article_graph_app,
    "chat": chat_graph_app,
    "chat_assistant": chat_graph_app,
    "react": chat_graph_app,
    "dongeng": dongeng_graph_app,
    "dongeng_pipeline": dongeng_graph_app,
    "youtube_dongeng": dongeng_graph_app,
}

# Default fallback jika task_type tidak dikenal
DEFAULT_GRAPH = chat_graph_app


def get_graph(task_type: str | None) -> Any:
    """Mengembalikan instance LangGraph yang sesuai berdasarkan task_type."""
    if not task_type:
        return DEFAULT_GRAPH

    normalized = str(task_type).lower().strip()
    graph = GRAPH_REGISTRY.get(normalized)
    if graph:
        logger.info(f"Menggunakan Graph: '{normalized}'")
        return graph

    logger.warning(f"task_type '{task_type}' tidak terdaftar di GRAPH_REGISTRY. Menggunakan default 'chat'.")
    return DEFAULT_GRAPH

