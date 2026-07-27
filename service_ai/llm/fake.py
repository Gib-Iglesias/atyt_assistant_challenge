"""
Proveedor falso. Es el valor por defecto y lo que permite arrancar y probar sin
red ni credenciales.

No inventa contenido: compone la respuesta a partir del contexto recuperado que
recibe en el mensaje, de modo que las citas apuntan a fragmentos reales. Emite
palabra por palabra con un retardo simulado, igual que haria el proveedor real,
para que el frontend ejercite el streaming de verdad.
"""
from __future__ import annotations

import asyncio
import re
from typing import AsyncIterator

from .base import ChatMessage, LLMProvider


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, token_delay_ms: int = 25) -> None:
        self._delay = max(0, token_delay_ms) / 1000.0

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        respuesta = self._componer(messages)
        for token in self._tokenizar(respuesta):
            if self._delay:
                await asyncio.sleep(self._delay)
            yield token

    # -- interno -------------------------------------------------------------
    @staticmethod
    def _tokenizar(texto: str) -> list[str]:
        # Conserva los espacios para que la concatenacion en el cliente sea fiel.
        return re.findall(r"\S+\s*", texto)

    def _componer(self, messages: list[ChatMessage]) -> str:
        pregunta = next((m.content for m in reversed(messages) if m.role == "user"), "")
        contexto = "\n".join(m.content for m in messages if m.role == "system")

        fragmentos = self._extraer_fragmentos(contexto)
        if not fragmentos:
            return (
                "No encontre informacion suficiente en la documentacion disponible "
                "para responder con seguridad a esta consulta. Recomiendo escalar el "
                "caso a un agente humano para su revision."
            )

        cuerpo = fragmentos[0].strip()
        if len(cuerpo) > 480:
            cuerpo = cuerpo[:480].rsplit(" ", 1)[0] + "..."
        pregunta_corta = pregunta.strip().rstrip("?").strip()
        return (
            f"Segun la documentacion interna, sobre \"{pregunta_corta}\": {cuerpo} "
            f"Puedes consultar las fuentes citadas para el detalle completo."
        )

    @staticmethod
    def _extraer_fragmentos(contexto: str) -> list[str]:
        # El orquestador marca cada fragmento con [[frag]]...[[/frag]].
        return re.findall(r"\[\[frag\]\](.*?)\[\[/frag\]\]", contexto, flags=re.DOTALL)
