"""
Emision y verificacion de JWT.

Django es la fuente de verdad de identidad; FastAPI solo valida la firma con el
mismo secreto. tenant_id viaja dentro del token firmado y esa es la unica via
por la que el servicio de IA lo acepta: no se lee del cuerpo, ni de la query,
ni de nada que el modelo pueda influir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from django.conf import settings


class TokenError(Exception):
    """Token ausente, caducado, mal firmado o con claims incoherentes."""


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    username: str
    tenant_id: int | None
    tenant_slug: str | None
    is_support_agent: bool
    is_staff: bool


def issue_token(user, ttl_minutes: int | None = None) -> tuple[str, int]:
    """Devuelve (token, segundos_de_vida) para el usuario dado."""
    ttl = timedelta(minutes=ttl_minutes or settings.JWT_TTL_MINUTES)
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user.pk),
        "username": user.username,
        "tenant_id": user.tenant_id,
        "tenant_slug": user.tenant.slug if user.tenant_id else None,
        "is_support_agent": bool(user.is_support_agent),
        "is_staff": bool(user.is_staff),
        "iss": settings.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, int(ttl.total_seconds())


def decode_token(token: str) -> TokenClaims:
    """Valida firma y caducidad. Lanza TokenError ante cualquier problema."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    return TokenClaims(
        user_id=int(payload["sub"]),
        username=payload.get("username", ""),
        tenant_id=payload.get("tenant_id"),
        tenant_slug=payload.get("tenant_slug"),
        is_support_agent=bool(payload.get("is_support_agent", False)),
        is_staff=bool(payload.get("is_staff", False)),
    )
