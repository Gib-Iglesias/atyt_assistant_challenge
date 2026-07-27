"""Proveedor Google Gemini (streamGenerateContent)."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import ChatMessage, LLMConfigError, LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str = "", timeout: int = 60) -> None:
        if not api_key:
            raise LLMConfigError("LLM_PROVIDER=gemini requiere LLM_API_KEY.")
        self._api_key = api_key
        self._model = model or "gemini-1.5-flash"
        self._base = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self._timeout = timeout

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        contents = []
        for m in messages:
            if m.role == "system":
                continue
            contents.append({"role": "user" if m.role == "user" else "model",
                             "parts": [{"text": m.content}]})
        payload: dict = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"{self._base}/models/{self._model}:streamGenerateContent?alt=sse&key={self._api_key}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for linea in resp.aiter_lines():
                    if not linea.startswith("data: "):
                        continue
                    try:
                        data = json.loads(linea.removeprefix("data: ").strip())
                        texto = data["candidates"][0]["content"]["parts"][0]["text"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    if texto:
                        yield texto
