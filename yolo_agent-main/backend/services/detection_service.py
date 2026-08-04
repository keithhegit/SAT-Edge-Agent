from __future__ import annotations

from collections import Counter
import mimetypes
from pathlib import Path

import requests

from config import load_config


def _validate_threshold(name: str, value: float) -> str | None:
    if 0 <= value <= 1:
        return None
    return f"检测失败：{name} 必须在 0 到 1 之间"


def _assess_confidence(avg_conf: float, min_conf: float) -> str:
    if min_conf >= 80 and avg_conf >= 88:
        return "整体置信度较高"
    if min_conf >= 60 and avg_conf >= 75:
        return "整体置信度较稳定"
    return "结果可参考，但低置信度目标建议结合原图再确认"


def _assess_distribution(detections: list[dict]) -> str:
    if len(detections) <= 1:
        return "目标位置相对集中"

    centers_x: list[float] = []
    centers_y: list[float] = []

    for det in detections:
        pixel_center = det.get("pixel_center", [])
        if len(pixel_center) != 2:
            continue
        centers_x.append(pixel_center[0])
        centers_y.append(pixel_center[1])

    if len(centers_x) <= 1:
        return "目标位置相对集中"

    x_span = max(centers_x) - min(centers_x)
    y_span = max(centers_y) - min(centers_y)

    if x_span > 300 or y_span > 300:
        return "目标分布较分散"
    return "目标分布较集中"


def _build_model_summary_text(
    detections: list[dict],
    summary: str,
    perf_total_ms: float,
) -> str:
    confidences = [((det.get("confidence") if det.get("confidence") is not None else det.get("score")) or 0) * 100 for det in detections]
    min_conf = min(confidences)
    max_conf = max(confidences)
    avg_conf = sum(confidences) / len(confidences)
    confidence_assessment = _assess_confidence(avg_conf, min_conf)
    distribution_assessment = _assess_distribution(detections)
    return (
        f"工具摘要：共检测到 {len(detections)} 个目标，类别统计为 {summary}。"
        f"置信度范围 {min_conf:.1f}%-{max_conf:.1f}%，平均 {avg_conf:.1f}%，{confidence_assessment}。"
        f"{distribution_assessment}，检测耗时 {perf_total_ms:.1f}ms。"
        "前端已单独展示完整检测清单和标注图。默认请只做简短分析，不要逐条重复坐标、编号或原始明细；"
        "除非用户明确要求详细列表。"
    )


def _build_batch_model_summary(items: list[dict[str, object]]) -> str:
    total_images = len(items)
    success_items = [item for item in items if item.get("success") is True]
    failed_items = [item for item in items if item.get("success") is False]
    detected_items = [item for item in success_items if int(item.get("detections_count") or 0) > 0]
    total_detections = sum(int(item.get("detections_count") or 0) for item in success_items)
    total_perf_ms = sum(float(item.get("perf_total_ms") or 0.0) for item in success_items)

    class_counter: Counter[str] = Counter()
    lines: list[str] = []
    for item in items:
        image_path = str(item.get("image_path") or "")
        image_name = Path(image_path).name or image_path or "unknown"
        if item.get("success") is not True:
            lines.append(f"- {image_name}：处理失败，原因：{item.get('summary') or '未知错误'}")
            continue

        detections_count = int(item.get("detections_count") or 0)
        classes = item.get("classes") or {}
        if isinstance(classes, dict):
            class_counter.update({str(name): int(count) for name, count in classes.items()})
        if detections_count > 0 and isinstance(classes, dict) and classes:
            class_summary = "，".join(f"{name}({count}个)" for name, count in sorted(classes.items()))
            lines.append(f"- {image_name}：检测到 {detections_count} 个目标，类别为 {class_summary}")
        elif detections_count > 0:
            lines.append(f"- {image_name}：检测到 {detections_count} 个目标")
        else:
            lines.append(f"- {image_name}：未检测到明确目标")

    top_classes = "、".join(f"{name}({count}个)" for name, count in class_counter.most_common(5)) or "无"
    detail_text = "\n".join(lines)
    return (
        f"工具摘要：本次共处理 {total_images} 张图片，成功 {len(success_items)} 张，失败 {len(failed_items)} 张。"
        f"其中有 {len(detected_items)} 张检测到目标，总计检测到 {total_detections} 个目标，"
        f"高频类别包括 {top_classes}，累计检测耗时 {total_perf_ms:.1f}ms。"
        "请先做整体中文概括，再按需要点出哪几张图目标更多、哪几张未检出或失败；"
        "默认不要逐条重复所有坐标和原始明细，除非用户明确要求。"
        + (f"\n逐图摘要：\n{detail_text}" if detail_text else "")
    )


