"""Database connection pool and Redis client configuration."""
import redis
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from config.settings import settings

# Inisialisasi Redis Client (decode_responses=True agar mengembalikan string)
redis_client: redis.Redis = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=15.0,
    socket_connect_timeout=10.0,
)

# Inisialisasi Postgres Connection Pool
# Menggunakan pool moderat (min 1, max 8) agar aman untuk limit memory t3.nano dan kuota Supabase
postgres_pool = ConnectionPool(
    conninfo=settings.DATABASE_URL,
    min_size=1,
    max_size=8,
    timeout=30.0,
    max_idle=60.0,
    open=True,
    kwargs={"autocommit": True, "prepare_threshold": None},
)


def get_checkpointer() -> PostgresSaver:
    """
    Mengembalikan instance PostgresSaver siap pakai.
    Memanggil checkpointer.setup() untuk memastikan tabel metadata
    langgraph checkpoints terbuat otomatis di PostgreSQL.
    """
    checkpointer = PostgresSaver(postgres_pool)
    checkpointer.setup()
    return checkpointer

