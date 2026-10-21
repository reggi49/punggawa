"""Helper script to enqueue test tasks into Redis Queue."""
import json
import uuid
import sys
from config.settings import settings
from orchestrator.connections import redis_client


def enqueue_task(
    query: str,
    requires_approval: bool = False,
    task_id: str | None = None,
    action: str = "start",
    approved: bool | None = None,
):
    """
    Kirim payload task ke antrean Redis.
    """
    task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
    payload = {
        "task_id": task_id,
        "thread_id": task_id,
        "action": action,
        "approved": approved,
        "input_data": {
            "query": query,
            "items": [101, 102, 103],
            "requires_approval": requires_approval,
        },
    }

    redis_client.rpush(settings.TASK_QUEUE_NAME, json.dumps(payload))
    print(f"✅ Berhasil enqueue task: ID={task_id} (ApprovalRequired={requires_approval}, Action={action})")
    return task_id


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--approval":
        print("Mengirim task dengan kebutuhan persetujuan (Human-in-the-loop)...")
        enqueue_task("Proses transaksi finansial / migrasi database", requires_approval=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "--race":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(f"🚀 Mengirim {count} task dengan thread_id SAMA untuk menguji Anti-Race Condition...")
        shared_thread = f"race_test_thread_{uuid.uuid4().hex[:6]}"
        for i in range(count):
            enqueue_task(
                query=f"Kalkulasi simultan batch #{i + 1}",
                task_id=shared_thread,
            )
    elif len(sys.argv) > 1 and sys.argv[1] == "--batch":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(f"Mengirim {count} task berbeda untuk load balancing...")
        for i in range(count):
            enqueue_task(f"Task batch #{i + 1}")
    else:
        print("Mengirim single task standar...")
        enqueue_task("Analisis metrik traffic server")

