# HIL Orchestration Metric Summary

## Repeated Fixed Workloads

| Metric | Single image | Serial two-image |
|---|---:|---:|
| Completed attempts | 20/20 | 20/20 |
| Full-Agent mean (s) | 29.353 | 60.937 |
| Full-Agent empirical P95 (s) | 31.166 | 66.882 |
| YOLO-tool mean (ms) | 861.386 | 1510.920 |
| Detector share of mean Full-Agent latency (%) | 2.93 | 2.48 |
| Mean sampled CPU (%) | 20.761 | 20.482 |
| Mean sampled NPU-load field (%) | 100.0 | 100.0 |

## Visible-Response Profiler

| Metric | Single image | Serial two-image |
|---|---:|---:|
| All-images-successful attempts | 20 | 19 |
| Structured partial results | 0 | 1 |
| Full-Agent mean (s) | 29.713 | 62.362 |
| Time to first visible token mean (s) | 16.184 | 28.785 |
| Post-first-token interval mean (s) | 13.347 | 33.392 |
| SSE tail mean (s) | 0.182 | 0.185 |
| Detector-total mean, nested (s) | 0.857 | 1.506 |

The NPU value is a 200-ms sampled devfreq/sysfs load field across the full request window. It is shared by local accelerator consumers and is not detector-only occupancy or calibrated utilization.

P99 is intentionally omitted because 20 attempts do not support a robust tail estimate.
