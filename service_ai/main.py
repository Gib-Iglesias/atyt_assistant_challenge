"""
Punto de entrada del servicio de IA.

Swagger queda en /docs (generado automaticamente por FastAPI). El proveedor de
LLM y el limitador de concurrencia se construyen una sola vez al arrancar y
viven en app.state, para que el semaforo sea compartido por todas las peticiones.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import routes_chat, routes_health
from .config import get_settings
from .llm.factory import build_provider
from .llm.limiter import ConcurrencyLimiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Falla al arrancar si el proveedor real no tiene API key, en vez de
    # degradarse en silencio a mitad de una peticion.
    app.state.provider = build_provider(settings)
    app.state.limiter = ConcurrencyLimiter(
        max_concurrency=settings.llm_max_concurrency,
        queue_max_size=settings.llm_queue_max_size,
        queue_timeout_s=settings.llm_queue_timeout_seconds,
    )
    yield


app = FastAPI(
    title="atyt_assistant_challenge — servicio de IA",
    description="Asistente de soporte con RAG, citas, streaming y escalado.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(routes_health.router, tags=["salud"])
app.include_router(routes_chat.router, prefix="/api", tags=["chat"])
