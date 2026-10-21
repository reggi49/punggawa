"""Distributed Locking implementation using Redis atomic commands and Lua script."""
import functools
import logging
import time
import uuid
from typing import Any, Callable

from orchestrator.connections import redis_client

logger = logging.getLogger("DistributedLock")

# Lua script untuk atomic release: Hanya hapus key jika value == owner_token
LUA_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class LockAcquisitionError(Exception):
    """Dilempar ketika lock gagal didapatkan oleh worker."""
    pass


class RedisDistributedLock:
    """
    Context manager untuk Redis Distributed Lock berbasis token acak dan TTL.
    """

    def __init__(
        self,
        lock_key: str,
        ttl_seconds: int = 60,
        acquire_timeout: float = 0.0,
        retry_interval: float = 0.1,
    ):
        """
        :param lock_key: Kunci unik di Redis, misal `lock:thread:<thread_id>`
        :param ttl_seconds: Masa berlaku lock sebelum expired otomatis
        :param acquire_timeout: Batas waktu tunggu (detik). Default 0 (fail-fast)
        :param retry_interval: Jeda antar percobaan jika acquire_timeout > 0
        """
        self.lock_key = lock_key
        self.ttl_seconds = ttl_seconds
        self.acquire_timeout = acquire_timeout
        self.retry_interval = retry_interval
        self.owner_token = str(uuid.uuid4())
        self._is_locked = False

    def acquire(self) -> bool:
        start_time = time.monotonic()
        while True:
            # SET NX EX adalah operasi atomik tunggal di Redis
            acquired = redis_client.set(
                self.lock_key,
                self.owner_token,
                nx=True,
                ex=self.ttl_seconds,
            )
            if acquired:
                self._is_locked = True
                logger.info(
                    f"[LOCK ACQUIRED] Key='{self.lock_key}' by Owner='{self.owner_token[:8]}...'"
                )
                return True

            # Jika fail-fast (acquire_timeout == 0), langsung keluar
            if self.acquire_timeout <= 0:
                break

            # Cek apakah batas waktu tunggu sudah habis
            if (time.monotonic() - start_time) >= self.acquire_timeout:
                break

            time.sleep(self.retry_interval)

        logger.warning(
            f"[LOCK REJECTED] Key='{self.lock_key}' sedang dikunci oleh worker lain."
        )
        return False

    def release(self) -> bool:
        if not self._is_locked:
            return False

        try:
            # Eksekusi Lua script untuk release secara aman
            result = redis_client.eval(
                LUA_RELEASE_LOCK_SCRIPT,
                1,
                self.lock_key,
                self.owner_token,
            )
            released = bool(result)
            if released:
                logger.info(
                    f"[LOCK RELEASED] Key='{self.lock_key}' oleh Owner='{self.owner_token[:8]}...'"
                )
            else:
                logger.warning(
                    f"[LOCK EXPIRED/LOST] Key='{self.lock_key}' sudah kadaluarsa atau di-release worker lain."
                )
            return released
        finally:
            self._is_locked = False

    def __enter__(self):
        if not self.acquire():
            raise LockAcquisitionError(
                f"Gagal mendapatkan distributed lock untuk resource: {self.lock_key}"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def with_distributed_lock(
    key_prefix: str = "lock:thread",
    ttl_seconds: int = 60,
    acquire_timeout: float = 0.0,
):
    """
    Decorator untuk membungkus pemanggilan LangGraph `app.invoke()` atau worker task.
    Mengekstrak `thread_id` dari argumen kwargs atau LangGraph config dict.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 1. Cari thread_id langsung di kwargs
            thread_id = kwargs.get("thread_id")

            # 2. Jika tidak ada, cek config LangGraph: config={"configurable": {"thread_id": ...}}
            if not thread_id:
                config = kwargs.get("config")
                if not config and len(args) > 1 and isinstance(args[1], dict):
                    config = args[1]

                if isinstance(config, dict):
                    thread_id = config.get("configurable", {}).get("thread_id")

            if not thread_id:
                raise ValueError("thread_id wajib disertakan untuk mengaktifkan Distributed Lock.")

            redis_lock_key = f"{key_prefix}:{thread_id}"

            with RedisDistributedLock(
                lock_key=redis_lock_key,
                ttl_seconds=ttl_seconds,
                acquire_timeout=acquire_timeout,
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator

