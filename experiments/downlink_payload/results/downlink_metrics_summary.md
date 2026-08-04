# Downlink Payload Metrics Summary

## 1. Experiment setup

- Repository context: run from the SAT-Edge-Agent repository root
- Script: `experiments/downlink_payload/scripts/collect_downlink_metrics.py`
- Dataset glob: `dataset/sample_100_mix/*.jpg`
- YOLO endpoint: `http://<edge-host>:8003/v1/detect`
- Link-rate sensitivity points (kbps): `9.6, 100, 1000, 10000, 100000`

Commands used:

```bash
python experiments/downlink_payload/scripts/collect_downlink_metrics.py \
  --images "dataset/sample_100_mix/*.jpg" \
  --yolo-url "http://<edge-host>:8003/v1/detect" \
  --output "experiments/downlink_payload/results/downlink_metrics_20.csv" \
  --rates-kbps "9.6,100,1000,10000,100000" \
  --max-images 20 \
  --timeout 60

python experiments/downlink_payload/scripts/collect_downlink_metrics.py \
  --images "dataset/sample_100_mix/*.jpg" \
  --yolo-url "http://<edge-host>:8003/v1/detect" \
  --output "experiments/downlink_payload/results/downlink_metrics_100.csv" \
  --rates-kbps "9.6,100,1000,10000,100000" \
  --max-images 100 \
  --timeout 60
```

Output files:

- `experiments/downlink_payload/results/downlink_metrics_20.csv`
- `experiments/downlink_payload/results/downlink_metrics_100.csv`

## 2. Payload-size summary

| Metric | 20 images | 100 images |
|---|---:|---:|
| raw image mean (bytes) | 343128.90 | 286894.03 |
| full YOLO JSON mean (bytes) | 233273.75 | 196529.22 |
| structured JSON mean (bytes) | 9690.30 | 8359.85 |
| summary mean (bytes) | 100.60 | 100.11 |
| raw/structured mean ratio | 117.409 | 104.518 |
| raw/structured min ratio | 11.190 | 4.510 |
| raw/structured max ratio | 432.769 | 949.811 |
| raw/summary mean ratio | 3387.494 | 2877.896 |
| raw/summary min ratio | 833.289 | 783.451 |
| raw/summary max ratio | 9222.074 | 9222.074 |

## 3. Transfer-time (median, seconds)

### 3.1 20-image run

| Link rate | Raw image | Structured JSON | Summary |
|---|---:|---:|---:|
| 9.6 kbps | 231.974 | 3.221 | 0.088 |
| 100 kbps | 22.270 | 0.309 | 0.008 |
| 1000 kbps | 2.227 | 0.031 | 0.001 |

### 3.2 100-image run

| Link rate | Raw image | Structured JSON | Summary |
|---|---:|---:|---:|
| 9.6 kbps | 205.438 | 2.750 | 0.085 |
| 100 kbps | 19.722 | 0.264 | 0.008 |
| 1000 kbps | 1.972 | 0.026 | 0.001 |

## 4. Evidence-backed interpretation

- For this FAIR1M sample, structured JSON is around `10^2` times smaller than raw imagery on average.
- Summary payload is around `10^3` times smaller than raw imagery on average.
- At low-rate links (e.g., 9.6 kbps, 100 kbps), first-return time for structured/summary payloads is substantially lower than raw image return.
- The 100-image run exceeds `10x` structured reduction and `100x` summary reduction on average, supporting continued evaluation of result-first payload return.

## 5. Scope boundary for writing

Current evidence supports payload-size and transfer-time sensitivity claims.
Do not overclaim full mission scheduling or in-orbit routing-controller validation from this dataset alone.
