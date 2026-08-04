# SAT-Edge-Agent Model and Runtime Card

This document separates the public service contracts from private deployment assets used by the SAT-Edge-Agent studies.

## System Role

SAT-Edge-Agent is evaluated as a HIL orchestration system. The detector and language model are tools inside the workflow, not standalone algorithmic contributions.

## Vision Tool

| Field | Public value |
|---|---|
| Role | Oriented object detection for remote-sensing images |
| Public label | Project-internal YOLO-style OBB service; `YOLO26` is an internal service/model label |
| Endpoint | `POST /v1/detect` |
| Input image size | 1024 |
| Object threshold | 0.25 |
| NMS threshold | 0.45 |
| Geographic mode used by the Agent | `required` |
| Weight availability | Private internal training asset |

The exact weight filename, hash, training configuration, and hardware-specific export details are not included because redistribution authorization has not been completed. The HIL orchestration study does not make detector-accuracy or SOTA claims.

The service response may include class labels, confidence values, OBB polygons, pixel centers, and FAIR1M metadata-backed geographic fields. These fields represent metadata propagation, not a new geolocation algorithm. When associated metadata are unavailable, the system does not synthesize coordinates or perform sensor-model georegistration.

## Local Language Service

| Field | Public value |
|---|---|
| Role | Agent routing support and operator-facing response formation |
| Interface | Local OpenAI-compatible endpoint |
| Deployment | Same COTS ARM-based heterogeneous edge-SoC HIL host class as the Agent workflow |
| Exact model identity | Withheld |
| Exact quantization/runtime identity | Withheld |
| Private generation throughput | Withheld |

The repeated HIL experiment is described through its service interface and measured request behavior. Exact private model and runtime identities are outside the public release boundary.

## Public Evidence

The following artifacts allow readers to inspect the contracts and recalculate the paper metrics without the private weights:

- `artifacts/hil_orchestration/examples/detect_success_redacted.json`
- `artifacts/hil_orchestration/examples/detect_failure_redacted.json`
- `artifacts/hil_orchestration/examples/sse_success_normalized.jsonl`
- `artifacts/hil_orchestration/examples/sse_partial_failure_normalized.jsonl`
- `artifacts/hil_orchestration/data/fixed_workload_runs.csv`
- `artifacts/hil_orchestration/data/visible_response_timing.csv`
- `artifacts/hil_orchestration/scripts/summarize_public_metrics.py`

## Substitute Reproduction Path

Readers may reproduce the workflow with:

1. any compatible OBB detector that implements the documented response fields;
2. any local OpenAI-compatible language endpoint;
3. FAIR1M samples acquired under the original third-party license terms; and
4. the public request-level evidence when hardware execution is not available.

Substitution reproduces the software contract and analysis pipeline, not the exact private model outputs.

## Claim Boundaries

### HIL Orchestration Study

The HIL orchestration study claims edge-Agent integration, observable tool orchestration, structured output, fixed-workload repeated timing, resource telemetry, and an explicit release boundary. It does not claim detector SOTA performance, public weight reproduction, general georegistration, calibrated energy efficiency, or flight validation.

### Downlink Payload Experiment

The downlink payload experiment uses saved structured outputs to evaluate result size and link-rate sensitivity. Its reproducibility path is the released output data and metric script; exact private model weights are not required to recompute those payload results.
