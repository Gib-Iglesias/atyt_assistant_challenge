"""
Interfaz del proveedor de LLM.

Todo acceso al modelo pasa por aqui. Cambiar de proveedor es cambiar la
implementacion detras de esta interfaz; el resto del servicio no se entera. El
enunciado exige tanto la interfaz como una implementacion falsa que emita token
a token sin red ni API key.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Literal


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


class LLMProvider:
    """Contrato minimo. Una implementacion emite la respuesta token a token."""

    name: str = "base"

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        raise NotImplementedError
        yield ""  # pragma: no cover - marca la funcion como generador async


class LLMConfigError(RuntimeError):
    """Configuracion incompleta: p. ej. proveedor real sin API key."""
