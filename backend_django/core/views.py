"""Endpoints minimos de identidad. El chat vive en el servicio FastAPI."""
from __future__ import annotations

import json

from django.contrib.auth import authenticate
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth_jwt import TokenError, decode_token, issue_token


def _json_body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


@csrf_exempt
@require_http_methods(["POST"])
def token(request: HttpRequest) -> JsonResponse:
    """POST /api/auth/token  {username, password} -> {access_token, ...}"""
    body = _json_body(request)
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return JsonResponse({"detail": "Faltan credenciales."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        # Mismo mensaje para usuario inexistente y contrasena incorrecta.
        return JsonResponse({"detail": "Credenciales invalidas."}, status=401)

    access_token, expires_in = issue_token(user)
    return JsonResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "user": {
                "id": user.pk,
                "username": user.username,
                "tenant_slug": user.tenant.slug if user.tenant_id else None,
                "is_support_agent": user.is_support_agent,
                "is_staff": user.is_staff,
            },
        }
    )


@require_http_methods(["GET"])
def me(request: HttpRequest) -> JsonResponse:
    """GET /api/auth/me con cabecera Authorization: Bearer <token>."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return JsonResponse({"detail": "Falta el token."}, status=401)
    try:
        claims = decode_token(header.removeprefix("Bearer ").strip())
    except TokenError as exc:
        return JsonResponse({"detail": f"Token invalido: {exc}"}, status=401)

    return JsonResponse(
        {
            "user_id": claims.user_id,
            "username": claims.username,
            "tenant_slug": claims.tenant_slug,
            "is_support_agent": claims.is_support_agent,
            "is_staff": claims.is_staff,
        }
    )


@require_http_methods(["GET"])
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok", "service": "django"})
