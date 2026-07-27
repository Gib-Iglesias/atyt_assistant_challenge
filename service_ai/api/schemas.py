"""Esquemas de entrada y salida. Pydantic da la validacion y alimenta Swagger."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000, description="Pregunta del agente.")
    conversation_id: int | None = Field(default=None, description="Hilo existente, si lo hay.")


class Citation(BaseModel):
    document_id: int
    title: str
    page_start: int
    page_end: int
    score: float


class HealthResponse(BaseModel):
    status: str
    service: str
    llm_provider: str
    waiting: int
