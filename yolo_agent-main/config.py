from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(slots=True)
class LLMConfig:
    api_base: str = "http://127.0.0.1:8080/v1"
    model: str = "local-model"
    api_key: str = ""
    temperature: float = 0.3
    max_tokens: int = 1024
    request_timeout: int = 120


@dataclass(slots=True)
class DetectionConfig:
    api_base: str = "http://127.0.0.1:8003"
    api_key: str = ""
    obj_thresh: float = 0.25
    nms_thresh: float = 0.45
    request_timeout: int = 30
    return_image: bool = True
    return_boxes: bool = True
    image_mode: str = "base64"
    geo_mode: str = "required"


@dataclass(slots=True)
class AgentConfig:
    system_prompt: str = (
        "你是一个专业的遥感图像旋转目标检测与地理定位助手。"
        "用户会提供图片路径，当用户想要检测、识别、找出图片中的物体时，请立即使用检测工具。"
        "检测工具会返回旋转目标框（OBB）、类别、置信度及经纬度坐标。"
        "如果用户一次性提供多张图片，请优先使用 detect_objects_batch；单张则用 detect_objects。\n"
        "前端会单独展示工具返回的检测标注图和完整明细。"
        "当检测工具返回后，你只需要基于工具摘要做简短中文分析："
        "说明检测到了什么、结果是否可靠、经纬度定位情况，必要时补一句分布特点或后续建议。"
        "除非用户明确要求，不要逐条重复坐标、编号或原始清单。"
    )
    thread_id: str = "default"
    streaming: bool = False
    checkpoint_db_path: str = "runtime/checkpoints/agent-checkpoints.db"


@dataclass(slots=True)
class AppConfig:
    llm: LLMConfig
    detection: DetectionConfig
    agent: AgentConfig


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")


def _read_yaml_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"配置文件格式错误：{config_path} 顶层必须是对象")

    return data


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _build_env_override() -> dict[str, Any]:
    env: dict[str, Any] = {"llm": {}, "detection": {}, "agent": {}}

    mapping: list[tuple[str, str, str, Any]] = [
        ("llm", "api_base", "ASSISTANT_LLM_API_BASE", str),
        ("llm", "model", "ASSISTANT_LLM_MODEL", str),
        ("llm", "api_key", "ASSISTANT_LLM_API_KEY", str),
        ("llm", "temperature", "ASSISTANT_LLM_TEMPERATURE", float),
        ("llm", "max_tokens", "ASSISTANT_LLM_MAX_TOKENS", int),
        ("llm", "request_timeout", "ASSISTANT_LLM_REQUEST_TIMEOUT", int),
        ("detection", "api_base", "NWPU_VHR_API_BASE", str),
        ("detection", "api_key", "NWPU_VHR_API_KEY", str),
        ("detection", "obj_thresh", "DEFAULT_OBJ_THRESH", float),
        ("detection", "nms_thresh", "DEFAULT_NMS_THRESH", float),
        ("detection", "request_timeout", "NWPU_VHR_REQUEST_TIMEOUT", int),
        ("detection", "image_mode", "NWPU_VHR_IMAGE_MODE", str),
        ("detection", "return_image", "NWPU_VHR_RETURN_IMAGE", _as_bool),
        ("detection", "return_boxes", "NWPU_VHR_RETURN_BOXES", _as_bool),
        ("detection", "geo_mode", "DETECTION_GEO_MODE", str),
        ("agent", "system_prompt", "AGENT_SYSTEM_PROMPT", str),
        ("agent", "thread_id", "AGENT_DEFAULT_THREAD_ID", str),
        ("agent", "streaming", "AGENT_STREAMING", _as_bool),
        ("agent", "checkpoint_db_path", "AGENT_CHECKPOINT_DB_PATH", str),
    ]

    for section, key, env_name, caster in mapping:
        raw_value = os.getenv(env_name)
        if raw_value in (None, ""):
            continue
        env[section][key] = caster(raw_value)

    return env


def load_config(config_path: str | Path | None = None) -> AppConfig:
    load_dotenv()

    resolved_path = Path(config_path or os.getenv("YOLO_AGENT_CONFIG", DEFAULT_CONFIG_PATH))
    file_config = _read_yaml_config(resolved_path)
    merged = _deep_merge(file_config, _build_env_override())

    llm_raw = merged.get("llm", {})
    detection_raw = merged.get("detection", {})
    agent_raw = merged.get("agent", {})

    return AppConfig(
        llm=LLMConfig(**llm_raw),
        detection=DetectionConfig(**detection_raw),
        agent=AgentConfig(**agent_raw),
    )
