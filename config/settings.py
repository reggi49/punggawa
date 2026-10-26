from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Muat environment variables langsung ke os.environ
load_dotenv()


class Settings(BaseSettings):
    # Cloud Postgres (Supabase / Managed PostgreSQL)
    DATABASE_URL: str = Field(
        "postgresql://postgres:postgres@localhost:5432/postgres",
        description="PostgreSQL connection URI",
    )

    # Redis for Distributed Lock & Queue
    REDIS_URL: str = Field(
        "redis://localhost:6379/0",
        description="Redis connection URI",
    )

    # Worker Identifier (e.g. 'mac-local' or 'vps-cloud-worker-1')
    WORKER_ID: str = Field(
        "local-worker",
        description="Identifier instance worker",
    )

    # Task Queue Settings
    TASK_QUEUE_NAME: str = Field(
        "agent:task:queue",
        description="Redis list key for task queue",
    )
    EVENT_CHANNEL: str = Field(
        "agent:events",
        description="Redis Pub/Sub channel for real-time agent events",
    )
    STREAM_SERVER_HOST: str = Field(
        "0.0.0.0",
        description="Host for real-time visualizer streaming server",
    )
    STREAM_SERVER_PORT: int = Field(
        8000,
        description="Port for real-time visualizer streaming server",
    )
    LOCK_TTL_SECONDS: int = Field(
        600,
        description="Time-to-live for distributed lock in seconds (10 menit untuk pipeline panjang)",
    )

    # Dashboard Access & Task Dispatch Authentication
    ADMIN_USERNAME: str = Field(
        "",
        description="Username untuk autentikasi kirim task di visualizer",
    )
    ADMIN_PASSWORD: str = Field(
        "",
        description="Password untuk autentikasi kirim task di visualizer",
    )
    AUTH_SECRET_KEY: str = Field(
        "",
        description="Secret key untuk validasi token dispatch",
    )

    # Supabase Specific (Opsional)
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None

    # 9Router Smart Gateway Settings (PRIMARY / DEFAULT)
    NINE_ROUTER_BASE_URL: str = Field(
        "http://localhost:20128/v1",
        description="OpenAI-compatible base URL 9Router gateway (Primary)",
    )
    NINE_ROUTER_API_KEY: str = Field(
        "",
        description="API key untuk 9Router (non-empty string)",
    )
    NINE_ROUTER_MODEL: str = Field(
        "gpt-4o-mini",
        description="Model identifier di 9Router",
    )

    # Direct Fallback Provider (Digunakan jika 9Router down/tidak merespon)
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    DEFAULT_LLM_MODEL: str = Field(
        "gpt-4o-mini",
        description="Model name untuk direct fallback provider",
    )
    GEMINI_API_KEY: str | None = None

    # KodePintar / Lucy Article Publisher Settings
    API_ENDPOINT: str | None = Field(None, description="KodePintar Lucy publishing endpoint")
    SECRET_KEY: str | None = Field(None, description="KodePintar Bearer secret key")
    USER_ID: str = Field("", description="KodePintar user ID")
    PEXELS_KEY: str | None = Field(None, description="Pexels API key for image search")
    BRAVE_API_KEY: str | None = Field(None, description="Brave Search API key for multi-source research")

    # YouTube & Dongeng CMS Settings
    YOUTUBE_API_KEY: str = Field(
        "",
        description="YouTube Data API v3 key",
    )
    DONGENG_CMS_POST_URL: str = Field(
        "",
        description="Endpoint POST CMS Dongeng",
    )
    DONGENG_CMS_STORIES_URL: str = Field(
        "https://bogorstore.com/agoose/api/posts/stories",
        description="Endpoint POST Stories / Shorts CMS Dongeng",
    )
    DONGENG_CMS_SEARCH_URL: str = Field(
        "",
        description="Endpoint Search CMS Dongeng",
    )
    DONGENG_TARGET_CHANNELS: list[str] = Field(
        default_factory=list,
        description="Daftar channel YouTube target dongeng",
    )
    DONGENG_FONT_PATH: str = Field(
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        description="Path ke file font bold untuk thumbnail dongeng",
    )
    DONGENG_CMS_NOTIFICATION_URL: str = Field(
        "https://bogorstore.com/agoose/posts/sendnotification",
        description="Endpoint trigger push notification CMS Dongeng ({id})",
    )
    DONGENG_CMS_COOKIE: str = Field(
        "",
        description="Opsional session cookie untuk trigger notification CMS",
    )

    # HITL (Human-in-the-Loop) & Telegram Alert Settings
    TELEGRAM_BOT_TOKEN: str = Field(
        "",
        description="Telegram bot token for HITL notifications",
    )
    TELEGRAM_CHAT_ID: str = Field(
        "",
        description="Telegram chat ID for HITL notifications",
    )
    BROWSER_DEBUGGER_BASE_URL: str = Field(
        "http://localhost:3000/debugger",
        description="Browser debugger base URL for human intervention",
    )
    # Browserless CDP Connection Settings
    BROWSERLESS_TOKEN: str = Field(
        "punggawa_super_secret_token_123",
        description="Token autentikasi Browserless",
    )
    BROWSERLESS_WS_URL: str = Field(
        "ws://127.0.0.1:3000",
        description="Base WebSocket URL container Browserless",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

