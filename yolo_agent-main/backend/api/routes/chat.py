from __future__ import annotations

from collections.abc import Iterator
import logging
from pathlib import Path
import sqlite3
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.agent.factory import create_detection_agent
from backend.application.chat_stream_service import stream_chat_events
from backend.infrastructure.storage.upload_store import UploadStore

logger = logging.getLogger(__name__)

router = APIRouter()
UPLOAD_STORE = UploadStore(base_dir=Path("runtime/uploads"))
SUPPORTED_IMAGE_TYPES = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".bmp": {"image/bmp"},
}
MAX_IMAGE_SIZE_MB = 10
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


def _validate_image_upload(upload: UploadFile) -> None:
    filename = (upload.filename or "").strip()
    extension = Path(filename).suffix.lower()
    content_type = (upload.content_type or "").strip().lower()

    if not filename or extension not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="不支持的图片类型，仅支持 jpeg/png/webp/bmp")

    if content_type not in SUPPORTED_IMAGE_TYPES[extension]:
        raise HTTPException(status_code=400, detail="图片 MIME 类型与扩展名不匹配")

    current_position = upload.file.tell()
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(current_position)
    if size <= 0:
        raise HTTPException(status_code=400, detail="上传文件不能为空")
    if size > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"上传文件大小不能超过 {MAX_IMAGE_SIZE_MB}MB")


@router.post("/chat/stream")
async def chat_stream(
    message: str | None = Form(default=None),
    thread_id: str | None = Form(default=None),
    images: list[UploadFile] | None = File(default=None),
) -> StreamingResponse:
    missing_fields: list[str] = []
    if not message:
        missing_fields.append("message")
    if not thread_id:
        missing_fields.append("thread_id")
    if missing_fields:
        raise HTTPException(status_code=400, detail=f"缺少必填字段: {','.join(missing_fields)}")

    uploads = [upload for upload in (images or []) if upload is not None and (upload.filename or "").strip()]
    for upload in uploads:
        _validate_image_upload(upload)

    request_id = uuid4().hex
    request_start = perf_counter()
    endpoint = "/api/v1/chat/stream"
    filenames = ",".join(upload.filename or "" for upload in uploads)
    content_types = ",".join(upload.content_type or "" for upload in uploads)
    logger.info(
        "chat request started request_id=%s thread_id=%s endpoint=%s filenames=%s content_types=%s images_count=%s",
        request_id,
        thread_id,
        endpoint,
        filenames,
        content_types,
        len(uploads),
    )

    try:
        agent = create_detection_agent(streaming=True)
    except (sqlite3.Error, OSError) as exc:
        logger.error(
            "chat request setup failed request_id=%s thread_id=%s endpoint=%s error=%s",
            request_id,
            thread_id,
            endpoint,
            str(exc),
        )
        raise HTTPException(status_code=500, detail="会话存储不可用，请稍后重试") from exc

    saved_paths: list[Path] = []
    upload_ms = 0
    if uploads:
        upload_start = perf_counter()
        try:
            for upload in uploads:
                saved_paths.append(UPLOAD_STORE.save(upload, request_id=request_id))
        except OSError as exc:
            logger.error(
                "chat request upload failed request_id=%s thread_id=%s endpoint=%s error=%s",
                request_id,
                thread_id,
                endpoint,
                str(exc),
            )
            raise HTTPException(status_code=500, detail="上传文件保存失败，请检查服务端存储配置") from exc
        upload_ms = int((perf_counter() - upload_start) * 1000)
    metrics: dict[str, object] = {"status": "success", "tool_ms": 0, "error": ""}

    def _event_stream() -> Iterator[str]:
        try:
            yield from stream_chat_events(
                agent=agent,
                message=message,
                thread_id=thread_id,
                image_paths=saved_paths,
                request_id=request_id,
                metrics=metrics,
            )
        finally:
            for saved_path in saved_paths:
                try:
                    UPLOAD_STORE.cleanup(saved_path)
                except OSError as exc:
                    logger.warning(
                        "chat request cleanup failed request_id=%s thread_id=%s endpoint=%s error=%s",
                        request_id,
                        thread_id,
                        endpoint,
                        str(exc),
                    )
            duration_ms = int((perf_counter() - request_start) * 1000)
            logger.info(
                "chat request finished request_id=%s thread_id=%s endpoint=%s status=%s duration_ms=%s upload_ms=%s tool_ms=%s error=%s images_count=%s",
                request_id,
                thread_id,
                endpoint,
                metrics.get("status", "success"),
                duration_ms,
                upload_ms,
                metrics.get("tool_ms", 0),
                metrics.get("error", ""),
                len(saved_paths),
            )

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream; charset=utf-8",
    )
