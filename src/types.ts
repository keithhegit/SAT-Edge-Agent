export type WorkbenchView = "agent" | "dataset";

export type HealthTone = "idle" | "working" | "success" | "error";

export type MessageRole = "assistant" | "user" | "tool" | "error" | "system";

export type DatasetClassName =
  | "airplane"
  | "ship"
  | "storage_tank"
  | "baseball_diamond"
  | "tennis_court"
  | "basketball_court"
  | "ground_track_field"
  | "harbor"
  | "bridge"
  | "vehicle";

export type DatasetSample = {
  id: string;
  fileName: string;
  relativePath: string;
  labelPath: string;
  primaryClassId: number;
  primaryClassName: DatasetClassName;
  classes: Array<{ classId: number; className: DatasetClassName; count: number }>;
  boxesCount: number;
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  label: string;
  meta: string;
  content: string;
  imageUrl?: string;
  imageUrls?: string[];
  summary?: string;
  attachmentNames?: string[];
  items?: ToolResultItemData[];
  timestamp: number;
};

export type DetectionRecord = {
  id: string;
  fileName: string;
  imageUrl: string;
  detectionsCount: number | null;
  perfTotalMs: number | null;
  summary: string;
  downloadName: string;
  geoCenter: [number, number] | null;
  geoStatus: string | null;
  detectionGeos: Array<{
    class_name: string;
    confidence: number;
    geo_center: [number, number];
  }> | null;
};

export type ActivityItem = {
  id: string;
  title: string;
  detail: string;
  tone: HealthTone;
  timestamp: number;
};

export type RequestMeta = {
  status: string;
  hint: string;
  tone: HealthTone;
};

export type StartEventData = {
  request_id: string;
  thread_id: string;
  timestamp: string;
};

export type TokenEventData = {
  text: string;
};

export type ToolResultItemData = {
  image_path?: string | null;
  image_name?: string | null;
  summary: string;
  result_text?: string | null;
  image_url?: string | null;
  detections_count?: number | null;
  perf_total_ms?: number | null;
  success?: boolean | null;
  geo_center?: [number, number] | null;
  geo_status?: string | null;
  detection_geos?: Array<{
    class_name: string;
    confidence: number;
    geo_center: [number, number];
  }> | null;
};

export type ToolEventData = {
  name: string;
  phase: string;
  summary: string;
  result_text?: string | null;
  image_url?: string | null;
  detections_count?: number | null;
  perf_total_ms?: number | null;
  images_count?: number | null;
  success_count?: number | null;
  failure_count?: number | null;
  detected_images_count?: number | null;
  total_detections_count?: number | null;
  items?: ToolResultItemData[] | null;
  geo_center?: [number, number] | null;
  geo_status?: string | null;
  detection_geos?: Array<{
    class_name: string;
    confidence: number;
    geo_center: [number, number];
  }> | null;
};

export type DoneEventData = {
  request_id: string;
  duration_ms: number;
};

export type ErrorEventData = {
  code: string;
  message: string;
};

export type AgentSseEvent =
  | { event: "start"; data: StartEventData }
  | { event: "token"; data: TokenEventData }
  | { event: "tool"; data: ToolEventData }
  | { event: "done"; data: DoneEventData }
  | { event: "error"; data: ErrorEventData };

export type Fair1mSplit = "all" | "train" | "val";

export type Fair1mSample = {
  fileName: string;
  relativePath: string;
  split: "train" | "val";
  centerLon: number;
  centerLat: number;
  resolutionXm: number;
  resolutionYm: number;
};
