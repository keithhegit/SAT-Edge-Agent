from __future__ import annotations

import json
from typing import Any


def to_sse(event: str, data: Any) -> str:
    if hasattr(data, "model_dump"):
        payload = json.dumps(data.model_dump(mode="json"), ensure_ascii=False)
    elif isinstance(data, str):
        payload = data
    else:
        payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
