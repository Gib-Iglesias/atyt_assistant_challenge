"""
Resolucion de herramientas de datos a partir de la pregunta.

Se detecta una referencia de pedido o un correo en el texto y se resuelve con la
herramienta correspondiente. El resultado se anade al contexto como un bloque de
datos mas, con la misma marca de no-instruccion.
"""
from __future__ import annotations

from ..deps import TenantContext
from . import orders


def resolver_datos(ctx: TenantContext, pregunta: str) -> list[str]:
    """Devuelve bloques de datos del sistema relevantes a la pregunta."""
    if not ctx.can_access_business_data:
        return []
    bloques: list[str] = []

    referencia = orders.detectar_referencia(pregunta)
    if referencia:
        info = orders.consultar_pedido(ctx, referencia)
        bloques.append(info if info else f"No existe el pedido {referencia} en este cliente.")

    email = orders.detectar_email(pregunta)
    if email:
        info = orders.consultar_historial(ctx, email)
        if info:
            bloques.append(info)

    return bloques
