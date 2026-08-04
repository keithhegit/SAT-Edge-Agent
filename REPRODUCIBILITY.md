# SAT-Edge-Agent Reproducibility Guide

This repository supports paper-facing reproduction without disclosing private laboratory infrastructure.

## Public Scope

The public release supports:

- building the React/Vite frontend;
- running the FastAPI Agent backend;
- inspecting the OBB and local-language service contracts;
- recalculating fixed-workload and profiler statistics from sanitized request rows;
- inspecting normalized success and structured partial-failure SSE lifecycles;
- reproducing downlink payload-size and link-rate calculations from saved outputs;
- acquiring and verifying the 100-image FAIR1M-derived sample without redistributing the images.

The public scope does not include private hostnames, IP addresses, VM access details, exact board identity, internal paths, detector weights, exact private language-model identity, or raw unredacted logs.

## Repository State

| Item | Value |
|---|---|
| Repository | `https://github.com/keithhegit/SAT-Edge-Agent` |
| Public host placeholder | `<edge-host>` |

## HIL Orchestration Reproduction

### Artifacts

| Artifact | Path |
|---|---|
| Package guide | `artifacts/hil_orchestration/README.md` |
| Fixed-workload request rows | `artifacts/hil_orchestration/data/fixed_workload_runs.csv` |
| Visible-response profiler rows | `artifacts/hil_orchestration/data/visible_response_timing.csv` |
| Summary JSON/Markdown | `artifacts/hil_orchestration/results/` |
| Recalculation script | `artifacts/hil_orchestration/scripts/summarize_public_metrics.py` |
| Redacted JSON and normalized SSE | `artifacts/hil_orchestration/examples/` |
| Vendor-agnostic runtime profile | `artifacts/hil_orchestration/runtime_profile.md` |
| Integrity hashes | `artifacts/hil_orchestration/MANIFEST.sha256` |
| LaTeX source | `manuscript/` |
| Overleaf-ready ZIP | `SAT-Edge-Agent_Overleaf.zip` |

### Recalculate

```bash
python artifacts/hil_orchestration/scripts/summarize_public_metrics.py
```

The script writes:

- `artifacts/hil_orchestration/results/hil_orchestration_summary.json`
- `artifacts/hil_orchestration/results/hil_orchestration_summary.md`

Statistical conventions:

- sample standard deviation uses `n-1`;
- empirical P95 uses nearest rank;
- P99 is not reported for `n=20`;
- detector time is nested within the Full-Agent request;
- the NPU value is a 200-ms sampled shared devfreq/sysfs field, not detector-only occupancy.

The separate plug-meter pilot is not combined with the repeated timing data to estimate energy per request.

## Downlink Payload Reproduction

This experiment compares communication cost for raw images and structured result payloads.

| Artifact | Path |
|---|---|
| 20-image metrics | `experiments/downlink_payload/results/downlink_metrics_20.csv` |
| 100-image metrics | `experiments/downlink_payload/results/downlink_metrics_100.csv` |
| Summary | `experiments/downlink_payload/results/downlink_metrics_summary.md` |
| Collection script | `experiments/downlink_payload/scripts/collect_downlink_metrics.py` |
| Summary script | `experiments/downlink_payload/results/summarize_metrics.py` |

Run against a compatible detector endpoint:

```bash
python experiments/downlink_payload/scripts/collect_downlink_metrics.py \
  --images "dataset/sample_100_mix/*.jpg" \
  --yolo-url "http://<edge-host>:8003/v1/detect" \
  --output "experiments/downlink_payload/results/downlink_metrics_100.csv" \
  --rates-kbps "9.6,100,1000,10000,100000" \
  --max-images 100 \
  --timeout 60
```

## Data Acquisition

FAIR1M-derived images and metadata are third-party data. Follow:

- `dataset/README.md`
- `dataset/DATA_LICENSE.md`
- `dataset/sample_100_mix_manifest.csv`
- `dataset/sample_100_mix_sha256.csv`

Download the source data from the Kaggle/FAIR1M page and verify the local filenames and SHA-256 values. The project software license does not override the data license.

## Model Substitution

The detector weight and exact local language model remain private. Public reproduction can use:

- a compatible user-provided OBB detector;
- a compatible OpenAI-style local language endpoint;
- the released sanitized JSON, SSE, and CSV evidence.

See `MODEL_CARD.md` for the exact claim boundary.

## Privacy Check Before Release

Public files must not contain:

- private IP addresses or hostnames;
- SSH details, credentials, keys, or tokens;
- Windows usernames or local absolute paths;
- internal VM management details;
- exact vendor-sensitive board or private model labels;
- raw logs containing unrelated internal traffic;
- base64 image payloads from request captures.
