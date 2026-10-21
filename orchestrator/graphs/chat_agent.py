"""Conversational ReAct Tool Agent Graph."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from config.settings import settings
from orchestrator.connections import get_checkpointer
from orchestrator.events import agent_node_tracker, emit_agent_event
from orchestrator.llm import llm_client
from orchestrator.state import AgentState
from orchestrator.tools import registry

logger = logging.getLogger("ChatGraph")


@agent_node_tracker("ingest_node", "Menerima pesan chat baru")
def ingest_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    input_data = state.get("input_data", {})
    query = input_data.get("query") or input_data.get("prompt") or "Halo"

    existing_messages = state.get("messages", [])
    new_messages = []
    if not existing_messages:
        new_messages = [HumanMessage(content=query)]

    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "status": "processing",
        "task_type": "chat",
        "messages": new_messages,
        "last_processed_by": settings.WORKER_ID,
        "execution_logs": [f"[{timestamp}] Task {task_id} ingested in Chat Agent."],
        "error": None,
    }


@agent_node_tracker("draft_node", "Penalaran AI & perumusan respon")
def reason_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    raw_messages = state.get("messages", [])

    formatted_messages = []
    for msg in raw_messages:
        if isinstance(msg, dict):
            formatted_messages.append(msg)
        elif isinstance(msg, HumanMessage):
            formatted_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            msg_dict = {"role": "assistant", "content": msg.content or ""}
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"]) if isinstance(tc["args"], dict) else tc["args"],
                        },
                    }
                    for tc in msg.tool_calls
                ]
            formatted_messages.append(msg_dict)
        elif isinstance(msg, ToolMessage):
            formatted_messages.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": str(msg.content),
            })

    openai_tools = registry.get_openai_tools()

    try:
        response = llm_client.generate(
            messages=formatted_messages,
            tools=openai_tools if openai_tools else None,
        )

        content = response["content"]
        tool_calls = response["tool_calls"]
        timestamp = datetime.now(timezone.utc).isoformat()

        ai_message_kwargs = {"content": content}
        if tool_calls:
            ai_message_kwargs["tool_calls"] = [
                {
                    "name": tc["function"]["name"],
                    "args": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"],
                    "id": tc["id"],
                }
                for tc in tool_calls
            ]

        ai_message = AIMessage(**ai_message_kwargs)
        return {
            "messages": [ai_message],
            "last_processed_by": settings.WORKER_ID,
            "execution_logs": [
                f"[{timestamp}] Reasoning finished (ToolCalls: {len(tool_calls)}, Provider: {response['provider']})."
            ],
            "error": None,
        }

    except Exception as exc:
        logger.error(f"Reasoning gagal: {exc}", exc_info=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        fallback_msg = AIMessage(content=f"LLM tidak tersedia saat ini ({exc}).")
        return {
            "messages": [fallback_msg],
            "last_processed_by": settings.WORKER_ID,
            "execution_logs": [f"[{timestamp}] Fallback reasoning triggered."],
            "error": str(exc),
        }


@agent_node_tracker("scrape_node", "Eksekusi pemanggilan tool")
def tool_execution_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    tool_messages = []
    execution_logs = []
    timestamp = datetime.now(timezone.utc).isoformat()

    pending_call = state.get("pending_tool_call")
    calls_to_execute = []

    if pending_call and state.get("is_approved"):
        calls_to_execute.append(pending_call)
    elif hasattr(last_message, "tool_calls") and last_message.tool_calls:
        calls_to_execute.extend(last_message.tool_calls)

    for tc in calls_to_execute:
        tool_name = tc["name"]
        tool_args = tc["args"]
        call_id = tc["id"]

        logger.info(f"Menjalankan tool '{tool_name}' dengan args: {tool_args}")
        exec_result = registry.execute(tool_name, tool_args)

        content_output = json.dumps(exec_result["output"]) if exec_result["success"] else f"Error: {exec_result['error']}"
        tool_messages.append(
            ToolMessage(
                content=content_output,
                tool_call_id=call_id,
                name=tool_name,
            )
        )
        execution_logs.append(f"[{timestamp}] Executed tool '{tool_name}' (Success={exec_result['success']}).")

    return {
        "messages": tool_messages,
        "pending_tool_call": None,
        "requires_approval": False,
        "is_approved": None,
        "last_processed_by": settings.WORKER_ID,
        "execution_logs": execution_logs,
    }


@agent_node_tracker("sop_validator_node", "Menunggu approval aksi")
def approval_checkpoint_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    pending = state.get("pending_tool_call", {})
    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "status": "waiting_approval",
        "requires_approval": True,
        "last_processed_by": settings.WORKER_ID,
        "execution_logs": [
            f"[{timestamp}] Menunggu approval manual untuk sensitive tool: '{pending.get('name')}'."
        ],
    }


@agent_node_tracker("publish_node", "Selesai memproses percakapan")
def complete_node(state: AgentState) -> dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    messages = state.get("messages", [])
    final_text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            final_text = msg.content
            break

    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "status": "completed",
        "result": {
            "summary": final_text or "Task completed without output text.",
            "total_messages": len(messages),
            "executed_by": settings.WORKER_ID,
        },
        "last_processed_by": settings.WORKER_ID,
        "execution_logs": [f"[{timestamp}] Task {task_id} completed by {settings.WORKER_ID}."],
    }


def route_after_reason(state: AgentState) -> Literal["tools", "await_approval", "complete"]:
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if state.get("is_approved") and state.get("pending_tool_call"):
        return "tools"

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tc in last_message.tool_calls:
            tool_name = tc.get("name")
            tool_def = registry.get(tool_name)
            if tool_def and tool_def.sensitive and not state.get("is_approved"):
                state["pending_tool_call"] = tc
                return "await_approval"
        return "tools"

    return "complete"


def create_chat_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("ingest", ingest_node)
    workflow.add_node("reason", reason_node)
    workflow.add_node("tools", tool_execution_node)
    workflow.add_node("await_approval", approval_checkpoint_node)
    workflow.add_node("complete", complete_node)

    workflow.add_edge(START, "ingest")
    workflow.add_edge("ingest", "reason")

    workflow.add_conditional_edges(
        "reason",
        route_after_reason,
        {"tools": "tools", "await_approval": "await_approval", "complete": "complete"},
    )

    workflow.add_edge("tools", "reason")
    workflow.add_edge("await_approval", END)
    workflow.add_edge("complete", END)

    checkpointer = get_checkpointer()
    return workflow.compile(checkpointer=checkpointer)


chat_graph_app = create_chat_graph()

