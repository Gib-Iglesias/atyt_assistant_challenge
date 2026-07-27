"""
Orquestador del chat. Une recuperacion, herramientas, limite de concurrencia y
generacion en un unico stream SSE.

Secuencia: recuperar -> (si no hay material) escalar y cerrar -> resolver datos
del sistema -> construir prompt con contexto no confiable -> pedir slot al
limitador -> emitir tokens -> emitir citas -> done.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..config import Settings, get_settings
from ..deps import TenantContext, get_tenant_context
from ..llm.base import LLMProvider
from ..llm.limiter import CapacityError, ConcurrencyLimiter
from ..rag import prompt as prompt_mod
from ..rag import retriever
from ..tools import orders, registry, tickets
from .schemas import ChatRequest
from .sse import evento

router = APIRouter()


def get_provider(request: Request) -> LLMProvider:
    return request.app.state.provider


def get_limiter(request: Request) -> ConcurrencyLimiter:
    return request.app.state.limiter


@router.post("/chat/stream", summary="Chat con respuesta en streaming (SSE)")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_provider),
    limiter: ConcurrencyLimiter = Depends(get_limiter),
):
    pregunta = payload.message.strip()

    async def stream():
        # 1. Recuperacion
        recuperados = retriever.recuperar(ctx, pregunta, settings)

        # 2. Escalado por falta de material
        if not retriever.hay_material_suficiente(recuperados, settings):
            referencia = orders.detectar_referencia(pregunta)
            ticket_id = tickets.escalar(ctx, pregunta, referencia)
            yield evento("token", {"text":
                "No encontre informacion suficiente en la documentacion para "
                "responder con seguridad. He escalado el caso a un agente humano."})
            yield evento("escalated", {"ticket_id": ticket_id})
            yield evento("done", {"citations": 0, "escalated": True})
            return

        # 3. Datos del sistema (pedidos / historial), como bloques de contexto
        bloques_datos = registry.resolver_datos(ctx, pregunta)

        # 4. Prompt con el contexto marcado como no instruccional
        mensajes, citas = prompt_mod.construir_mensajes(
            pregunta, recuperados, settings.llm_max_context_tokens * 4
        )
        for bloque in bloques_datos:
            from ..llm.base import ChatMessage
            mensajes.insert(-1, ChatMessage(role="system",
                            content=f"[[frag]] Datos del sistema:\n{bloque}\n[[/frag]]"))

        # 5. Generacion bajo el limite global de 20
        try:
            async with limiter.slot():
                async for token in provider.stream_chat(mensajes):
                    yield evento("token", {"text": token})
        except CapacityError as exc:
            yield evento("error", {"detail": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001
            yield evento("error", {"detail": f"Error del proveedor de IA: {exc}"})
            return

        # 6. Citas al final: ya validadas contra lo recuperado
        yield evento("citations", {"citations": [c.as_dict() for c in citas]})
        yield evento("done", {"citations": len(citas), "escalated": False})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
