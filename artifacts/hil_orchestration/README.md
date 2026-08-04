# HIL Orchestration Evidence

This directory contains the sanitized request-level evidence used to support the SAT-Edge-Agent hardware-in-the-loop orchestration study.

The package supports fixed-workload systems claims. It does not support detector-accuracy, flight-validation, calibrated-energy, broad-workload, or robust-tail-latency claims.

## Contents

| Path | Purpose |
|---|---|
| `data/fixed_workload_runs.csv` | Forty repeated runs: 20 single-image and 20 serial two-image attempts. |
| `data/visible_response_timing.csv` | Forty profiler attempts, including one structured partial result. |
| `results/hil_orchestration_summary.json` | Machine-readable derived statistics. |
| `results/hil_orchestration_summary.md` | Reader-facing summary table. |
| `scripts/summarize_public_metrics.py` | Recalculates the reported statistics from the sanitized CSV files. |
| `examples/detect_success_redacted.json` | Redacted service success example. |
| `examples/detect_failure_redacted.json` | Structured invalid-media example. |
| `examples/sse_success_normalized.jsonl` | Normalized success event lifecycle. |
| `examples/sse_partial_failure_normalized.jsonl` | Normalized serial partial-result lifecycle. |
| `runtime_profile.md` | Vendor-agnostic execution and telemetry boundary. |
| `templates/power_trace_template.csv` | Fields required by a future synchronized power study. |
| `MANIFEST.sha256` | SHA-256 hashes for every package file except the manifest itself. |

## Recalculate

From the repository root:

```bash
python artifacts/hil_orchestration/scripts/summarize_public_metrics.py
```

Expected headline values:

| Metric | Single image | Serial two-image |
|---|---:|---:|
| Completed attempts | 20/20 | 20/20 |
| Full-Agent mean | 29.353 s | 60.937 s |
| Full-Agent empirical P95 | 31.166 s | 66.882 s |
| YOLO-tool mean | 861.386 ms | 1510.920 ms |
| Detector share of mean Full-Agent latency | 2.93% | 2.48% |
| Mean sampled CPU | 20.761% | 20.482% |
| Mean sampled NPU-load field | 100.0% | 100.0% |

Sample standard deviation uses the `n-1` denominator. Empirical P95 uses nearest rank. P99 is intentionally omitted because 20 attempts do not support a robust tail estimate.

The NPU value is a devfreq/sysfs load field sampled every 200 ms across the complete request. It is a shared-accelerator software field, not detector-only occupancy, per-service attribution, or calibrated utilization.

## Sanitization Boundary

No latency or resource value was synthesized. The public transformation removes request identifiers, exact timestamps, internal paths, private model and board labels, base64 images, operator-facing generated text, and fields rejected by the internal audit.

The FAIR1M/Kaggle image files are not included. See `dataset/README.md` and `dataset/DATA_LICENSE.md` for acquisition, attribution, and license boundaries.

The exact board model, exact private language-model identity, detector weight, access details, and raw unredacted logs are intentionally withheld. Compatible OBB and OpenAI-style local endpoints may be substituted when reproducing the service contracts.
