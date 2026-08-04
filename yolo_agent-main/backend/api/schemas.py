from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class StartEventData(BaseModel):
    request_id: str
    thread_id: str
    timestamp: str


class TokenEventData(BaseModel):
    text: str


class ToolResultItemData(BaseModel):
    image_path: str | None = None
    image_name: str | None = None
    summary: str
    result_text: str | None = None
    image_url: str | None = None
    detections_count: int | None = None
    perf_total_ms: float | None = None
    success: bool | None = None
    geo_center: list[float] | None = None
    geo_status: str | None = None
    detection_geos: list[dict] | None = None


class ToolEventData(BaseModel):
    name: str
    phase: str
    summary: str
    result_text: str | None = None
    image_url: str | None = None
    detections_count: int | None = None
    perf_total_ms: float | None = None
    images_count: int | None = None
    success_count: int | None = None
    failure_count: int | None = None
    detected_images_count: int | None = None
    total_detections_count: int | None = None
    items: list[ToolResultItemData] | None = None
    geo_center: list[float] | None = None
    geo_status: str | None = None
    detection_geos: list[dict] | None = None


class DoneEventData(BaseModel):
    request_id: str
    duration_ms: int


class ErrorEventData(BaseModel):
    code: str
    message: str
