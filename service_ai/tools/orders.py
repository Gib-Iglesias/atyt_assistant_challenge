"""
Herramientas de datos: consulta de pedidos e historial de cliente.

Reciben el TenantContext y delegan en los repositorios, que aplican el filtro por
tenant. Ninguna acepta tenant_id: no hay forma de pedir datos de otro cliente.
El correo se enmascara cuando el usuario no es agente de soporte.
"""
from __future__ import annotations

import re

from ..deps import TenantContext
from ..db import repositories

REF_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d{4,})\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def _enmascarar(email: str, ctx: TenantContext) -> str:
    if ctx.is_support_agent or ctx.is_staff:
        return email
    usuario, _, dominio = email.partition("@")
    visible = usuario[:2] if len(usuario) > 2 else usuario[:1]
    return f"{visible}***@{dominio}"


def detectar_referencia(texto: str) -> str | None:
    m = REF_RE.search(texto.upper())
    return m.group(1) if m else None


def detectar_email(texto: str) -> str | None:
    m = EMAIL_RE.search(texto)
    return m.group(0) if m else None


def consultar_pedido(ctx: TenantContext, referencia: str) -> str | None:
    pedido = repositories.buscar_pedido(ctx, referencia)
    if not pedido:
        return None
    correo = _enmascarar(pedido["customer_email"], ctx)
    return (
        f"Pedido {pedido['reference']}: estado {pedido['status']}, "
        f"importe {pedido['total_amount']} {pedido['currency']}, "
        f"cliente {correo}, realizado el {pedido['placed_at']}."
    )


def consultar_historial(ctx: TenantContext, email: str) -> str | None:
    pedidos = repositories.historial_cliente(ctx, email)
    if not pedidos:
        return None
    lineas = [
        f"- {p['reference']}: {p['status']}, {p['total_amount']} {p['currency']} ({p['placed_at']})"
        for p in pedidos
    ]
    return f"Historial de {_enmascarar(email, ctx)} ({len(pedidos)} pedidos):\n" + "\n".join(lineas)
