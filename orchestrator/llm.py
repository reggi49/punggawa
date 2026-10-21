"""LLM Router with automatic fallback to 9Router smart gateway and Tool-calling support."""
import json
import logging
from typing import Any
from openai import OpenAI
from config.settings import settings

logger = logging.getLogger("LLMRouter")


class LLMClient:
    """
    Klien LLM dengan kapabilitas:
    - Primary (Default): 9Router (http://localhost:20128/v1)
    - Fallback: Direct OpenAI / Provider lain jika 9Router gagal/down/tidak aktif
    - Dukungan OpenAI Tools / Function Calling schema
    """

    def __init__(self):
        self._9router_client = None
        self._fallback_client = None

        # 1. Setup 9Router sebagai Primary Client (Default)
        if settings.NINE_ROUTER_BASE_URL:
            self._9router_client = OpenAI(
                api_key=settings.NINE_ROUTER_API_KEY,
                base_url=settings.NINE_ROUTER_BASE_URL,
                timeout=120.0,  # Berikan timeout 120s untuk generasi artikel panjang (ID/EN)
                max_retries=1,
            )

        # 2. Setup Direct Provider sebagai Fallback
        if settings.OPENAI_API_KEY:
            self._fallback_client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                timeout=15.0,
            )

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Kirim prompt ke LLM beserta daftar tools (jika ada).
        Urutan prioritas:
        1. 9Router (Utama / Default)
        2. Direct Provider (Fallback jika 9Router gagal/down)
        """
        errors = []
        call_kwargs = dict(kwargs)
        if tools:
            call_kwargs["tools"] = tools
            call_kwargs["tool_choice"] = "auto"

        # 1. Coba 9Router terlebih dahulu (Primary Default)
        if self._9router_client:
            primary_model = model or settings.NINE_ROUTER_MODEL
            try:
                logger.info(
                    f"[LLM] Menjalankan 9Router (Primary) di {settings.NINE_ROUTER_BASE_URL} (model={primary_model})..."
                )
                # Nonaktifkan thinking/reasoning internal jika model mendukung agar tidak timeout
                if "thinking" not in call_kwargs and ("qwen" in primary_model or primary_model in ("free", "bansos")):
                    call_kwargs["extra_body"] = {"thinking": {"enabled": False}}

                response = self._9router_client.chat.completions.create(
                    model=primary_model,
                    messages=messages,
                    temperature=temperature,
                    **call_kwargs,
                )
                return self._parse_response(response, provider="9router", model=primary_model, fallback_used=False)
            except Exception as nine_router_err:
                # Coba sekali lagi tanpa extra_body HANYA jika bukan timeout/connection error
                is_timeout = "timeout" in str(nine_router_err).lower()
                if "extra_body" in call_kwargs and not is_timeout:
                    try:
                        del call_kwargs["extra_body"]
                        response = self._9router_client.chat.completions.create(
                            model=primary_model,
                            messages=messages,
                            temperature=temperature,
                            **call_kwargs,
                        )
                        return self._parse_response(response, provider="9router", model=primary_model, fallback_used=False)
                    except Exception:
                        pass
                err_msg = f"9Router (Primary) gagal/offline: {nine_router_err}"
                logger.warning(f"[LLM FALLBACK TRIGGERED] {err_msg}")
                errors.append(err_msg)
        else:
            logger.warning("[LLM] 9Router tidak dikonfigurasi, mencoba fallback direct provider...")

        # 2. Fallback ke Direct Provider jika 9Router gagal
        if self._fallback_client:
            fallback_model = model or settings.DEFAULT_LLM_MODEL
            try:
                logger.info(f"[LLM] Mencoba direct fallback provider (model={fallback_model})...")
                response = self._fallback_client.chat.completions.create(
                    model=fallback_model,
                    messages=messages,
                    temperature=temperature,
                    **call_kwargs,
                )
                return self._parse_response(response, provider="direct_fallback", model=fallback_model, fallback_used=True)
            except Exception as fallback_err:
                err_msg = f"Direct fallback provider gagal: {fallback_err}"
                logger.error(f"[LLM] {err_msg}")
                errors.append(err_msg)
        else:
            errors.append("Direct fallback provider tidak diset (OPENAI_API_KEY kosong).")

        raise RuntimeError(f"Semua provider LLM gagal dipanggil. Detail error: {'; '.join(errors)}")

    @staticmethod
    def _parse_response(response: Any, provider: str, model: str, fallback_used: bool) -> dict[str, Any]:
        """Ekstrak content dan pemanggilan tools dari response chat.completions."""
        message = response.choices[0].message
        content = message.content or ""
        tool_calls_list = []

        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                call_info = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                tool_calls_list.append(call_info)

        return {
            "content": content,
            "tool_calls": tool_calls_list,
            "provider": provider,
            "model": model,
            "fallback_used": fallback_used,
            "raw_message": message,
        }


# Singleton instance
llm_client = LLMClient()
