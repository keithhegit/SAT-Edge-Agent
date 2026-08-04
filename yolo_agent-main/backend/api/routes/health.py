from __future__ import annotations

from fastapi import APIRouter

from backend.api.schemas import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="yolo-agent-backend")
