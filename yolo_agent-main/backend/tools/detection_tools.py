from __future__ import annotations

from langchain_core.tools import tool

from backend.services.detection_service import detect_image_with_artifact, detect_images_with_artifact


@tool(response_format="content_and_artifact")
def detect_objects(
    image_path: str,
    obj_thresh: float | None = None,
    nms_thresh: float | None = None,
) -> tuple[str, dict[str, object]]:
    """【工具】OBB旋转目标检测 + 经纬度定位 - 当用户想要检测、识别、找出图片中的旋转目标并获取经纬度时使用

    Args:
        image_path: 待检测图片路径（文件名需匹配geo记录才能获取经纬度）
        obj_thresh: 置信度阈值，范围 0-1，留空时使用当前配置值
        nms_thresh: NMS IoU 阈值，范围 0-1，留空时使用当前配置值

    Returns:
        检测结果含旋转框、类别、置信度及经纬度坐标
    """
    return detect_image_with_artifact(image_path=image_path, obj_thresh=obj_thresh, nms_thresh=nms_thresh)


@tool(response_format="content_and_artifact")
def detect_objects_batch(
    image_paths: list[str],
    obj_thresh: float | None = None,
    nms_thresh: float | None = None,
) -> tuple[str, dict[str, object]]:
    """【工具】批量OBB旋转目标检测 + 经纬度定位 - 当用户一次性提供多张图片，或要求批量检测、比较多张图片结果时使用

    Args:
        image_paths: 待批量检测的图片路径列表
        obj_thresh: 置信度阈值，范围 0-1，留空时使用当前配置值
        nms_thresh: NMS IoU 阈值，范围 0-1，留空时使用当前配置值

    Returns:
        批量检测结果含旋转框、类别、置信度及经纬度坐标
    """
    return detect_images_with_artifact(image_paths=image_paths, obj_thresh=obj_thresh, nms_thresh=nms_thresh)


TOOLS = [detect_objects, detect_objects_batch]
