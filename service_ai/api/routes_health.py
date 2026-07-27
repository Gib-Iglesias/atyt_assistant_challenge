"""Sondas de salud."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..config import Settings, get_settings
from .schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Estado del servicio")
async def health(request: Request, settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="atyt-assistant-api",
        llm_provider=settings.llm_provider,
        waiting=request.app.state.limiter.en_espera,
    )
