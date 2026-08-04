from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import re
from time import perf_counter
from typing import Any

import requests

from config import load_config

from backend.api.schemas import (
    DoneEventData,
    ErrorEventData,
    StartEventData,
    TokenEventData,
    ToolEventData,
    ToolResultItemData,
)
from backend.api.sse import to_sse

logger = logging.getLogger(__name__)


def _extract_message(chunk: Any) -> Any:
    if isinstance(chunk, tuple) and len(chunk) == 2:
        return chunk[0]
    return chunk


def _message_to_dict(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        return message
    if hasattr(message, "model_dump"):
        return message.model_dump()
    if hasattr(message, "dict"):
        return message.dict()
    return {"role": str(message.__class__.__name__), "content": getattr(message, "content", str(message))}


def _build_tool_event_data(message: dict[str, Any], tool_text: str, artifact: dict[str, Any]) -> ToolEventData:
    tool_name = str(message.get("name") or "detect_objects")
    items_raw = artifact.get("items")
    items: list[ToolResultItemData] | None = None
    if isinstance(items_raw, list):
        items = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            image_path = str(item.get("image_path") or "")
            items.append(
                ToolResultItemData(
                    image_path=image_path or None,
                    image_name=Path(image_path).name if image_path else None,
                    summary=str(item.get("summary") or "检测工具已返回结果"),
                    result_text=str(item.get("result_text") or item.get("summary") or ""),
                    image_url=str(item.get("image_url") or "") or None,
                    detections_count=item.get("detections_count"),
                    perf_total_ms=item.get("perf_total_ms"),
                    success=item.get("success"),
                    geo_center=item.get("geo_center"),
                    geo_status=item.get("geo_status"),
                    detection_geos=item.get("detection_geos"),
                )
            )

    return ToolEventData(
        name=tool_name,
        phase="result",
        summary=str(artifact.get("summary") or "检测工具已返回结果"),
        result_text=str(artifact.get("result_text") or tool_text or ""),
        image_url=str(artifact.get("image_url") or "") or None,
        detections_count=artifact.get("detections_count"),
        perf_total_ms=artifact.get("perf_total_ms"),
        images_count=artifact.get("images_count"),
        success_count=artifact.get("success_count"),
        failure_count=artifact.get("failure_count"),
        detected_images_count=artifact.get("detected_images_count"),
        total_detections_count=artifact.get("total_detections_count"),
        items=items,
        geo_center=artifact.get("geo_center") if not items_raw else None,
        geo_status=artifact.get("geo_status") if not items_raw else None,
        detection_geos=artifact.get("detection_geos") if not items_raw else None,
    )


def _extract_events(chunk: Any) -> list[tuple[str, Any]]:
    message = _message_to_dict(_extract_message(chunk))

    role = str(message.get("role") or "").lower()
    message_type = str(message.get("type") or "").lower()
    message_name = str(message.get("name") or "").lower()
    if role == "tool" or message_type == "tool" or message_name in {"detect_objects", "detect_objects_batch"}:
        tool_content = message.get("content")
        if isinstance(tool_content, list):
            tool_text = "\n".join(str(item) for item in tool_content if item)
        else:
            tool_text = str(tool_content or "")
        artifact = message.get("artifact") or {}
        return [
            (
                "tool",
                _build_tool_event_data(message, tool_text, artifact),
            )
        ]

    content = message.get("content")
    if isinstance(content, str) and content:
        return [("token", TokenEventData(text=content))]

    if role in ("ai", "aimessagechunk", "assistant") and isinstance(content, list):
        events: list[tuple[str, Any]] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    events.append(("token", TokenEventData(text=text)))
            elif isinstance(item, str) and item:
                events.append(("token", TokenEventData(text=item)))
        return events

    if isinstance(content, list):
        events: list[tuple[str, Any]] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    events.append(("token", TokenEventData(text=text)))
            elif isinstance(item, str) and item:
                events.append(("token", TokenEventData(text=item)))
        return events

    return []


def _immediate_detection_events(image_paths: list[Path], tool_name: str) -> list[tuple[str, ToolEventData]]:
    from backend.services.detection_service import detect_image_with_artifact, detect_images_with_artifact

    if not image_paths:
        return []

    if len(image_paths) == 1:
        tool_text, artifact = detect_image_with_artifact(str(image_paths[0]))
        return [("tool", _build_tool_event_data({"name": tool_name}, tool_text, artifact))]

    tool_text, artifact = detect_images_with_artifact([str(path) for path in image_paths])
    return [("tool", _build_tool_event_data({"name": tool_name}, tool_text, artifact))]


def _artifact_prompt(tool_events: list[tuple[str, ToolEventData]]) -> str:
    if not tool_events:
        return ""
    payloads = [event.model_dump(mode="json") for _, event in tool_events]
    return (
        "检测工具已经完成，下面是工具返回的结构化结果 JSON。"
        "请基于这些真实检测结果做简短中文总结；不要编造不存在的目标。\n"
        f"{json.dumps(payloads, ensure_ascii=False)}"
    )


def _prefer_english(user_message: str) -> bool:
    english_chars = len(re.findall(r"[A-Za-z]", user_message or ""))
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", user_message or ""))
    return english_chars > chinese_chars


def _format_detection_classes(detection_geos: list[dict] | None, *, limit: int = 12) -> str:
    if not detection_geos:
        return ""

    counts: dict[str, int] = {}
    confidences: dict[str, list[float]] = {}
    for item in detection_geos:
        label = str(item.get("class") or item.get("label") or item.get("name") or "object")
        counts[label] = counts.get(label, 0) + 1
        score = item.get("confidence", item.get("score"))
        if isinstance(score, int | float):
            confidences.setdefault(label, []).append(float(score))

    parts: list[str] = []
    for label, count in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[:limit]:
        scores = confidences.get(label) or []
        if scores:
            parts.append(f"{label} x{count}, confidence {min(scores):.1%}-{max(scores):.1%}")
        else:
            parts.append(f"{label} x{count}")
    return "; ".join(parts)


def _build_reasoning_context(tool_events: list[tuple[str, ToolEventData]], *, english: bool = False) -> str:
    result_events = [event for _, event in tool_events if event.phase == "result"]
    if not result_events:
        return ""

    if len(result_events) == 1 and not result_events[0].items:
        event = result_events[0]
        geo_text = "无"
        if event.geo_center:
            geo_text = f"[{event.geo_center[0]:.5f}, {event.geo_center[1]:.5f}]"
        if english:
            classes = _format_detection_classes(event.detection_geos)
            return (
                "Single image detection result:\n"
                f"Summary: {event.detections_count or 0} objects detected.\n"
                f"Geo center: {geo_text}\n"
                f"Classes: {classes or 'see structured detection details'}"
            )
        return (
            f"单图检测结果：\n"
            f"摘要：{event.summary}\n"
            f"目标数：{event.detections_count or 0}\n"
            f"中心经纬度：{geo_text}\n"
            f"明细：{event.result_text or event.summary}"
        )

    lines: list[str] = []
    for event in result_events:
        if event.items:
            for item in event.items:
                if english:
                    lines.append(
                        f"- {item.image_name or item.image_path or 'image'}: {item.detections_count or 0} objects detected"
                    )
                    continue
                lines.append(
                    f"- {item.image_name or item.image_path or '图片'}：{item.summary}，目标数 {item.detections_count or 0}"
                )
        else:
            if english:
                lines.append(f"- {event.name}: {event.detections_count or 0} objects detected")
                continue
            lines.append(f"- {event.name}：{event.summary}，目标数 {event.detections_count or 0}")
    if english:
        return "Batch detection result:\n" + "\n".join(lines)
    return "批量检测结果：\n" + "\n".join(lines)


def _build_local_llm_payload(
    user_message: str,
    tool_events: list[tuple[str, ToolEventData]],
    *,
    stream: bool,
) -> tuple[str, dict[str, Any], dict[str, str]]:
    english = _prefer_english(user_message)
    context = _build_reasoning_context(tool_events, english=english)
    if not context:
        return "", {}, {}

    app_config = load_config()
    url = f"{app_config.llm.api_base.rstrip('/')}/chat/completions"
    if english:
        system_prompt = "You are a remote-sensing object detection analyst. You must answer in English only. Do not use Chinese."
        prompt = (
            "Analyze only the real YOLO detection results below. Do not invent objects. "
            "Do not include unrelated greetings. Keep the answer within 120 words.\n"
            f"User question: {user_message}\n"
            f"Detection context:\n{context}\n"
            "Output what was detected, how reliable the confidence scores are, and mention that the annotated result image is available."
        )
    else:
        system_prompt = "你是遥感目标检测结果分析助手。你必须只用中文回答，不要使用英文寒暄。"
        prompt = (
            "请只根据下面的YOLO真实检测结果进行推理总结，不要编造未出现的目标；"
            "不要输出寒暄；控制在120字以内。\n"
            f"用户问题：{user_message}\n"
            f"{context}\n"
            "请输出：检测到了什么、置信度/可靠性如何、结果图已返回可查看标注位置。"
        )
    payload = {
        "model": app_config.llm.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": app_config.llm.temperature,
        "max_tokens": min(app_config.llm.max_tokens, 512),
        "stream": stream,
    }
    headers = {"Content-Type": "application/json"}
    if app_config.llm.api_key:
        headers["Authorization"] = f"Bearer {app_config.llm.api_key}"
    return url, payload, headers


def _local_llm_reasoning_text(user_message: str, tool_events: list[tuple[str, ToolEventData]]) -> str:
    url, payload, headers = _build_local_llm_payload(user_message, tool_events, stream=False)
    if not url:
        return ""

    app_config = load_config()
    response = requests.post(url, json=payload, headers=headers, timeout=app_config.llm.request_timeout)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("本地语言服务未返回 choices")
    message = choices[0].get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise ValueError("本地语言服务返回内容为空")
    return content


def _stream_local_llm_reasoning_tokens(user_message: str, tool_events: list[tuple[str, ToolEventData]]) -> Iterator[str]:
    url, payload, headers = _build_local_llm_payload(user_message, tool_events, stream=True)
    if not url:
        return

    app_config = load_config()
    with requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=app_config.llm.request_timeout,
        stream=True,
    ) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            data_text = line[5:].strip()
            if not data_text or data_text == "[DONE]":
                continue
            try:
                data = json.loads(data_text)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            text = delta.get("content")
            if text:
                yield str(text)


