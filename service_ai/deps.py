"""
Contexto de peticion: identidad y tenant, derivados del JWT.

tenant_id sale del token firmado por Django y de ningun otro sitio. Es la pieza
sobre la que descansa el aislamiento: ni el cuerpo de la peticion, ni la query,
ni nada que el modelo pueda influir puede cambiarlo. Ver docs/ARQUITECTURA.md,
seccion 6.
"""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings


@dataclass(frozen=True)
class TenantContext:
    user_id: int
    username: str
    tenant_id: int | None
    tenant_slug: str | None
    is_support_agent: bool
    is_staff: bool

    @property
    def can_access_business_data(self) -> bool:
        """Sin tenant no hay datos de negocio que consultar, salvo staff global."""
        return self.tenant_id is not None or self.is_staff


def get_tenant_context(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> TenantContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta la cabecera Authorization: Bearer <token>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalido: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TenantContext(
        user_id=int(payload["sub"]),
        username=payload.get("username", ""),
        tenant_id=payload.get("tenant_id"),
        tenant_slug=payload.get("tenant_slug"),
        is_support_agent=bool(payload.get("is_support_agent", False)),
        is_staff=bool(payload.get("is_staff", False)),
    )
