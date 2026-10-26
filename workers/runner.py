"""Autonomous Worker Entrypoint for processing tasks from Redis Queue."""
import json
import logging
import signal
import time
from typing import Any

import redis

from config.settings import settings
from orchestrator.connections import postgres_pool, redis_client
from orchestrator.events import emit_agent_event, emit_idle_event
from orchestrator.graphs import get_graph
from orchestrator.lock import LockAcquisitionError, RedisDistributedLock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(f"Worker-{settings.WORKER_ID}")

RETRY_DELAY_SECONDS = 5


def _handle_task_success(
    schedule_id: str | None,
    thread_id: str,
    agent_name: str,
    title: str,
    final_state: dict[str, Any],
):
    """Mencatat status keberhasilan task ke content_schedules dan memancarkan event sukses."""
    result_url = None
    published_ids = final_state.get("published_ids") or {}
    cms_res = final_state.get("cms_post_result") or {}
    curation_res = final_state.get("curation_result") or {}

    if published_ids.get("id"):
        result_url = f"https://www.kodeabc.tech/article/{published_ids['id']}"
    elif cms_res.get("url"):
        result_url = cms_res["url"]
    elif curation_res.get("skip"):
        result_url = f"Dilewati ({curation_res.get('reason', 'skip')})"
    elif final_state.get("saved_job_id"):
        job_id = final_state.get("saved_job_id")
        eval_res = final_state.get("evaluation_result") or {}
        score = eval_res.get("fit_score", 1)
        result_url = f"Evaluasi Loker #{job_id} (Skor: {score}/5)"

    if schedule_id:
        try:
            with postgres_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE content_schedules
                        SET status = 'completed', completed_at = NOW(), result_url = %s, error_message = NULL
                        WHERE id = %s;
                        """,
                        (result_url, schedule_id),
                    )
                    logger.info(f"✅ Schedule '{schedule_id}' ditandai COMPLETED di PostgreSQL (result_url='{result_url}').")
        except Exception as db_err:
            logger.warning(f"Gagal memperbarui status schedule {schedule_id}: {db_err}")

    emit_agent_event(
        thread_id=thread_id,
        node="publish_node",
        status="completed",
        message=f"Sukses menerbitkan: '{title}'",
        details={
            "schedule_id": schedule_id,
            "agent_name": agent_name,
            "title": title,
            "result_url": result_url,
        },
    )


def _handle_task_failure(
    schedule_id: str | None,
    thread_id: str,
    agent_name: str,
    title: str,
    error_reason: str,
):
    """Mencatat status kegagalan beserta alasan lengkap ke content_schedules dan memancarkan event failed."""
    logger.error(f"❌ [TASK FAILURE] {agent_name} gagal memproses '{title}': {error_reason}")
    is_duplicate = any(w in error_reason.lower() for w in ("duplikat", "duplicate", "already_in_cms", "already exists"))

    if schedule_id:
        try:
            with postgres_pool.connection() as conn:
                with conn.cursor() as cur:
                    saved_err = f"Dilewati otomatis (Duplikat): {error_reason}" if is_duplicate else error_reason
                    cur.execute(
                        """
                        UPDATE content_schedules
                        SET status = 'failed', completed_at = NOW(), error_message = %s
                        WHERE id = %s;
                        """,
                        (saved_err, schedule_id),
                    )
                    logger.info(f"⚠️ Schedule '{schedule_id}' ditandai FAILED di PostgreSQL (Duplikat={is_duplicate}).")
        except Exception as db_err:
            logger.warning(f"Gagal memperbarui status failed schedule {schedule_id}: {db_err}")

    if is_duplicate:
        # Emit event dilewati (skipped) khusus duplikasi agar kru langsung auto-advance
        emit_agent_event(
            thread_id=thread_id,
            node="sop_validator_node",
            status="skipped",
            message=f"⏭️ Melewati '{title}' karena sudah pernah terbit di CMS. Kru langsung lanjut ke task berikutnya agar kuota harian terpenuhi.",
            details={
                "schedule_id": schedule_id,
                "agent_name": "Bay-Zero",
                "title": title,
                "error": error_reason,
                "action": "auto_advance",
            },
        )
    else:
        emit_agent_event(
            thread_id=thread_id,
            node="failed_node",
            status="failed",
            message=f"❌ Gagal memproses '{title}'. Alasan: {error_reason}",
            details={
                "schedule_id": schedule_id,
                "agent_name": agent_name,
                "title": title,
                "error": error_reason,
            },
        )


def poll_and_dispatch_due_schedules() -> int:
    """
    Schedule Ticker: Memeriksa apakah ada task di content_schedules yang
    berstatus pending dan scheduled_at <= NOW().
    Menandai in_progress, mengisi started_at, lalu mendorong payload ke antrean Redis TASK_QUEUE_NAME.
    """
    dispatched = 0
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                # 0. Auto-recovery: Pulihkan jadwal zombie yang menggantung in_progress lebih dari 30 menit (akibat worker restart/mati)
                cur.execute(
                    """
                    UPDATE content_schedules
                    SET status = 'failed', completed_at = NOW(), error_message = 'Task timeout: worker terhenti atau task menggantung saat in_progress (>30 menit).'
                    WHERE status = 'in_progress' AND started_at < NOW() - INTERVAL '30 minutes';
                    """
                )

                cur.execute(
                    """
                    SELECT id, agent_name, task_type, title, payload
                    FROM content_schedules
                    WHERE status = 'pending' AND scheduled_at <= NOW()
                    ORDER BY scheduled_at ASC
                    FOR UPDATE SKIP LOCKED;
                    """
                )
                due_tasks = cur.fetchall()
                for s_id, agent_name, task_type, title, payload_raw in due_tasks:
                    payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw or "{}")
                    payload["schedule_id"] = s_id
                    if "input_data" in payload and isinstance(payload["input_data"], dict):
                        payload["input_data"]["schedule_id"] = s_id

                    cur.execute(
                        """
                        UPDATE content_schedules
                        SET status = 'in_progress', started_at = NOW()
                        WHERE id = %s;
                        """,
                        (s_id,),
                    )
                    redis_client.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))
                    dispatched += 1
                    logger.info(
                        f"⏰ [SCHEDULE TICKER] Memulai pengerjaan jadwal: '{s_id}' ({agent_name}: '{title}')"
                    )

                    emit_agent_event(
                        thread_id=payload.get("thread_id", s_id),
                        node="task_start",
                        status="in_progress",
                        message=f"Memulai pengerjaan jadwal: {title}",
                        details={
                            "schedule_id": s_id,
                            "agent_name": agent_name,
                            "task_type": task_type,
                            "title": title,
                        },
                    )
    except Exception as exc:
        logger.warning(f"Error checking due schedules: {exc}")
    return dispatched


class GracefulShutdownHandler:
    """Menangani sinyal SIGINT dan SIGTERM agar worker berhenti dengan rapi."""
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        logger.info(
            f"Menerima signal {signum}. Menyelesaikan task aktif sebelum mematikan worker..."
        )
        self.kill_now = True


def execute_graph_with_lock(task_payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Mengeksekusi LangGraph secara atomic dengan membungkusnya dalam Redis Distributed Lock.
    """
    task_id = task_payload.get("task_id")
    thread_id = task_payload.get("thread_id", task_id)

    if not thread_id:
        logger.error(f"Payload tidak memiliki thread_id atau task_id: {task_payload}")
        return None

    lock_key = f"lock:thread:{thread_id}"
    config = {"configurable": {"thread_id": thread_id}}

    input_data = task_payload.get("input_data") or {}
    schedule_id = task_payload.get("schedule_id") or input_data.get("schedule_id")
    task_type = task_payload.get("task_type") or input_data.get("task_type")
    is_job = str(task_type).lower() in ("job", "job_hunt", "job_ops", "career", "career_ops", "job_hunter")
    agent_name = "Scout" if is_job else ("Usagi" if task_type == "dongeng" else "Stark")
    title = (
        task_payload.get("title")
        or input_data.get("topic")
        or input_data.get("query")
        or f"Task {task_id}"
    )

    try:
        # Acquire Distributed Lock dengan fail-fast (acquire_timeout=0.0)
        with RedisDistributedLock(
            lock_key=lock_key,
            ttl_seconds=settings.LOCK_TTL_SECONDS,
            acquire_timeout=0.0,
        ):
            logger.info(f"Lock berhasil didapatkan untuk thread_id: '{thread_id}'.")

            # Pilih graph yang tepat dari Registry of Graphs
            target_graph = get_graph(task_type)
            logger.info(f"Menggunakan execution graph untuk tipe: '{task_type or 'default'}'")

            action = task_payload.get("action", "start")

            if action == "resume":
                # Resume task approval (Human-in-the-loop)
                is_approved = bool(task_payload.get("approved", True))
                logger.info(
                    f"Melanjutkan task checkpoint '{thread_id}' dengan approval status: {is_approved}"
                )

                target_graph.update_state(
                    config,
                    {
                        "is_approved": is_approved,
                        "status": "processing" if is_approved else "failed",
                        "execution_logs": [
                            f"Task resumed by {settings.WORKER_ID} with approval={is_approved}"
                        ],
                    },
                )
                final_state = target_graph.invoke(None, config=config)

            else:
                # Memulai task baru
                logger.info(f"Memulai eksekusi task baru '{thread_id}' ({agent_name}: '{title}')...")
                input_data = task_payload.get("input_data", {})
                initial_state = {
                    "task_id": task_id,
                    "thread_id": thread_id,
                    "task_type": task_type,
                    "status": "pending",
                    "input_data": input_data,
                    "target_urls": input_data.get("target_urls") or input_data.get("urls"),
                    "category": input_data.get("category", "technology"),
                    "scraped_content": None,
                    "url_references": None,
                    "dual_content": None,
                    "dual_images": None,
                    "published_ids": None,
                    "trend_source_data": None,
                    "trend_selected_item": None,
                    "video_id": input_data.get("video_id"),
                    "video_metadata": None,
                    "curation_result": None,
                    "thumbnail_path": None,
                    "cms_post_result": None,
                    "execution_logs": [
                        f"Task queued and picked up by worker '{settings.WORKER_ID}'"
                    ],
                    "result": None,
                    "requires_approval": False,
                    "is_approved": None,
                    "last_processed_by": None,
                    "error": None,
                }
                final_state = target_graph.invoke(initial_state, config=config)

            # Evaluasi Hasil Eksekusi LangGraph (Success vs Failure with Reason)
            is_failed = final_state.get("status") == "failed" or bool(final_state.get("error"))
            if is_failed:
                error_reason = final_state.get("error") or "LangGraph execution failed without explicit error code."
                _handle_task_failure(schedule_id, thread_id, agent_name, title, error_reason)
            else:
                _handle_task_success(schedule_id, thread_id, agent_name, title, final_state)

            # Auto-rebalance Bay-Zero: Jika task terjadwal selesai (terutama jika selesai lebih cepat),
            # segera pindai dan majukan tugas berikutnya agar hari depan tidak pernah nganggur.
            if schedule_id:
                try:
                    from scripts.planner import rebalance_and_replenish_schedules
                    rebalance_and_replenish_schedules(days_ahead=7)
                except Exception as reb_err:
                    logger.warning(f"Auto-rebalance error setelah task '{thread_id}': {reb_err}")

            logger.info(
                f"Selesai memproses thread_id '{thread_id}'. Status akhir: {final_state.get('status')}"
            )
            return final_state

    except LockAcquisitionError:
        # Race condition terdeteksi: task sedang dikunci oleh worker lain
        logger.warning(
            f"[RACE PREVENTED] Thread '{thread_id}' sedang aktif di worker lain. Mengembalikan ke antrean..."
        )
        time.sleep(1)
        redis_client.lpush(settings.TASK_QUEUE_NAME, json.dumps(task_payload))
        return None

    except Exception as exc:
        error_reason = str(exc)
        logger.error(
            f"Terjadi error fatal saat memproses thread_id '{thread_id}': {error_reason}",
            exc_info=True,
        )
        _handle_task_failure(schedule_id, thread_id, agent_name, title, error_reason)
        return None


