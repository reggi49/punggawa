"""Notification and dispatching tools with sensitivity control."""
import logging
from typing import Any
import httpx
from orchestrator.tools.base import register_tool

logger = logging.getLogger("NotificationTools")


@register_tool(
    name="send_webhook_notification",
    description="Mengirim notifikasi atau payload data ke webhook URL eksternal (Aksi Kritis/Sensitif yang memerlukan persetujuan).",
    sensitive=True,  # Memerlukan Human-in-the-Loop Approval sebelum dieksekusi
)
def send_webhook_notification(webhook_url: str, message: str, priority: str = "normal") -> dict[str, Any]:
    """
    Mengirim pesan POST ke webhook URL.
    Karena ditandai sensitive=True, graf akan menahan eksekusi di checkpoint
    sampai user memberikan izin via scripts/dispatch.py.
    """
    payload = {
        "source": "Punggawa Autonomous Agent",
        "priority": priority,
        "message": message,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(webhook_url, json=payload)
            return {
                "sent": True,
                "webhook_url": webhook_url,
                "status_code": resp.status_code,
                "response": resp.text[:200],
            }
    except Exception as exc:
        logger.error(f"Gagal mengirim webhook ke {webhook_url}: {exc}")
        return {
            "sent": False,
            "error": str(exc),
            "webhook_url": webhook_url,
        }

