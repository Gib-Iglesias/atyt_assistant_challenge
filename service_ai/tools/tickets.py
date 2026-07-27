"""Escalado de tickets."""
from __future__ import annotations

from ..deps import TenantContext
from ..db import repositories


def escalar(ctx: TenantContext, pregunta: str, order_reference: str | None = None) -> int:
    asunto = f"Escalado automatico: {pregunta.strip()[:120]}"
    cuerpo = (
        "El asistente no encontro informacion suficiente para responder con seguridad.\n\n"
        f"Consulta original del agente {ctx.username}:\n{pregunta.strip()}"
    )
    return repositories.crear_ticket_escalado(ctx, asunto, cuerpo, order_reference)