def stream_chat_events(
    *,
    agent: Any,
    message: str,
    thread_id: str,
    image_paths: list[Path] | None,
    request_id: str,
    metrics: dict[str, Any] | None = None,
) -> Iterator[str]:
    start_time = perf_counter()
    tool_result_emitted = False
    image_paths = image_paths or []

    if image_paths:
        if len(image_paths) == 1:
            user_content = (
                f"用户消息：{message}\n"
                f"图片路径：{image_paths[0]}\n"
                "如需分析图片内容，请优先使用 detect_objects 工具检测图片中的物体，再结合工具摘要做简短分析回答。"
                "前端会单独展示工具的完整检测图与明细，默认不要把这些明细逐条复述给用户。"
            )
            tool_name = "detect_objects"
            tool_summary = "正在调用检测工具分析图片"
        else:
            joined_paths = "\n".join(f"- {path}" for path in image_paths)
            user_content = (
                f"用户消息：{message}\n"
                f"图片路径列表：\n{joined_paths}\n"
                "如需分析这批图片内容，请优先使用 detect_objects_batch 工具做批量检测，"
                "再结合工具摘要做整体概括，并按需要指出图片之间的差异。"
                "前端会单独展示工具返回的完整检测图与逐图明细，默认不要逐条复述全部明细。"
            )
            tool_name = "detect_objects_batch"
            tool_summary = f"正在调用批量检测工具分析 {len(image_paths)} 张图片"
    else:
        user_content = (
            f"用户消息：{message}\n"
            "当前没有上传图片。\n"
            "如果用户的问题依赖图片内容，请明确提示用户先上传图片；"
            "如果是普通文本问答或产品使用说明，则直接回答。"
        )
        tool_name = "detect_objects"
        tool_summary = "等待图片上传"

    direct_tool_events: list[tuple[str, ToolEventData]] = []
    if image_paths:
        direct_tool_events = _immediate_detection_events(image_paths, tool_name)
        artifact_prompt = _artifact_prompt(direct_tool_events)
        if artifact_prompt:
            user_content = f"{user_content}\n\n{artifact_prompt}"

    payload = {
        "messages": [
            {
                "role": "user",
                "content": user_content,
            }
        ]
    }
    config = {"configurable": {"thread_id": thread_id}}

    yield to_sse(
        "start",
        StartEventData(
            request_id=request_id,
            thread_id=thread_id,
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        ),
    )
    if image_paths:
        yield to_sse(
            "tool",
            ToolEventData(
                name=tool_name,
                phase="start",
                summary=tool_summary,
                images_count=len(image_paths),
            ),
        )
    try:
        for event_name, payload_data in direct_tool_events:
            tool_result_emitted = True
            yield to_sse(event_name, payload_data)

        reasoning_context = _build_reasoning_context(direct_tool_events)
        if reasoning_context:
            emitted_reasoning_token = False
            try:
                for reasoning_token in _stream_local_llm_reasoning_tokens(message, direct_tool_events):
                    emitted_reasoning_token = True
                    yield to_sse("token", TokenEventData(text=reasoning_token))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "local llm reasoning stream failed request_id=%s thread_id=%s emitted=%s error=%s",
                    request_id,
                    thread_id,
                    emitted_reasoning_token,
                    str(exc),
                )
                if not emitted_reasoning_token:
                    yield to_sse("token", TokenEventData(text=f"本地语言服务推理失败：{exc}。检测结果图和工具明细已返回。"))
            elapsed_ms = int((perf_counter() - start_time) * 1000)
            if metrics is not None:
                metrics["tool_ms"] = elapsed_ms
                metrics["status"] = "success"
            logger.info(
                "chat stream finished request_id=%s thread_id=%s status=success tool_ms=%s mode=direct",
                request_id,
                thread_id,
                elapsed_ms,
            )
            yield to_sse("done", DoneEventData(request_id=request_id, duration_ms=elapsed_ms))
            return

        for chunk in agent.stream(payload, config=config, stream_mode="messages"):
            for event_name, payload_data in _extract_events(chunk):
                if event_name == "tool" and getattr(payload_data, "phase", "") == "result":
                    tool_result_emitted = True
                yield to_sse(event_name, payload_data)

        elapsed_ms = int((perf_counter() - start_time) * 1000)
        if metrics is not None:
            metrics["tool_ms"] = elapsed_ms
            metrics["status"] = "success"
        logger.info(
            "chat stream finished request_id=%s thread_id=%s status=success tool_ms=%s",
            request_id,
            thread_id,
            elapsed_ms,
        )
        yield to_sse("done", DoneEventData(request_id=request_id, duration_ms=elapsed_ms))
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((perf_counter() - start_time) * 1000)
        if metrics is not None:
            metrics["tool_ms"] = elapsed_ms
            metrics["status"] = "error"
            metrics["error"] = str(exc)
        logger.warning(
            "chat stream failed request_id=%s thread_id=%s status=error tool_ms=%s error=%s",
            request_id,
            thread_id,
            elapsed_ms,
            str(exc),
        )
        if tool_result_emitted:
            fallback_text = (
                "检测结果已经返回，但当前模型总结超时。"
                "你可以先查看左侧结果图和工具结果明细，再决定是否继续追问。"
            )
            yield to_sse("token", TokenEventData(text=fallback_text))
            yield to_sse("done", DoneEventData(request_id=request_id, duration_ms=elapsed_ms))
            return
        yield to_sse(
            "error",
            ErrorEventData(code="DETECTION_FAILED", message=f"检测失败：{exc}"),
        )
