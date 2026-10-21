"""State definitions for the LangGraph agent orchestrator."""
from operator import add
from typing import Annotated, Any, Literal, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Definisi State utama yang disimpan dan dimutasi via PostgresSaver.
    Mendukung ReAct conversational tools, pipeline content publishing otomatis,
    dan audit trail thread-safe.
    """
    task_id: str
    thread_id: str

    # Status Lifecycle Task
    status: Literal["pending", "processing", "waiting_approval", "completed", "failed"]

    # Jenis Graph / Pipeline
    task_type: str | None

    # History pesan multi-turn dan pemanggilan tool menggunakan reducer add_messages
    messages: Annotated[list[Any], add_messages]

    # Tool call yang tertunda jika memerlukan persetujuan manual (Sensitive Action)
    pending_tool_call: dict[str, Any] | None

    # Payload input awal
    input_data: dict[str, Any]

    # Pipeline Content Publishing Fields (writer-kodeabc)
    target_urls: str | list[str] | None
    category: str | None
    scraped_content: str | None
    url_references: str | None
    dual_content: dict[str, Any] | None       # {"id": {...}, "en": {...}, "translation_key": "..."}
    dual_images: dict[str, str] | None        # {"id": "data:image/jpeg;base64,...", "en": "..."}
    published_ids: dict[str, Any] | None      # {"id": "...", "en": "..."}

    # Trend Ingestion Data (Google News RSS & GitHub Trending Weekly)
    trend_source_data: list[dict[str, Any]] | None
    trend_selected_item: dict[str, Any] | None

    # Pipeline Dongeng YouTube -> Bogorstore CMS Fields
    video_id: str | None
    video_metadata: dict[str, Any] | None
    curation_result: dict[str, Any] | None    # {"skip": bool, "reason": "...", "title": "...", "category_id": "..."}
    thumbnail_path: str | None
    cms_post_result: dict[str, Any] | None

    # Audit trail & logs terakumulasi tanpa menimpa data sebelumnya
    execution_logs: Annotated[list[str], add]

    # Output atau ringkasan hasil kalkulasi akhir
    result: dict[str, Any] | None

    # Human-in-the-loop: flag verifikasi aksi kritis
    requires_approval: bool
    is_approved: bool | None

    # Metadata penelusuran worker
    last_processed_by: str | None
    error: str | None