def run_worker():
    """
    Main loop polling Redis queue menggunakan BLPOP.
    """
    shutdown_handler = GracefulShutdownHandler()
    logger.info(
        f"🚀 Worker '{settings.WORKER_ID}' aktif mendengarkan queue '{settings.TASK_QUEUE_NAME}'..."
    )
    # Emit idle state saat worker siap menerima antrean
    emit_idle_event("Worker is ready and waiting for tasks")

    # Inisialisasi timer auto-cleanup database (setiap 24 jam / 86400 detik)
    last_cleanup_timestamp = 0.0
    CLEANUP_INTERVAL_SECONDS = 86400

    # Inisialisasi timer schedule ticker Bay-Zero (setiap 60 detik)
    last_schedule_check_timestamp = 0.0
    SCHEDULE_CHECK_INTERVAL_SECONDS = 60.0

    # Inisialisasi timer Anti-Idle Rebalancer Bay-Zero (setiap 300 detik / 5 menit)
    last_rebalance_timestamp = 0.0
    REBALANCE_INTERVAL_SECONDS = 300.0

    # Inisialisasi timer uptime health check microservice (setiap 3600 detik / 1 jam)
    last_uptime_check_timestamp = 0.0
    UPTIME_CHECK_INTERVAL_SECONDS = 3600.0
    last_uptime_status = None

    while not shutdown_handler.kill_now:
        try:
            now = time.time()

            # 1. Polling berkala jadwal content_schedules yang jatuh tempo (scheduled_at <= NOW())
            if now - last_schedule_check_timestamp >= SCHEDULE_CHECK_INTERVAL_SECONDS:
                last_schedule_check_timestamp = now
                try:
                    dispatched_count = poll_and_dispatch_due_schedules()
                    if dispatched_count > 0:
                        logger.info(
                            f"⏰ [SCHEDULE TICKER] Berhasil mendispatch {dispatched_count} jadwal yang jatuh tempo ke antrean."
                        )
                except Exception as s_err:
                    logger.warning(f"Error checking due schedules: {s_err}")

            # 1b. Anti-Idle Rebalancer & Auto-Replenish Bay-Zero (setiap 5 menit / 300 detik)
            if now - last_rebalance_timestamp >= REBALANCE_INTERVAL_SECONDS:
                last_rebalance_timestamp = now
                try:
                    from scripts.planner import rebalance_and_replenish_schedules
                    rebalance_and_replenish_schedules(days_ahead=7)
                except Exception as r_err:
                    logger.warning(f"Error running periodic Anti-Idle rebalance: {r_err}")

            # 2. Auto-cleanup checkpoint PostgreSQL lama (> 3 hari) secara periodik
            if now - last_cleanup_timestamp >= CLEANUP_INTERVAL_SECONDS:
                last_cleanup_timestamp = now
                try:
                    from scripts.cleanup import clean_old_checkpoints
                    logger.info("Menjalankan periodic auto-cleanup database PostgreSQL (retensi 3 hari)...")
                    emit_agent_event(
                        thread_id="system",
                        node="housekeeping",
                        status="in_progress",
                        message="Janitor Bot aktif: Menyapu sisa checkpoint & memangkas data...",
                    )
                    clean_res = clean_old_checkpoints(days=3)
                    logger.info(
                        f"Periodic auto-cleanup selesai: {clean_res.get('deleted_threads_count', 0)} thread dibersihkan "
                        f"({clean_res.get('deleted_checkpoints', 0)} checkpoints, "
                        f"{clean_res.get('deleted_blobs', 0)} blobs, "
                        f"{clean_res.get('deleted_writes', 0)} writes)."
                    )
                    emit_agent_event(
                        thread_id="system",
                        node="housekeeping",
                        status="completed",
                        message="Pembersihan tuntas. Kembali ke docking station.",
                    )
                except Exception as c_err:
                    logger.warning(f"Gagal menjalankan periodic auto-cleanup database: {c_err}")

            # 3. Uptime health check microservice eksternal (setiap 1 jam / 3600 detik)
            if now - last_uptime_check_timestamp >= UPTIME_CHECK_INTERVAL_SECONDS:
                last_uptime_check_timestamp = now
                try:
                    from orchestrator.tools.uptime_checker import (
                        run_all_health_checks,
                        REDIS_SERVICES_HEALTH_KEY,
                        REDIS_SERVICES_HEALTH_TTL,
                    )
                    health_res = run_all_health_checks()
                    redis_client.setex(
                        REDIS_SERVICES_HEALTH_KEY,
                        REDIS_SERVICES_HEALTH_TTL,
                        json.dumps(health_res),
                    )
                    current_status = health_res.get("overall_status", "healthy")
                    logger.info(
                        f"🩺 [UPTIME MONITOR] Health check selesai. Status keseluruhan: {current_status.upper()}"
                    )

                    if current_status == "degraded":
                        down_services = [
                            s["name"] for s in health_res.get("services", []) if s["status"] != "healthy"
                        ]
                        emit_agent_event(
                            thread_id="system",
                            node="uptime_alert",
                            status="failed",
                            message=f"⚠️ Peringatan Service Down: Satu atau lebih microservice tidak merespons! ({', '.join(down_services)})",
                            details={
                                "agent_name": "Bay-Zero",
                                "health": health_res,
                            },
                        )
                    elif last_uptime_status == "degraded" and current_status == "healthy":
                        emit_agent_event(
                            thread_id="system",
                            node="uptime_alert",
                            status="completed",
                            message="✅ Seluruh microservice normal kembali.",
                            details={
                                "agent_name": "Bay-Zero",
                                "health": health_res,
                            },
                        )
                        emit_idle_event("Kantor virtual siap. Seluruh microservice normal.")
                    last_uptime_status = current_status
                except Exception as u_err:
                    logger.warning(f"Error running uptime health check: {u_err}")

            # BLPOP memblokir koneksi secara efisien hingga task masuk
            task_raw = redis_client.blpop(settings.TASK_QUEUE_NAME, timeout=2)

            if not task_raw:
                continue

            _, payload_str = task_raw
            task_payload = json.loads(payload_str)

            logger.info(f"Menerima task dari antrean: {task_payload.get('task_id')}")
            execute_graph_with_lock(task_payload)

            # Segera periksa dan dispatch jadwal due berikutnya agar agen langsung lanjut tanpa nganggur
            try:
                poll_and_dispatch_due_schedules()
            except Exception:
                pass

            # Setelah task selesai, kembalikan karakter ke posisi IDLE
            emit_idle_event("Task processing finished. Returning to IDLE.")

        except redis.RedisError as r_err:
            logger.error(
                f"Redis connection error: {r_err}. Mencoba menyambung kembali dalam {RETRY_DELAY_SECONDS} detik..."
            )
            time.sleep(RETRY_DELAY_SECONDS)
        except Exception as err:
            logger.error(f"Unexpected worker error: {err}", exc_info=True)
            time.sleep(1)

    logger.info(f"Worker '{settings.WORKER_ID}' telah dimatikan dengan aman.")
    try:
        from orchestrator.connections import postgres_pool
        postgres_pool.close()
    except Exception:
        pass


if __name__ == "__main__":
    run_worker()

