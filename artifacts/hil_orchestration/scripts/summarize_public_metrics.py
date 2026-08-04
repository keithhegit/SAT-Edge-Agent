"""Recalculate HIL orchestration statistics from sanitized request-level CSV files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


SCENARIOS = ("single", "batch_serial_2")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def numbers(rows: list[dict[str, str]], field: str, scale: float = 1.0) -> list[float]:
    return [float(row[field]) / scale for row in rows]


def nearest_rank(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = max(1, math.ceil(quantile * len(ordered))) - 1
    return ordered[index]


def describe(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "sample_sd": statistics.stdev(values),
        "median": statistics.median(values),
        "empirical_p95_nearest_rank": nearest_rank(values, 0.95),
        "minimum": min(values),
        "maximum": max(values),
    }


def summarize_fixed_runs(rows: list[dict[str, str]]) -> dict[str, object]:
    output = {}
    for scenario in SCENARIOS:
        selected = [row for row in rows if row["scenario"] == scenario]
        completed = [row for row in selected if row["completion_status"] == "completed"]
        full_ms = numbers(completed, "full_agent_latency_ms")
        detector_ms = numbers(completed, "yolo_tool_latency_ms")
        output[scenario] = {
            "attempts": len(selected),
            "completed_attempts": len(completed),
            "target_counts": sorted({int(row["target_count"]) for row in completed}),
            "full_agent_seconds": describe([value / 1000.0 for value in full_ms]),
            "yolo_tool_milliseconds": describe(detector_ms),
            "detector_share_of_mean_full_agent_percent": (
                100.0 * statistics.fmean(detector_ms) / statistics.fmean(full_ms)
            ),
            "mean_cpu_sampled_percent": statistics.fmean(
                numbers(completed, "cpu_mean_sampled_percent")
            ),
            "maximum_cpu_peak_sampled_percent": max(
                numbers(completed, "cpu_peak_sampled_percent")
            ),
            "mean_npu_load_field_percent": statistics.fmean(
                numbers(completed, "npu_mean_load_field_percent")
            ),
            "peak_npu_frequency_mhz": max(
                numbers(completed, "npu_peak_frequency_hz")
            )
            / 1_000_000.0,
        }
    return output


def summarize_profiler_runs(rows: list[dict[str, str]]) -> dict[str, object]:
    output = {}
    for scenario in SCENARIOS:
        selected = [row for row in rows if row["scenario"] == scenario]
        successful = [
            row for row in selected if row["completion_status"] == "all_images_successful"
        ]
        output[scenario] = {
            "attempts": len(selected),
            "all_images_successful_attempts": len(successful),
            "structured_partial_results": sum(
                row["completion_status"].startswith("partial_result") for row in selected
            ),
            "full_agent_mean_seconds": statistics.fmean(
                numbers(successful, "full_agent_latency_ms", 1000.0)
            ),
            "detector_total_mean_seconds": statistics.fmean(
                numbers(successful, "detector_total_ms", 1000.0)
            ),
            "time_to_first_visible_token_mean_seconds": statistics.fmean(
                numbers(successful, "time_to_first_visible_token_ms", 1000.0)
            ),
            "post_first_token_interval_mean_seconds": statistics.fmean(
                numbers(successful, "post_first_token_interval_ms", 1000.0)
            ),
            "sse_tail_mean_seconds": statistics.fmean(
                numbers(successful, "sse_tail_ms", 1000.0)
            ),
        }
    return output


def markdown_summary(result: dict[str, object]) -> str:
    fixed = result["fixed_workload_runs"]
    profiler = result["visible_response_profiler"]
    lines = [
        "# HIL Orchestration Metric Summary",
        "",
        "## Repeated Fixed Workloads",
        "",
        "| Metric | Single image | Serial two-image |",
        "|---|---:|---:|",
    ]
    single = fixed["single"]
    batch = fixed["batch_serial_2"]
    lines.extend(
        [
            f"| Completed attempts | {single['completed_attempts']}/{single['attempts']} | {batch['completed_attempts']}/{batch['attempts']} |",
            f"| Full-Agent mean (s) | {single['full_agent_seconds']['mean']:.3f} | {batch['full_agent_seconds']['mean']:.3f} |",
            f"| Full-Agent empirical P95 (s) | {single['full_agent_seconds']['empirical_p95_nearest_rank']:.3f} | {batch['full_agent_seconds']['empirical_p95_nearest_rank']:.3f} |",
            f"| YOLO-tool mean (ms) | {single['yolo_tool_milliseconds']['mean']:.3f} | {batch['yolo_tool_milliseconds']['mean']:.3f} |",
            f"| Detector share of mean Full-Agent latency (%) | {single['detector_share_of_mean_full_agent_percent']:.2f} | {batch['detector_share_of_mean_full_agent_percent']:.2f} |",
            f"| Mean sampled CPU (%) | {single['mean_cpu_sampled_percent']:.3f} | {batch['mean_cpu_sampled_percent']:.3f} |",
            f"| Mean sampled NPU-load field (%) | {single['mean_npu_load_field_percent']:.1f} | {batch['mean_npu_load_field_percent']:.1f} |",
        ]
    )
    lines.extend(
        [
            "",
            "## Visible-Response Profiler",
            "",
            "| Metric | Single image | Serial two-image |",
            "|---|---:|---:|",
        ]
    )
    ps = profiler["single"]
    pb = profiler["batch_serial_2"]
    lines.extend(
        [
            f"| All-images-successful attempts | {ps['all_images_successful_attempts']} | {pb['all_images_successful_attempts']} |",
            f"| Structured partial results | {ps['structured_partial_results']} | {pb['structured_partial_results']} |",
            f"| Full-Agent mean (s) | {ps['full_agent_mean_seconds']:.3f} | {pb['full_agent_mean_seconds']:.3f} |",
            f"| Time to first visible token mean (s) | {ps['time_to_first_visible_token_mean_seconds']:.3f} | {pb['time_to_first_visible_token_mean_seconds']:.3f} |",
            f"| Post-first-token interval mean (s) | {ps['post_first_token_interval_mean_seconds']:.3f} | {pb['post_first_token_interval_mean_seconds']:.3f} |",
            f"| SSE tail mean (s) | {ps['sse_tail_mean_seconds']:.3f} | {pb['sse_tail_mean_seconds']:.3f} |",
            f"| Detector-total mean, nested (s) | {ps['detector_total_mean_seconds']:.3f} | {pb['detector_total_mean_seconds']:.3f} |",
            "",
            "The NPU value is a 200-ms sampled devfreq/sysfs load field across the full request window. It is shared by local accelerator consumers and is not detector-only occupancy or calibrated utilization.",
            "",
            "P99 is intentionally omitted because 20 attempts do not support a robust tail estimate.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_manifest(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or path.name == "MANIFEST.sha256"
            or "__pycache__" in relative.parts
            or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(f"{digest}  {relative.as_posix()}")
    (root / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="ascii")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixed-runs",
        type=Path,
        default=root / "data" / "fixed_workload_runs.csv",
    )
    parser.add_argument(
        "--profiler-runs",
        type=Path,
        default=root / "data" / "visible_response_timing.csv",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=root / "results" / "hil_orchestration_summary.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=root / "results" / "hil_orchestration_summary.md",
    )
    args = parser.parse_args()

    result = {
        "measurement_notes": {
            "standard_deviation": "sample SD with n-1 denominator",
            "quantile_method": "nearest-rank empirical P95",
            "npu_field": "200-ms sampled devfreq/sysfs field over the full request; shared accelerator consumers; not detector-only occupancy",
            "power_exclusion": "The separate 2026-07-03 plug-meter pilot is not combined with these 2026-07-13 timings.",
        },
        "fixed_workload_runs": summarize_fixed_runs(read_csv(args.fixed_runs)),
        "visible_response_profiler": summarize_profiler_runs(read_csv(args.profiler_runs)),
    }

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(markdown_summary(result), encoding="utf-8")
    write_manifest(root)


if __name__ == "__main__":
    main()
