"""Real-time event publisher for 3D Visualizer and persistent agent execution logging."""
import functools
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from config.settings import settings
from orchestrator.connections import redis_client

logger = logging.getLogger("AgentEvents")

RECENT_EVENTS_KEY = "agent:events:recent"
MAX_RECENT_EVENTS = 50

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))


def infer_agent_name(node: str, thread_id: str = "", details: dict[str, Any] | None = None) -> str:
    """Menentukan aktor agen dari node, thread_id, atau payload details."""
    det = details or {}
    explicit = det.get("agent_name")
    if explicit and explicit not in ("Squad", ""):
        return explicit

    node_lower = (node or "").lower()
    th_lower = (thread_id or "").lower()

    if any(k in node_lower for k in ("bayzero", "sop_validator", "audit", "schedule_audit")):
        return "Bay-Zero"
    if any(k in node_lower for k in ("janitor", "cleanup", "housekeeping")):
        return "Janitor Droid"
    if any(k in th_lower or k in node_lower for k in ("job", "career", "clara", "scout")):
        return "Clara"
    if "dongeng" in th_lower or any(k in node_lower for k in ("curate_video", "render_cover")):
        return "Usagi"
    if any(k in th_lower or k in node_lower for k in ("article", "stark", "trend", "github", "news")):
        return "Stark"

    return explicit or "Squad"


def persist_agent_log(
    log_id: str,
    thread_id: str,
    agent_name: str,
    node: str,
    status: str,
    message: str,
    details: dict[str, Any] | None,
    created_at: datetime,
) -> bool:
    """Simpan log eksekusi ke PostgreSQL agent_execution_logs secara permanen."""
    if node.upper() in ("IDLE", "STREAM_INIT", "WS_INIT"):
        return False
    try:
        from orchestrator.connections import postgres_pool
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_execution_logs (
                        id, thread_id, agent_name, node, status, message, details, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        log_id,
                        str(thread_id),
                        str(agent_name or "Squad"),
                        str(node),
                        str(status),
                        str(message),
                        json.dumps(details or {}),
                        created_at,
                    ),
                )
        return True
    except Exception as exc:
        logger.debug(f"Gagal mencatat log ke DB: {exc}")
        return False


def get_persisted_logs(
    limit: int = 100,
    agent: str | None = None,
    date: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """
    Mengambil riwayat log eksekusi agen dari PostgreSQL agent_execution_logs.
    Mendukung filter berdasarkan agent, date (YYYY-MM-DD WIB), dan status.
    """
    results: list[dict[str, Any]] = []
    try:
        from orchestrator.connections import postgres_pool
        query = """
            SELECT id, thread_id, agent_name, node, status, message, details, created_at
            FROM agent_execution_logs
            WHERE 1=1
        """
        params: list[Any] = []

        if agent and agent.lower() != "all":
            query += " AND LOWER(agent_name) LIKE LOWER(%s)"
            params.append(f"%{agent.strip()}%")

        if status and status.lower() != "all":
            query += " AND LOWER(status) = LOWER(%s)"
            params.append(status.strip())

        if date:
            # Filter tanggal WIB (UTC + 7 jam)
            query += " AND ((created_at AT TIME ZONE 'UTC' + INTERVAL '7 hours')::date) = %s::date"
            params.append(date.strip())

        query += " ORDER BY created_at DESC LIMIT %s;"
        params.append(limit)

        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                for r in rows:
                    l_id, thread_id, agent_name, node, st, msg, det_raw, created_at = r
                    det = det_raw if isinstance(det_raw, dict) else json.loads(det_raw or "{}")

                    # Hitung representasi waktu WIB
                    dt_wib = created_at.astimezone(WIB) if created_at else datetime.now(WIB)
                    today_wib = datetime.now(WIB).date()
                    is_today = (dt_wib.date() == today_wib)

                    time_fmt = dt_wib.strftime("%H:%M:%S") if is_today else dt_wib.strftime("%d/%m %H:%M")

                    results.append({
                        "id": l_id,
                        "thread_id": thread_id,
                        "agent_name": agent_name,
                        "node": node,
                        "status": st,
                        "message": msg,
                        "details": det,
                        "result_url": det.get("result_url") or det.get("url"),
                        "error": det.get("error"),
                        "created_at": created_at.isoformat() if created_at else None,
                        "timestamp": created_at.isoformat() if created_at else None,
                        "time": time_fmt,
                        "date": dt_wib.strftime("%Y-%m-%d"),
                        "display_time": dt_wib.strftime("%a, %d %b %H:%M:%S WIB"),
                    })
    except Exception as exc:
        logger.error(f"Gagal mengambil logs persisten dari database: {exc}")
    return results


def emit_agent_event(
    thread_id: str,
    node: str,
    status: str,
    message: str = "",
    details: dict[str, Any] | None = None,
) -> bool:
    """
    Publish an agent event to Redis Pub/Sub channel (real-time stream)
    dan simpan ke PostgreSQL agent_execution_logs (riwayat permanen lintas sesi).
    Non-blocking dan aman untuk LangGraph worker.
    """
    try:
        now_dt = datetime.now(timezone.utc)
        timestamp = now_dt.isoformat()
        resolved_agent_name = infer_agent_name(node, thread_id, details)

        log_id = (details or {}).get("log_id") or f"log_{uuid.uuid4().hex[:12]}"
        det = dict(details or {})
        det["log_id"] = log_id
        if "agent_name" not in det or det["agent_name"] in ("Squad", ""):
            det["agent_name"] = resolved_agent_name

        payload = {
            "id": log_id,
            "thread_id": str(thread_id),
            "node": str(node),
            "status": str(status),
            "message": str(message) if message else f"Node {node} {status}",
            "timestamp": timestamp,
            "worker_id": settings.WORKER_ID,
            "agent_name": resolved_agent_name,
            "details": det,
        }
        raw_json = json.dumps(payload)

        # 1. Publish ke Redis Pub/Sub channel
        redis_client.publish(settings.EVENT_CHANNEL, raw_json)

        # 2. Simpan event terakhir di Redis list untuk sinkronisasi awal frontend
        try:
            pipe = redis_client.pipeline(transaction=False)
            pipe.lpush(RECENT_EVENTS_KEY, raw_json)
            pipe.ltrim(RECENT_EVENTS_KEY, 0, MAX_RECENT_EVENTS - 1)
            pipe.execute()
        except Exception:
            pass

        # 3. Simpan permanen ke PostgreSQL
        persist_agent_log(
            log_id=log_id,
            thread_id=thread_id,
            agent_name=resolved_agent_name,
            node=node,
            status=status,
            message=payload["message"],
            details=det,
            created_at=now_dt,
        )

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
                agent_name = "Scout"
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
                agent_name = "Scout" if is_job_task else ("Usagi" if task_type == "dongeng" else "Stark")
            else:
                agent_name = "Scout" if is_job_task else ("Usagi" if task_type == "dongeng" else "Stark")

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
