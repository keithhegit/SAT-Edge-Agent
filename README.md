# SAT-Edge-Agent

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-research%20prototype-informational)](#english)

[English](#english) | [中文](#中文)

## 中文

SAT-Edge-Agent 是面向星载边缘智能研究的硬件在环（HIL）系统原型。它将浏览器工作台、FastAPI Agent、遥感有向目标检测工具、本地 OpenAI 兼容语言服务和 SSE 事件流组织为端到端任务工作流。

当前公开内容聚焦两类可复现实验：端侧 Agent 的 HIL 编排，以及结构化结果相对于原始图像的下行 payload 成本。

本文不将检测器精度、通用地理配准、飞行验证或校准能耗作为当前贡献。

## 系统组成

- React + Vite 操作工作台
- 基于 LangChain/LangGraph 组件的 FastAPI Agent 后端
- 项目内部 YOLO-style OBB 检测服务
- 本地 OpenAI 兼容语言模型服务
- `start -> tool -> token -> done` 的 SSE 可观测事件链

```text
Browser / operator client
  -> React frontend (5173)
     -> FastAPI Agent (<edge-host>:9001)
        -> YOLO-style OBB service (<edge-host>:8003)
        -> Local OpenAI-compatible service (<edge-host>:8080/v1)
```

所有公开文档使用 `<edge-host>` 等占位符。私有 IP、主机名、VM 访问方式、内部路径、具体板卡型号和私有模型身份不进入公开材料。

## 研究制品

[HIL orchestration evidence](./artifacts/hil_orchestration/README.md) 包含：

- 20 次单图与 20 次双图串行固定工作负载记录；
- 20 次单图 profiler、19 次完整双图 profiler 和 1 次结构化部分失败记录；
- 脱敏 JSON 与标准化 SSE 示例；
- 可重新计算均值、样本标准差、中位数和 nearest-rank P95 的脚本；
- SHA-256 完整性清单和厂商无关运行环境说明。

运行：

```bash
python artifacts/hil_orchestration/scripts/summarize_public_metrics.py
```

论文 LaTeX 源码位于 [manuscript](./manuscript/)，同时提供[可直接导入 Overleaf 的 ZIP 包](./SAT-Edge-Agent_Overleaf.zip)。

20/100 图 payload-size 与链路速率敏感性结果位于 [experiments/downlink_payload/results](./experiments/downlink_payload/results/)。

## 数据集

实验样本来自第三方 FAIR1M Kaggle 镜像：

https://www.kaggle.com/datasets/ollypowell/fair1m-satellite-imagery-for-object-detection

本仓库不重新分发图像文件，只公开下载说明、100 文件清单和 SHA-256 校验值。详见 [dataset/README.md](./dataset/README.md) 与 [dataset/DATA_LICENSE.md](./dataset/DATA_LICENSE.md)。

## 快速启动

前端：

```bash
npm install
npm run dev
```

Agent 后端：

```bash
cd yolo_agent-main
uv run uvicorn backend.app:app --host 0.0.0.0 --port 9001
```

常用环境变量：

- `VITE_AGENT_BASE_URL`
- `VITE_DEMO_PASSWORD`（可选；留空时不显示演示登录页）
- `NWPU_VHR_API_BASE`
- `ASSISTANT_LLM_API_BASE`

## 复现边界

- 检测权重是内部训练资产，当前不公开。
- 精确板卡型号与私有语言模型身份保留在内部证据中。
- 读者可使用兼容的 OBB 检测接口与 OpenAI 兼容本地语言接口替换私有组件。

核心文档：

- [Reproducibility Guide](./REPRODUCIBILITY.md)
- [Model and Runtime Card](./MODEL_CARD.md)
- [Dataset Notes](./dataset/README.md)

---

## English

SAT-Edge-Agent is a hardware-in-the-loop (HIL) research prototype for onboard edge intelligence. It combines a browser workspace, a FastAPI Agent, an oriented remote-sensing detection tool, a local OpenAI-compatible language service, and an SSE-observable task workflow.

The public research artifacts cover two reproducible evaluations: HIL edge-Agent orchestration and the downlink-payload cost of structured results relative to raw imagery.

The current release does not claim detector accuracy leadership, general georegistration, flight validation, or calibrated energy efficiency.

## Architecture

```text
Browser / operator client
  -> React frontend (5173)
     -> FastAPI Agent (<edge-host>:9001)
        -> YOLO-style OBB service (<edge-host>:8003)
        -> Local OpenAI-compatible service (<edge-host>:8080/v1)
```

Public documentation uses placeholders such as `<edge-host>`. Private IP addresses, hostnames, VM access details, internal paths, exact board identity, and private model identity are excluded.

## Research Artifacts

The [HIL orchestration evidence package](./artifacts/hil_orchestration/README.md) provides sanitized request-level CSV files, normalized success and partial-failure SSE examples, redacted JSON, a recalculation script, a vendor-agnostic runtime profile, and a SHA-256 manifest.

```bash
python artifacts/hil_orchestration/scripts/summarize_public_metrics.py
```

The LaTeX source is available under [manuscript](./manuscript/), together with an [Overleaf-ready ZIP archive](./SAT-Edge-Agent_Overleaf.zip).

The 20-image and 100-image payload-size/link-rate results are available under [experiments/downlink_payload/results](./experiments/downlink_payload/results/).

## Dataset

The experiments use samples acquired from the third-party FAIR1M Kaggle mirror:

https://www.kaggle.com/datasets/ollypowell/fair1m-satellite-imagery-for-object-detection

Image files are not redistributed. The repository includes acquisition notes, a 100-file manifest, and SHA-256 checksums. See [dataset/README.md](./dataset/README.md) and [dataset/DATA_LICENSE.md](./dataset/DATA_LICENSE.md).

## Getting Started

Frontend:

```bash
npm install
npm run dev
```

Agent backend:

```bash
cd yolo_agent-main
uv run uvicorn backend.app:app --host 0.0.0.0 --port 9001
```

Common overrides:

- `VITE_AGENT_BASE_URL`
- `VITE_DEMO_PASSWORD` (optional; leave empty to disable the demo login gate)
- `NWPU_VHR_API_BASE`
- `ASSISTANT_LLM_API_BASE`

## Reproducibility Boundary

- The detector weight is an internal training asset and is not released.
- The exact board and private language-model identities remain in internal evidence.
- Compatible OBB and OpenAI-style local endpoints may replace the private components.

Core documents:

- [Reproducibility Guide](./REPRODUCIBILITY.md)
- [Model and Runtime Card](./MODEL_CARD.md)
- [Dataset Notes](./dataset/README.md)

## License

Project code and evidence-processing scripts are released under the Apache License 2.0. Third-party FAIR1M/Kaggle images, labels, geographic fields, and derived data elements remain governed by the source terms described in [dataset/DATA_LICENSE.md](./dataset/DATA_LICENSE.md).
