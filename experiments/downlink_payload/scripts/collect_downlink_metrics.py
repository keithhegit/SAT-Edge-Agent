from __future__ import annotations

import argparse
import base64
import csv
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit("This script requires requests. Install with: pip install requests") from exc


DEFAULT_RATES_KBPS = [9.6, 100, 1000, 10_000, 100_000]


def byte_len(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def transfer_seconds(byte_count: int, kbps: float) -> float:
    return (byte_count * 8) / (kbps * 1000)


def strip_image_payload(result: dict[str, Any]) -> dict[str, Any]:
    stripped = json.loads(json.dumps(result, ensure_ascii=False))
    for key in ("image_result", "image"):
        payload = stripped.get(key)
        if isinstance(payload, dict) and isinstance(payload.get("value"), str):
            payload["value"] = f"<removed:{len(payload['value'])} base64 chars>"
    return stripped


def estimate_annotated_image_bytes(result: dict[str, Any]) -> int:
    for key in ("image_result", "image"):
        payload = result.get(key)
        if not isinstance(payload, dict):
            continue
        value = payload.get("value")
        mode = payload.get("mode")
        if mode == "base64" and isinstance(value, str) and value:
            try:
                return len(base64.b64decode(value, validate=False))
            except Exception:
                return int(len(value) * 0.75)
    return 0


def compact_summary(result: dict[str, Any]) -> str:
    detections = result.get("detections") or []
    classes: dict[str, int] = {}
    geo_count = 0
    for det in detections:
        cls = str(det.get("class_name") or "unknown")
        classes[cls] = classes.get(cls, 0) + 1
        if det.get("geo_center"):
            geo_count += 1
    class_text = ", ".join(f"{name}:{count}" for name, count in sorted(classes.items())) or "none"
    perf = result.get("perf") or {}
    total_ms = perf.get("total_ms")
    return (
        f"detections={len(detections)}; classes={class_text}; "
        f"geo_targets={geo_count}; total_ms={total_ms}"
    )


def call_yolo(yolo_url: str, image_path: Path, timeout: int) -> dict[str, Any]:
    with image_path.open("rb") as fh:
        files = {"image": (image_path.name, fh, "image/jpeg")}
        data = {
            "return_image": "true",
            "return_boxes": "true",
            "image_mode": "base64",
            "geo_mode": "required",
        }
        try:
            response = requests.post(yolo_url, files=files, data=data, timeout=timeout)
        except requests.exceptions.ConnectionError as exc:
            host = urlparse(yolo_url).hostname or ""
            hint = (
                "The URL uses localhost/127.0.0.1, so it points to the machine running this script. "
                "If YOLO is on another edge host, run this script on that host or pass "
                "--yolo-url http://<edge-host>:8003/v1/detect."
            )
            if host not in {"127.0.0.1", "localhost", "::1"}:
                hint = (
                    "Check that the YOLO service is running, bound to 0.0.0.0, and that the firewall "
                    "allows access to port 8003 from this machine."
                )
            raise SystemExit(
                f"Cannot connect to YOLO service at {yolo_url} while processing {image_path}.\n{hint}"
            ) from exc
    response.raise_for_status()
    return response.json()


def measure_one(image_path: Path, yolo_url: str, rates: list[float], timeout: int) -> dict[str, Any]:
    raw_image_bytes = image_path.stat().st_size
    result = call_yolo(yolo_url, image_path, timeout)
    structured = strip_image_payload(result)
    summary = compact_summary(result)

    payloads = {
        "raw_image_bytes": raw_image_bytes,
        "full_yolo_json_bytes": byte_len(result),
        "structured_json_bytes": byte_len(structured),
        "annotated_image_bytes": estimate_annotated_image_bytes(result),
        "summary_bytes": len(summary.encode("utf-8")),
    }
    row: dict[str, Any] = {
        "image": str(image_path),
        "detections_count": len(result.get("detections") or []),
        "summary": summary,
        **payloads,
    }
    for name, size in payloads.items():
        for rate in rates:
            row[f"{name}_tx_s_at_{rate:g}_kbps"] = round(transfer_seconds(size, rate), 6)
    if payloads["structured_json_bytes"]:
        row["raw_to_structured_ratio"] = round(raw_image_bytes / payloads["structured_json_bytes"], 6)
    if payloads["summary_bytes"]:
        row["raw_to_summary_ratio"] = round(raw_image_bytes / payloads["summary_bytes"], 6)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect result-first downlink payload metrics.")
    parser.add_argument("--images", default="dataset/sample_100_mix/*.jpg", help="Glob of images to test.")
    parser.add_argument("--yolo-url", default="http://127.0.0.1:8003/v1/detect")
    parser.add_argument("--output", default="experiments/downlink_payload/results/downlink_metrics.csv")
    parser.add_argument("--rates-kbps", default=",".join(str(x) for x in DEFAULT_RATES_KBPS))
    parser.add_argument("--max-images", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    rates = [float(x.strip()) for x in args.rates_kbps.split(",") if x.strip()]
    images = sorted(Path(".").glob(args.images))[: args.max_images]
    if not images:
        raise SystemExit(f"No images matched: {args.images}")

    rows = [measure_one(path, args.yolo_url, rates, args.timeout) for path in images]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