def detect_image_with_artifact(
    image_path: str,
    obj_thresh: float | None = None,
    nms_thresh: float | None = None,
) -> tuple[str, dict[str, object]]:
    """调用 YOLO 检测服务并格式化返回结果。"""
    path = Path(image_path)
    if not path.exists():
        message = f"错误：文件不存在 '{image_path}'"
        return message, {"summary": message, "result_text": message, "image_url": "", "detections_count": 0, "perf_total_ms": 0.0}

    if not path.is_file():
        message = f"错误：'{image_path}' 不是有效文件"
        return message, {"summary": message, "result_text": message, "image_url": "", "detections_count": 0, "perf_total_ms": 0.0}

    detection_config = load_config().detection
    final_obj_thresh = detection_config.obj_thresh if obj_thresh is None else obj_thresh
    final_nms_thresh = detection_config.nms_thresh if nms_thresh is None else nms_thresh
    threshold_error = _validate_threshold("obj_thresh", final_obj_thresh)
    if threshold_error:
        return threshold_error, {
            "summary": threshold_error,
            "result_text": threshold_error,
            "image_url": "",
            "detections_count": 0,
            "perf_total_ms": 0.0,
        }

    threshold_error = _validate_threshold("nms_thresh", final_nms_thresh)
    if threshold_error:
        return threshold_error, {
            "summary": threshold_error,
            "result_text": threshold_error,
            "image_url": "",
            "detections_count": 0,
            "perf_total_ms": 0.0,
        }

    url = f"{detection_config.api_base}/v1/detect"
    headers: dict[str, str] = {}
    if detection_config.api_key:
        headers["X-API-Key"] = detection_config.api_key
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    try:
        with path.open("rb") as f:
            files = {"image": (path.name, f, mime_type)}
            data = {
                "return_image": "true",
                "return_boxes": str(detection_config.return_boxes).lower(),
                "image_mode": detection_config.image_mode,
                "obj_thresh": str(final_obj_thresh),
                "nms_thresh": str(final_nms_thresh),
                "geo_mode": detection_config.geo_mode,
            }

            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=detection_config.request_timeout,
            )
            response.raise_for_status()
        try:
            result = response.json()
        except ValueError:
            message = "检测失败：检测服务返回了无效的 JSON 响应"
            return message, {"summary": message, "result_text": message, "image_url": "", "detections_count": 0, "perf_total_ms": 0.0, "geo_center": None, "geo_status": None, "detection_geos": None}
    except requests.exceptions.Timeout:
        message = "检测超时，请稍后重试"
        return message, {"summary": message, "result_text": message, "image_url": "", "detections_count": 0, "perf_total_ms": 0.0, "geo_center": None, "geo_status": None, "detection_geos": None}
    except requests.exceptions.RequestException as e:
        message = f"检测失败：{str(e)}"
        return message, {"summary": message, "result_text": message, "image_url": "", "detections_count": 0, "perf_total_ms": 0.0, "geo_center": None, "geo_status": None, "detection_geos": None}
    except Exception as e:
        message = f"检测失败：{str(e)}"
        return message, {"summary": message, "result_text": message, "image_url": "", "detections_count": 0, "perf_total_ms": 0.0, "geo_center": None, "geo_status": None, "detection_geos": None}

    detections = result.get("detections", [])
    image_info = result.get("image") or {}
    center_geo = image_info.get("center_geo")
    geo_status = result.get("geo_status", "ok")
    image_payload = result.get("image_result") or image_info or {}
    image_base64 = image_payload.get("value")
    image_data_url = ""
    if image_payload.get("mode") == "base64" and isinstance(image_base64, str) and image_base64:
        image_data_url = f"data:image/jpeg;base64,{image_base64}"

    if not detections:
        message = "检测完成：未在图片中发现任何目标。"
        model_summary = (
            "工具摘要：本次未检测到明确目标。"
            "请简要告知用户当前未检出物体，并可建议检查图片清晰度、目标大小或阈值设置；不要编造检测结果。"
        )
        return model_summary, {
            "summary": message,
            "result_text": message,
            "image_url": image_data_url,
            "detections_count": 0,
            "perf_total_ms": float((result.get("perf") or {}).get("total_ms", 0)),
            "classes": {},
            "geo_center": center_geo,
            "geo_status": geo_status,
            "detection_geos": None,
        }

    counter = Counter(d.get("class_name", "unknown") for d in detections)
    summary_parts = [f"{name} ({count}个)" for name, count in sorted(counter.items())]
    summary = "，".join(summary_parts)

    perf = result.get("perf", {})
    perf_str = f"总耗时 {perf.get('total_ms', 0):.1f}ms"

    details: list[str] = []
    for i, det in enumerate(detections, 1):
        cls = det.get("class_name", "unknown")
        conf = ((det.get("confidence") if det.get("confidence") is not None else det.get("score")) or 0) * 100
        geo = det.get("geo_center")
        geo_str = f"，经纬度 [{geo[0]:.5f}, {geo[1]:.5f}]" if geo and len(geo) == 2 else ""
        details.append(f"  {i}. {cls}（置信度 {conf:.1f}%{geo_str}）")

    result_text = (
        f"检测完成！共发现 {len(detections)} 个目标：{summary}\n"
        f"{perf_str}\n"
        f"详细结果：\n" + "\n".join(details)
    )

    detection_geos: list[dict[str, object]] | None = None
    geo_dets = [det for det in detections if det.get("geo_center")]
    if geo_dets:
        detection_geos = [
            {
                "class_name": det.get("class_name", ""),
                "confidence": (det.get("confidence") if det.get("confidence") is not None else det.get("score")) or 0,
                "geo_center": det.get("geo_center"),
            }
            for det in geo_dets
        ]

    geo_summary = ""
    if center_geo and len(center_geo) == 2:
        geo_summary = f"图片中心经纬度 [{center_geo[0]:.5f}, {center_geo[1]:.5f}]，"

    model_summary = _build_model_summary_text(detections, summary, float(perf.get("total_ms", 0)))
    if geo_summary:
        model_summary = geo_summary + model_summary

    return model_summary, {
        "summary": f"检测完成，共发现 {len(detections)} 个目标",
        "result_text": result_text,
        "image_url": image_data_url,
        "detections_count": len(detections),
        "perf_total_ms": float(perf.get("total_ms", 0)),
        "classes": dict(counter),
        "geo_center": center_geo,
        "geo_status": geo_status,
        "detection_geos": detection_geos,
    }


