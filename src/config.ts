import type { DatasetClassName, WorkbenchView } from "./types";

const DEFAULT_AGENT_PORT = "9001";

export const DEMO_PASSWORD = String(import.meta.env.VITE_DEMO_PASSWORD ?? "");

export const DATASET_MANIFEST_PATH = "/dataset_NWPU_VHR-10/manifest.json";

export const FAIR1M_MANIFEST_PATH = "/sample_100_mix/manifest.json";

export const VIEW_LABELS: Record<WorkbenchView, string> = {
  agent: "Agent 对话",
  dataset: "NWPU 样片检测"
};

export const SUGGESTIONS = [
  "请检测这些遥感图中的旋转目标，并报告经纬度和拍摄地点",
  "请先做目标检测，再给出经纬度定位和简短分析，并告诉我这是什么国家和城市范围",
  "检测这张图片，如存在多个目标，帮我对比这些目标的分布和位置差异。",
];

export const NWPU_CLASS_NAMES: Record<number, DatasetClassName> = {
  0: "airplane",
  1: "ship",
  2: "storage_tank",
  3: "baseball_diamond",
  4: "tennis_court",
  5: "basketball_court",
  6: "ground_track_field",
  7: "harbor",
  8: "bridge",
  9: "vehicle"
};

export const CLASS_LABELS: Record<DatasetClassName | "all", string> = {
  all: "全部",
  airplane: "飞机",
  ship: "船只",
  storage_tank: "储罐",
  baseball_diamond: "棒球场",
  tennis_court: "网球场",
  basketball_court: "篮球场",
  ground_track_field: "田径场",
  harbor: "港口",
  bridge: "桥梁",
  vehicle: "车辆"
};

export function inferAgentBaseUrl(): string {
  if (import.meta.env.VITE_AGENT_BASE_URL) {
    return String(import.meta.env.VITE_AGENT_BASE_URL).replace(/\/+$/, "");
  }
  if (typeof window !== "undefined" && window.location.hostname) {
    return `${window.location.protocol}//${window.location.hostname}:${DEFAULT_AGENT_PORT}`;
  }
  return `http://127.0.0.1:${DEFAULT_AGENT_PORT}`;
}

export function createThreadId(): string {
  const stamp = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  return `nwpu-thread-${stamp}`;
}

export function createResultDownloadName(fileName: string): string {
  const stem = fileName.replace(/\.[^.]+$/, "") || "result";
  return `${stem}-detected.jpg`;
}
