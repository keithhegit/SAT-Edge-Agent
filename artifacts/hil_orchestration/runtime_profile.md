# Vendor-Agnostic HIL Runtime Profile

This profile describes the public execution environment at the level needed to interpret the HIL evidence. It is not a space-grade hardware qualification record.

| Item | Public value |
|---|---|
| Operating system | Debian GNU/Linux 11 (bullseye) |
| Kernel and architecture | Linux 6.1.115, aarch64 |
| Hardware class | COTS ARM-based heterogeneous edge-SoC board |
| CPU and memory | 8 Cortex-A55 cores, up to 2304 MHz; 31 GiB memory |
| Python | 3.13.12 |
| Key packages | requests 2.32.5; FastAPI 0.136.1; Uvicorn 0.46.0; Pydantic 2.13.3; NumPy 2.4.4 |
| Agent interface | FastAPI with SSE-visible `start`, `tool`, `token`, and `done` events |
| Detector interface | Project-internal YOLO-style OBB service implementing `POST /v1/detect` |
| Language interface | Local OpenAI-compatible endpoint; exact model identity withheld |
| Dataset mode | FAIR1M-derived fixed samples acquired under the original third-party terms |

## Accelerator Telemetry

CPU counters and an NPU devfreq/sysfs load/frequency field were sampled every 200 ms over each Full-Agent request. The detector and local language service can both use the accelerator. The recorded `100%` NPU-load field is a coarse shared-accelerator state and must not be interpreted as detector-only occupancy or calibrated utilization.

## Model Boundary

The detector weight and exact local language model are private deployment assets. The public release documents their service contracts and provides redacted outputs. The Qwen Instruct 16K supplementary capability benchmark was collected under a different configuration and task boundary and is not used to identify the model in the repeated 2026-07-13 HIL runs.

## Qualification Boundary

This runtime profile supports a ground-based HIL integration claim. It does not establish radiation tolerance, thermal-vacuum performance, RF-in-the-loop behavior, flight-computer certification, or in-orbit operation.