def detect_images_with_artifact(
    image_paths: list[str],
    obj_thresh: float | None = None,
    nms_thresh: float | None = None,
) -> tuple[str, dict[str, object]]:
    """批量调用 YOLO 检测服务并聚合返回结果。"""
    if not image_paths:
        message = "检测失败：image_paths 不能为空"
        return message, {
            "summary": message,
            "result_text": message,
            "images_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "detected_images_count": 0,
            "total_detections_count": 0,
            "items": [],
        }

    items: list[dict[str, object]] = []
    for image_path in image_paths:
        _, artifact = detect_image_with_artifact(
            image_path=image_path,
            obj_thresh=obj_thresh,
            nms_thresh=nms_thresh,
        )
        summary = str(artifact.get("summary") or artifact.get("result_text") or "")
        item = {
            "image_path": image_path,
            "summary": summary,
            "result_text": str(artifact.get("result_text") or summary),
            "image_url": str(artifact.get("image_url") or ""),
            "detections_count": int(artifact.get("detections_count") or 0),
            "perf_total_ms": float(artifact.get("perf_total_ms") or 0.0),
            "classes": artifact.get("classes") if isinstance(artifact.get("classes"), dict) else {},
            "success": not summary.startswith("错误：") and not summary.startswith("检测失败：") and not summary.startswith("检测超时"),
            "geo_center": artifact.get("geo_center"),
            "geo_status": artifact.get("geo_status"),
            "detection_geos": artifact.get("detection_geos"),
        }
        items.append(item)

    success_count = sum(1 for item in items if item["success"] is True)
    failure_count = len(items) - success_count
    detected_images_count = sum(1 for item in items if item["success"] is True and int(item["detections_count"]) > 0)
    total_detections_count = sum(int(item["detections_count"]) for item in items if item["success"] is True)

    summary = (
        f"批量检测完成，共处理 {len(items)} 张图片，"
        f"成功 {success_count} 张，失败 {failure_count} 张，"
        f"其中 {detected_images_count} 张检测到目标，总计 {total_detections_count} 个目标"
    )
    detail_lines = [
        f"- {Path(str(item['image_path'])).name or item['image_path']}：{item['summary']}"
        for item in items
    ]
    result_text = summary + "\n逐图结果：\n" + "\n".join(detail_lines)

    return _build_batch_model_summary(items), {
        "summary": summary,
        "result_text": result_text,
        "images_count": len(items),
        "success_count": success_count,
        "failure_count": failure_count,
        "detected_images_count": detected_images_count,
        "total_detections_count": total_detections_count,
        "items": items,
    }


def detect_image(
    image_path: str,
    obj_thresh: float | None = None,
    nms_thresh: float | None = None,
) -> str:
    _, artifact = detect_image_with_artifact(image_path=image_path, obj_thresh=obj_thresh, nms_thresh=nms_thresh)
    return str(artifact.get("result_text") or artifact.get("summary") or "")


def detect_images(
    image_paths: list[str],
    obj_thresh: float | None = None,
    nms_thresh: float | None = None,
) -> str:
    _, artifact = detect_images_with_artifact(image_paths=image_paths, obj_thresh=obj_thresh, nms_thresh=nms_thresh)
    return str(artifact.get("result_text") or artifact.get("summary") or "")
