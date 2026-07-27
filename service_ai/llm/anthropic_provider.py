"""Proveedor Anthropic (Messages API). Streaming de eventos."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import ChatMessage, LLMConfigError, LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, base_url: str = "", timeout: int = 60) -> None:
        if not api_key:
            raise LLMConfigError("LLM_PROVIDER=anthropic requiere LLM_API_KEY.")
        self._api_key = api_key
        self._model = model or "claude-sonnet-4-5"
        self._base = (base_url or "https://api.anthropic.com/v1").rstrip("/")
        self._timeout = timeout

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        # Anthropic separa el system del resto de mensajes.
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        conversacion = [
            {"role": m.role, "content": m.content} for m in messages if m.role != "system"
        ]
        payload = {
            "model": self._model,
            "max_tokens": 1024,
            "system": system,
            "messages": conversacion,
            "stream": True,
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST", f"{self._base}/messages", json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                async for linea in resp.aiter_lines():
                    if not linea.startswith("data: "):
                        continue
                    try:
                        evento = json.loads(linea.removeprefix("data: ").strip())
                    except json.JSONDecodeError:
                        continue
                    if evento.get("type") == "content_block_delta":
                        texto = evento.get("delta", {}).get("text")
                        if texto:
                            yield texto
