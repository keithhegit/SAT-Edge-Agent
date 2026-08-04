# SAT-Edge-Agent Manuscript Source

This directory contains the public LaTeX source for:

`SAT-Edge-Agent: Hardware-in-the-Loop Edge-Agent Orchestration for Onboard Satellite Intelligence`

## Compile Files

- `main.tex`
- `glyphtounicode.tex`
- `sections/*.tex`
- `figures/fig1_system_overview.png`
- `figures/fig2_hil_workflow.png`
- `figures/fig3_runtime_resource_snapshot.png`

Repository evidence and analysis scripts are kept under `artifacts/` and `experiments/` rather than duplicated in the manuscript source directory.

## Claim Boundary

The manuscript does not claim:

- performance generalization beyond the two fixed workloads;
- robust P99 latency;
- detector mAP, SOTA accuracy, or a new YOLO family;
- independently validated geolocation accuracy;
- calibrated power, energy per request, or spacecraft power qualification;
- timeout, watchdog, or restart fault tolerance;
- radiation, RF, environmental, or flight validation.

The repeated latency/resource evidence and the separate plug-meter pilot must not be combined into energy-per-request estimates.

## Compile

Compile `main.tex` twice with pdfLaTeX:

```bash
pdflatex main.tex
pdflatex main.tex
```

After compilation, inspect the abstract, Figure 3, runtime tables, Appendix A, and the reference sequence.
