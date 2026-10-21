"""
Real-time Streaming Gateway Server for Punggawa 3D Office Simulation.
Exposes SSE (/api/stream), WebSocket (/api/ws), and Health Check (/api/health).
Bridges Redis Pub/Sub (channel 'agent:events') to frontend visualizer.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import redis.asyncio as aioredis
import uvicorn

from config.settings import settings
from orchestrator.connections import postgres_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [StreamServer] %(message)s",
)
logger = logging.getLogger("StreamServer")

# Async Redis client for pub/sub
async_redis_client: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global async_redis_client
    logger.info(f"Connecting async Redis client to {settings.REDIS_URL}...")
    async_redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=15.0,
    )
    logger.info("✅ Redis connected successfully.")
    yield
    if async_redis_client:
        logger.info("Closing async Redis client...")
        await async_redis_client.aclose()


app = FastAPI(
    title="Punggawa 3D Office Event Stream Gateway",
    description="Real-time SSE and WebSocket stream gateway bridging LangGraph agent events to Three.js frontend.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Vite frontend dev server and external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class DispatchRequest(BaseModel):
    prompt: str = Field("", description="Prompt or topic for the agent")
    type: str = Field("article", description="Task type: 'article', 'dongeng', or 'chat'")
    category: str = Field("technology", description="Article category")
    urls: str = Field("", description="Reference target URLs separated by comma")
    video_id: str | None = Field(None, description="YouTube Video ID for dongeng")
    dry_run: bool = Field(False, description="Dry-run mode (render only, do not publish)")
    thread_id: str | None = Field(None, description="Custom thread ID")
    source: str | None = Field(None, description="Trend source: 'github' or 'gnews'")
    lang: str | None = Field(None, description="Programming language for GitHub trending")
    query: str | None = Field(None, description="Search query for Google News RSS")


def generate_auth_token(username: str) -> str:
    """Creates a signed HMAC auth token valid for 7 days."""
    expire_ts = int(time.time()) + 86400 * 7
    raw_payload = f"{username}:{expire_ts}"
    signature = hmac.new(
        settings.AUTH_SECRET_KEY.encode(),
        raw_payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{raw_payload}:{signature}"


def verify_auth_token(token: str | None) -> bool:
    """Verifies that the HMAC auth token is valid and unexpired."""
    if not token:
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    username, expire_ts_str, signature = parts
    try:
        expire_ts = int(expire_ts_str)
        if time.time() > expire_ts:
            return False
    except ValueError:
        return False
    expected_payload = f"{username}:{expire_ts_str}"
    expected_sig = hmac.new(
        settings.AUTH_SECRET_KEY.encode(),
        expected_payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_sig) and username == settings.ADMIN_USERNAME


@app.get("/api/health")
async def health_check():
    """Checks worker status, Redis connectivity, and Postgres pool status."""
    health_status: dict[str, Any] = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker_id": settings.WORKER_ID,
        "event_channel": settings.EVENT_CHANNEL,
        "queue_name": settings.TASK_QUEUE_NAME,
        "checks": {},
    }

    # Check Redis
    try:
        if async_redis_client:
            t0 = time.perf_counter()
            pong = await async_redis_client.ping()
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            health_status["checks"]["redis"] = {
                "status": "connected" if pong else "error",
                "latency_ms": latency_ms,
            }
        else:
            health_status["checks"]["redis"] = {"status": "uninitialized"}
    except Exception as exc:
        health_status["checks"]["redis"] = {"status": "error", "error": str(exc)}
        health_status["status"] = "degraded"

    # Check Postgres pool
    try:
        stats = postgres_pool.get_stats()
        health_status["checks"]["postgres"] = {
            "status": "connected",
            "pool_size": stats.get("pool_size", 0),
            "pool_available": stats.get("pool_available", 0),
        }
    except Exception as exc:
        health_status["checks"]["postgres"] = {"status": "error", "error": str(exc)}
        health_status["status"] = "degraded"

    return JSONResponse(content=health_status)


@app.get("/api/events/recent")
async def get_recent_events():
    """Returns recent agent events cached in Redis list."""
    if not async_redis_client:
        return []
    try:
        raw_events = await async_redis_client.lrange("agent:events:recent", 0, 49)
        parsed = []
        for item in raw_events:
            try:
                parsed.append(json.loads(item))
            except Exception:
                continue
        return parsed
    except Exception as exc:
        logger.error(f"Failed to fetch recent events: {exc}")
        return []


async def sse_event_generator(request: Request) -> AsyncGenerator[str, None]:
    """Generator streaming events via SSE from Redis Pub/Sub."""
    if not async_redis_client:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Redis client not initialized'})}\n\n"
        return

    pubsub = async_redis_client.pubsub()
    await pubsub.subscribe(settings.EVENT_CHANNEL)
    logger.info(f"Client connected to SSE stream (channel: {settings.EVENT_CHANNEL})")

    # Send initial connection handshake
    initial_event = {
        "thread_id": "system",
        "node": "STREAM_INIT",
        "status": "connected",
        "message": "Connected to Punggawa 3D Office Event Stream",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker_id": settings.WORKER_ID,
    }
    yield f"data: {json.dumps(initial_event)}\n\n"

    # Send the most recent event if available
    try:
        recent_raw = await async_redis_client.lindex("agent:events:recent", 0)
        if recent_raw:
            recent_data = json.loads(recent_raw)
            yield f"data: {json.dumps(recent_data)}\n\n"
        else:
            # Send default idle event so avatar starts in idle state
            default_idle = {
                "thread_id": "system",
                "node": "IDLE",
                "status": "idle",
                "message": "Office is calm. Worker waiting for tasks.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(default_idle)}\n\n"
    except Exception:
        pass

    try:
        while True:
            # Check client disconnection
            if await request.is_disconnected():
                logger.info("SSE client disconnected.")
                break

            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message.get("type") == "message":
                data_str = message.get("data", "{}")
                yield f"data: {data_str}\n\n"
            else:
                # Keep-alive heartbeat comment every second to prevent timeouts
                yield ": keep-alive\n\n"
                await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        logger.info("SSE stream cancelled by client.")
    except Exception as exc:
        logger.error(f"Error in SSE stream generator: {exc}")
    finally:
        await pubsub.unsubscribe(settings.EVENT_CHANNEL)
        await pubsub.aclose()


@app.get("/api/stream")
async def stream_events(request: Request):
    """
    SSE endpoint streaming real-time agent events.
    Frontend connects using EventSource('/api/stream').
    """
    return StreamingResponse(
        sse_event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
        },
    )


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional streaming.
    """
    await websocket.accept()
    logger.info("Client connected via WebSocket.")

    if not async_redis_client:
        await websocket.send_json({"error": "Redis not available"})
        await websocket.close()
        return

    pubsub = async_redis_client.pubsub()
    await pubsub.subscribe(settings.EVENT_CHANNEL)

    # Send handshake
    await websocket.send_json({
        "thread_id": "system",
        "node": "WS_INIT",
        "status": "connected",
        "message": "WebSocket connected to Punggawa 3D Office Event Gateway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Send recent event or default IDLE
    try:
        recent_raw = await async_redis_client.lindex("agent:events:recent", 0)
        if recent_raw:
            await websocket.send_text(recent_raw)
        else:
            await websocket.send_json({
                "thread_id": "system",
                "node": "IDLE",
                "status": "idle",
                "message": "Office is calm. Worker waiting for tasks.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass

    async def redis_listener():
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    await websocket.send_text(msg.get("data", "{}"))
                await asyncio.sleep(0.01)
        except Exception:
            pass

    async def client_listener():
        try:
            while True:
                data = await websocket.receive_text()
                # Respond to ping or custom commands
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    listener_task = asyncio.create_task(redis_listener())
    client_task = asyncio.create_task(client_listener())

    done, pending = await asyncio.wait(
        [listener_task, client_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()

    await pubsub.unsubscribe(settings.EVENT_CHANNEL)
    await pubsub.aclose()
    logger.info("WebSocket client disconnected.")


@app.post("/api/auth/login")
async def auth_login(req: LoginRequest):
    """
    Authenticates squad administrator for task dispatching.
    Credentials configured via ADMIN_USERNAME & ADMIN_PASSWORD in .env.
    """
    if req.username == settings.ADMIN_USERNAME and req.password == settings.ADMIN_PASSWORD:
        token = generate_auth_token(req.username)
        logger.info(f"Admin '{req.username}' logged in successfully.")
        return {
            "success": True,
            "token": token,
            "username": settings.ADMIN_USERNAME,
            "message": "Autentikasi berhasil",
        }
    logger.warning(f"Failed login attempt for username '{req.username}'")
    raise HTTPException(status_code=401, detail="Username atau password pengelola salah.")


@app.get("/api/auth/verify")
async def auth_verify(request: Request):
    """Checks whether the currently supplied token is valid."""
    auth_header = request.headers.get("Authorization", "")
    token = (
        auth_header.replace("Bearer ", "").strip()
        if auth_header.startswith("Bearer ")
        else request.query_params.get("token")
    )
    if verify_auth_token(token):
        return {"valid": True, "username": settings.ADMIN_USERNAME}
    return {"valid": False}


@app.post("/api/dispatch")
async def dispatch_task(req: DispatchRequest, request: Request):
    """
    Enqueues a new agent task from the visualizer HUD or REST client.
    Requires authentication via Authorization Bearer token or X-Admin-Password.
    """
    if not async_redis_client:
        raise HTTPException(status_code=503, detail="Redis client not initialized")

    # Enforce authentication check
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else None
    admin_pw = request.headers.get("X-Admin-Password")

    if not verify_auth_token(token) and admin_pw != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Autentikasi diperlukan untuk mengirim task ke squad. Silakan masukkan password pengelola.",
        )

    task_id = req.thread_id or f"task_{uuid.uuid4().hex[:8]}"
    action_name = "trend-article" if req.source else "start"
    prompt_topic = req.prompt or req.query or (f"GitHub Trending ({req.lang or 'All'})" if req.source == "github" else "Google News")

    payload = {
        "task_id": task_id,
        "thread_id": task_id,
        "task_type": req.type,
        "action": action_name,
        "input_data": {
            "query": req.query or req.prompt,
            "topic": prompt_topic,
            "task_type": req.type,
            "action": action_name,
            "source": req.source,
            "lang": req.lang,
            "category": req.category,
            "urls": req.urls,
            "target_urls": req.urls,
            "video_id": req.video_id,
            "dry_run": req.dry_run,
        },
    }

    await async_redis_client.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))
    logger.info(f"Task dispatched via HTTP API: {task_id} ({req.type})")

    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"Task '{task_id}' queued in '{settings.TASK_QUEUE_NAME}'",
    }


# =========================================================================
# 7. CONTENT SCHEDULES & BAY-ZERO PLANNER ENDPOINTS
# =========================================================================

@app.get("/api/schedules")
async def get_schedules(limit: int = 20, status: str | None = None):
    """Mengambil daftar jadwal konten dari PostgreSQL content_schedules."""
    try:
        from scripts.planner import list_editorial_schedules
        schedules = list_editorial_schedules(limit=limit, status=status)
        return {"success": True, "count": len(schedules), "schedules": schedules}
    except Exception as exc:
        logger.error(f"Error fetching schedules: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal mengambil jadwal: {str(exc)}")


@app.post("/api/schedules/generate")
async def generate_schedules(request: Request):
    """Memicu Bay-Zero Planner untuk menyusun kalender editorial 7 hari ke depan."""
    # Autentikasi pengelola
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else None
    admin_pw = request.headers.get("X-Admin-Password")

    if not verify_auth_token(token) and admin_pw != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Autentikasi pengelola diperlukan.")

    try:
        from scripts.planner import generate_weekly_editorial_plan, list_editorial_schedules
        planned = generate_weekly_editorial_plan()
        schedules = list_editorial_schedules(limit=20)
        return {
            "success": True,
            "message": f"Berhasil membuat {len(planned)} jadwal konten 7 hari ke depan.",
            "schedules": schedules,
        }
    except Exception as exc:
        logger.error(f"Error generating weekly plan: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal generate jadwal: {str(exc)}")


@app.post("/api/schedules/{schedule_id}/trigger")
async def trigger_schedule_now(schedule_id: str, request: Request):
    """Memicu eksekusi jadwal tertentu sekarang juga tanpa menunggu scheduled_at."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else None
    admin_pw = request.headers.get("X-Admin-Password")

    if not verify_auth_token(token) and admin_pw != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Autentikasi pengelola diperlukan.")

    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, agent_name, task_type, title, payload
                    FROM content_schedules
                    WHERE id = %s;
                    """,
                    (schedule_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan.")

                s_id, agent_name, task_type, title, payload_raw = row
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

        if async_redis_client:
            await async_redis_client.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))

        logger.info(f"Manual trigger for schedule '{schedule_id}' ({title})")
        return {"success": True, "message": f"Jadwal '{schedule_id}' berhasil didorong ke antrean."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error triggering schedule {schedule_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal memicu jadwal: {str(exc)}")


# Static web UI serving if web/dist exists
web_dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "dist")
if os.path.exists(web_dist_dir):
    app.mount("/", StaticFiles(directory=web_dist_dir, html=True), name="static_web")


def run():
    """CLI runner function for stream server."""
    logger.info(
        f"🚀 Starting Punggawa Streaming Server on http://{settings.STREAM_SERVER_HOST}:{settings.STREAM_SERVER_PORT}"
    )
    uvicorn.run(
        "server.stream_server:app",
        host=settings.STREAM_SERVER_HOST,
        port=settings.STREAM_SERVER_PORT,
        reload=False,
    )


if __name__ == "__main__":
    run()
