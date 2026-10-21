"""Backward-compatibility bridge for default agent_app and visualizer events."""
from orchestrator.events import agent_node_tracker, emit_agent_event, emit_idle_event
from orchestrator.graphs import DEFAULT_GRAPH, get_graph
from orchestrator.graphs.article_pipeline import article_graph_app
from orchestrator.graphs.chat_agent import chat_graph_app
from orchestrator.graphs.dongeng_pipeline import dongeng_graph_app

# Default agent app untuk menjaga backward compatibility
agent_app = DEFAULT_GRAPH

__all__ = [
    "agent_app",
    "get_graph",
    "article_graph_app",
    "chat_graph_app",
    "dongeng_graph_app",
    "emit_agent_event",
    "emit_idle_event",
    "agent_node_tracker",
]

