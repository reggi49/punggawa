"""Real-time event publisher for 3D Visualizer and agent monitoring via Redis Pub/Sub."""
import functools
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from config.settings import settings
from orchestrator.connections import redis_client

logger = logging.getLogger("AgentEvents")

RECENT_EVENTS_KEY = "agent:events:recent"
MAX_RECENT_EVENTS = 50


def emit_agent_event(
    thread_id: str,
    node: str,
    status: str,
    message: str = "",
    details: dict[str, Any] | None = None,
) -> bool:
    """
    Publish an agent event to Redis Pub/Sub channel (Fire-and-forget).
    Non-blocking and zero-lag for the LangGraph worker.
    """
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        agent_name = (details or {}).get("agent_name")
        payload = {
            "thread_id": str(thread_id),
            "node": str(node),
            "status": str(status),
            "message": str(message) if message else f"Node {node} {status}",
            "timestamp": timestamp,
            "worker_id": settings.WORKER_ID,
            "agent_name": agent_name,
            "details": details or {},
        }
        raw_json = json.dumps(payload)

        # Publish ke Redis Pub/Sub channel
        redis_client.publish(settings.EVENT_CHANNEL, raw_json)

        # Simpan event terakhir di Redis list untuk sinkronisasi awal frontend
        try:
            pipe = redis_client.pipeline(transaction=False)
            pipe.lpush(RECENT_EVENTS_KEY, raw_json)
            pipe.ltrim(RECENT_EVENTS_KEY, 0, MAX_RECENT_EVENTS - 1)
            pipe.execute()
        except Exception:
            pass

        return True
    except Exception as exc:
        logger.warning(f"Gagal mengirim agent event: {exc}")
        return False


def emit_idle_event(message: str = "Worker is idle waiting for tasks") -> bool:
    """Mengirim sinyal worker kembali ke status IDLE."""
    return emit_agent_event(
        thread_id="system",
        node="IDLE",
        status="idle",
        message=message,
        details={"worker_id": settings.WORKER_ID, "agent_name": "Squad"},
    )


def agent_node_tracker(node_name: str, description: str = ""):
    """
    Decorator untuk LangGraph node yang otomatis memancarkan status:
    - started pada saat node mulai
    - completed saat node selesai sukses
    - failed_node saat terjadi error atau status == 'failed'
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(state: dict[str, Any], *args, **kwargs):
            task_id = state.get("task_id", "unknown")
            thread_id = state.get("thread_id") or task_id
            task_type = (
                state.get("task_type")
                or (state.get("input_data") or {}).get("task_type")
                or ("dongeng" if "dongeng" in str(thread_id).lower() or "dongeng" in str(task_id).lower() else "article")
            )

            is_job_task = str(task_type).lower() in ("job", "job_hunt", "job_ops", "career", "career_ops", "job_hunter") or "job" in str(thread_id).lower() or "job" in str(task_id).lower()

            # Tentukan aktor agen berdasarkan node dan tipe task
            if node_name in (
                "ingest_job_node",
                "fetch_job_node",
                "evaluate_fit_node",
                "draft_application_node",
                "review_critique_node",
                "generate_prep_node",
                "save_job_node",
            ) or is_job_task:
                agent_name = "Clara"
            elif node_name in (
                "curate_video_node",
                "curate_node",
                "render_cover_node",
                "post_cms_node",
                "trigger_notification_node",
            ):
                agent_name = "Usagi"
            elif node_name in ("sop_validator_node", "await_approval"):
                agent_name = "Bay-Zero"
            elif node_name in ("housekeeping", "housekeeping_node"):
                agent_name = "Janitor Droid"
            elif node_name in ("publish_node", "complete_node"):
                agent_name = "Clara" if is_job_task else ("Usagi" if task_type == "dongeng" else "Stark")
            else:
                agent_name = "Clara" if is_job_task else ("Usagi" if task_type == "dongeng" else "Stark")

            # Extract basic context for HUD
            input_data = state.get("input_data", {})
            topic = (
                input_data.get("topic")
                or input_data.get("query")
                or state.get("category")
                or ""
            )

            event_details = {
                "agent_name": agent_name,
                "topic": topic,
                "task_id": task_id,
                "task_type": task_type,
                "action_type": task_type,
            }

            # Emit node started
            emit_agent_event(
                thread_id=thread_id,
                node=node_name,
                status="started",
                message=f"Starting {description or node_name}",
                details=event_details,
            )

            try:
                result = func(state, *args, **kwargs)

                # Cek jika node mengembalikan status gagal
                if isinstance(result, dict) and (
                    result.get("status") == "failed" or result.get("error")
                ):
                    err_msg = str(result.get("error") or "Unknown error")
                    emit_agent_event(
                        thread_id=thread_id,
                        node="failed_node",
                        status="failed",
                        message=f"Error in {node_name}: {err_msg}",
                        details={
                            **event_details,
                            "error": err_msg,
                            "original_node": node_name,
                        },
                    )
                else:
                    emit_agent_event(
                        thread_id=thread_id,
                        node=node_name,
                        status="completed",
                        message=f"Completed {description or node_name}",
                        details=event_details,
                    )
                return result
            except Exception as exc:
                emit_agent_event(
                    thread_id=thread_id,
                    node="failed_node",
                    status="failed",
                    message=f"Fatal exception in {node_name}: {str(exc)}",
                    details={
                        **event_details,
                        "error": str(exc),
                        "original_node": node_name,
                    },
                )
                raise
        return wrapper
    return decorator
