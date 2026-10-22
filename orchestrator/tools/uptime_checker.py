"""Automated Microservice Uptime Monitor (Zero LLM Cost)."""
import time
import requests
from typing import Any

MONITORED_SERVICES = [
    {
        "id": "keselip",
        "name": "Keselip-API",
        "url": "https://keselipapi.bogorstore.com/",
        "expected_status": 200,
    },
    {
        "id": "kataku",
        "name": "Kataku-API",
        "url": "https://katakuapi.bogorstore.com/api/health",
        "expected_status": 200,
    },
    {
        "id": "dongeng",
        "name": "Dongeng-API",
        "url": "https://bogorstore.com/agoose/api/posts",
        "expected_status": 200,
    },
]

REDIS_SERVICES_HEALTH_KEY = "system:services_health"
REDIS_SERVICES_HEALTH_TTL = 86400  # 24 hours retention


def check_single_service(service: dict[str, Any]) -> dict[str, Any]:
    """Lakukan HTTP GET check ke single service dengan timeout 7s (Zero LLM Cost)."""
    start_time = time.time()
    try:
        resp = requests.get(
            service["url"],
            timeout=7,
            headers={"User-Agent": "Punggawa-Uptime-Bot/1.0"},
        )
        latency_ms = int((time.time() - start_time) * 1000)
        is_healthy = resp.status_code == service["expected_status"]
        return {
            "id": service["id"],
            "name": service["name"],
            "url": service["url"],
            "status": "healthy" if is_healthy else "unhealthy",
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "error": None if is_healthy else f"HTTP Status {resp.status_code}",
            "last_checked": int(time.time()),
        }
    except requests.exceptions.Timeout:
        return {
            "id": service["id"],
            "name": service["name"],
            "url": service["url"],
            "status": "unhealthy",
            "status_code": None,
            "latency_ms": int((time.time() - start_time) * 1000),
            "error": "Connection Timeout (>7s)",
            "last_checked": int(time.time()),
        }
    except requests.exceptions.ConnectionError as conn_err:
        return {
            "id": service["id"],
            "name": service["name"],
            "url": service["url"],
            "status": "unhealthy",
            "status_code": None,
            "latency_ms": int((time.time() - start_time) * 1000),
            "error": f"Connection Error: {conn_err}",
            "last_checked": int(time.time()),
        }
    except Exception as exc:
        return {
            "id": service["id"],
            "name": service["name"],
            "url": service["url"],
            "status": "unhealthy",
            "status_code": None,
            "latency_ms": int((time.time() - start_time) * 1000),
            "error": str(exc),
            "last_checked": int(time.time()),
        }


def run_all_health_checks() -> dict[str, Any]:
    """Pindai seluruh daftar MONITORED_SERVICES dan agregasikan status ketersediaannya."""
    results = [check_single_service(s) for s in MONITORED_SERVICES]
    all_healthy = all(r["status"] == "healthy" for r in results)
    return {
        "overall_status": "healthy" if all_healthy else "degraded",
        "services": results,
        "timestamp": int(time.time()),
    }
