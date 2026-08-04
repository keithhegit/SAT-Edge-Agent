import { useRef, useState, useEffect } from "react";

function LoginPage({ onLogin, password }: { onLogin: () => void; password: string }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const submit = () => {
    if (pw === password) { onLogin(); }
    else { setErr("密码错误，请重试"); }
  };
  return (
    <div className="login-page">
      <div className="login-intro">
        <img src="https://pub-c98d5902eedf42f6a9765dfad981fd88.r2.dev/Icon/oglink-device-intro.png" alt="OgLink 介绍" />
      </div>
      <div className="login-box">
        <img src="https://pub-c98d5902eedf42f6a9765dfad981fd88.r2.dev/Icon/oglink.png" alt="logo" className="login-logo" />
        <div className="login-eyebrow">OGLINK · 星上算力平台</div>
        <h2 className="login-title">低轨遥感图片实时推理识别 Agent</h2>
        <div className="login-field">
          <label>访问密码</label>
          <input type="password" value={pw} onChange={e => { setPw(e.target.value); setErr(""); }} onKeyDown={e => e.key === "Enter" && submit()} placeholder="请输入密码" autoFocus />
        </div>
        {err && <div className="error-box">{err}</div>}
        <button className="btn-primary login-btn" onClick={submit}>进入系统</button>
      </div>
    </div>
  );
}
import type { AgentSseEvent, ChatMessage, DetectionRecord, Fair1mSample, Fair1mSplit, MessageRole, ToolResultItemData } from "./types";
import { SUGGESTIONS, FAIR1M_MANIFEST_PATH, DEMO_PASSWORD, inferAgentBaseUrl, createThreadId, createResultDownloadName } from "./config";

type PreviewFile = { id: string; file: File; previewUrl: string };

const SPLIT_LABELS: Record<Fair1mSplit, string> = { all: "全部", train: "训练集", val: "验证集" };
const SAMPLES_PER_PAGE = 20;

type ProgressStatus = "idle" | "uploading" | "detecting" | "reasoning" | "done" | "error";

const PROGRESS_STEPS: { key: ProgressStatus; label: string }[] = [
  { key: "uploading", label: "图片上传" },
  { key: "detecting", label: "目标检测" },
  { key: "reasoning", label: "推理分析" },
  { key: "done", label: "完成" },
];

function ProgressBar({ status }: { status: ProgressStatus }) {
  if (status === "idle") return null;
  const currentIdx = PROGRESS_STEPS.findIndex(s => s.key === status);
  return (
    <div className="progress-bar-row">
      {PROGRESS_STEPS.map((step, idx) => {
        const reached = currentIdx >= idx;
        const active = status === step.key && status !== "done";
        const isError = status === "error";
        return (
          <div key={step.key} className={`progress-step ${reached ? "reached" : ""} ${active ? "active" : ""} ${isError && idx === currentIdx ? "error" : ""}`}>
            {step.label}
          </div>
        );
      })}
    </div>
  );
}
// current round input images shown in preview area
type PreviewImage = { id: string; url: string; label: string; isResult?: boolean };

function uid() { return Math.random().toString(36).slice(2, 11); }
function msg(role: MessageRole, content: string, label: string, meta = ""): ChatMessage {
  return { id: uid(), role, label, meta, content, timestamp: Date.now() };
}
function normPath(p: string) { return "/" + p.replace(/^\/+/, "").replace(/^assets\//, ""); }

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!DEMO_PASSWORD);
  return loggedIn ? <Main /> : <LoginPage password={DEMO_PASSWORD} onLogin={() => setLoggedIn(true)} />;
}

function Main() {
  const [agentBaseUrl, setAgentBaseUrl] = useState(inferAgentBaseUrl);
  const [threadId, setThreadId] = useState(createThreadId);
  const [healthText, setHealthText] = useState("未检测");
  const [fair1mSamples, setFair1mSamples] = useState<Fair1mSample[]>([]);
  const [fair1mSplit, setFair1mSplit] = useState<Fair1mSplit>("all");
  const [selectedFair1mFile, setSelectedFair1mFile] = useState<string>("");
  const [samplePage, setSamplePage] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [uploadFiles, setUploadFiles] = useState<PreviewFile[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [records, setRecords] = useState<DetectionRecord[]>([]);
  const [validationMsg, setValidationMsg] = useState("");
  const [progress, setProgress] = useState<ProgressStatus>("idle");
  // preview area: shows current round inputs, replaced by result images after detection
  const [previewImages, setPreviewImages] = useState<PreviewImage[]>([]);
  // lightbox
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const msgViewRef = useRef<HTMLDivElement>(null);
  const ctrlRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetch(FAIR1M_MANIFEST_PATH)
      .then(r => r.json())
      .then((data: Fair1mSample[]) => { setFair1mSamples(data); if (data.length > 0) setSelectedFair1mFile(data[0].fileName); })
      .catch(() => { /* manifest load failed */ });
  }, []);

  const filteredSamples = fair1mSplit === "all" ? fair1mSamples : fair1mSamples.filter(s => s.split === fair1mSplit);
  const totalPages = Math.max(1, Math.ceil(filteredSamples.length / SAMPLES_PER_PAGE));
  const currentPage = Math.min(samplePage, totalPages - 1);
  const pagedSamples = filteredSamples.slice(currentPage * SAMPLES_PER_PAGE, (currentPage + 1) * SAMPLES_PER_PAGE);
  const selectedSample = fair1mSamples.find(s => s.fileName === selectedFair1mFile) ?? null;

  const scrollToBottom = () => { setTimeout(() => { if (msgViewRef.current) msgViewRef.current.scrollTop = msgViewRef.current.scrollHeight; }, 50); };

  const runHealthCheck = async () => {
    setHealthText("检测中...");
    try {
      const r = await fetch(`${agentBaseUrl}/api/v1/health`, { signal: AbortSignal.timeout(5000) });
      if (!r.ok) { setHealthText(`异常(${r.status})`); return; }
      const d = await r.json() as { status?: string };
      setHealthText(d.status ? `正常(${d.status})` : "正常");
    } catch { setHealthText("不可达"); }
  };

  const applyFiles = (fl: FileList) => {
    const nf: PreviewFile[] = [];
    for (let i = 0; i < fl.length; i++) {
      const f = fl[i];
      if (!f.type.startsWith("image/")) continue;
      nf.push({ id: uid(), file: f, previewUrl: URL.createObjectURL(f) });
    }
    setUploadFiles(prev => [...prev, ...nf].slice(0, 12));
  };

  const removeUpload = (id: string) => {
    setUploadFiles(prev => { const it = prev.find(f => f.id === id); if (it) URL.revokeObjectURL(it.previewUrl); return prev.filter(f => f.id !== id); });
  };

  const appendToken = (text: string) => {
    setMessages(prev => {
      const last = prev[prev.length - 1];
      if (last?.role === "assistant" && !last.meta) return [...prev.slice(0, -1), { ...last, content: last.content + text }];
      return [...prev, msg("assistant", text, "Agent")];
    });
    scrollToBottom();
  };

  const finalizeAssistant = (meta: string) => {
    setMessages(prev => { const last = prev[prev.length - 1]; if (last?.role === "assistant" && !last.meta) return [...prev.slice(0, -1), { ...last, meta }]; return prev; });
    setIsSubmitting(false);
  };

  const handleToolEvent = (data: Record<string, unknown>) => {
    const addRecord = (imageUrl: string, name: string, summary: string, detections_count: unknown, perf_total_ms: unknown, geoData?: { geo_center?: [number, number] | null; geo_status?: string | null; detection_geos?: Array<{ class_name: string; confidence: number; geo_center: [number, number] }> | null }) => {
      const rec: DetectionRecord = { id: uid(), fileName: name, imageUrl, detectionsCount: (detections_count as number) ?? null, perfTotalMs: (perf_total_ms as number) ?? null, summary: summary ?? "", downloadName: createResultDownloadName(name), geoCenter: geoData?.geo_center ?? null, geoStatus: geoData?.geo_status ?? null, detectionGeos: geoData?.detection_geos ?? null };
      setRecords(cur => [rec, ...cur].slice(0, 24));
      setPreviewImages(prev => {
        const existing = prev.find(p => !p.isResult);
        if (existing) return prev.map(p => p.isResult ? p : { ...p, url: imageUrl, label: name, isResult: true });
        return [...prev, { id: uid(), url: imageUrl, label: name, isResult: true }];
      });
      setMessages(prev => {
        const last = prev[prev.length - 1];
        if (last?.role === "assistant") return [...prev.slice(0, -1), { ...last, items: [...(last.items || []), { image_url: imageUrl, image_name: name, summary, detections_count: detections_count as number, perf_total_ms: perf_total_ms as number, geo_center: geoData?.geo_center, geo_status: geoData?.geo_status, detection_geos: geoData?.detection_geos }] }];
        return prev;
      });
    };

    const extractGeo = (d: Record<string, unknown>) => ({
      geo_center: (d.geo_center as [number, number]) ?? null,
      geo_status: (d.geo_status as string) ?? null,
      detection_geos: (d.detection_geos as Array<{ class_name: string; confidence: number; geo_center: [number, number] }>) ?? null,
    });

    if (data.image_url) addRecord(data.image_url as string, (data.name as string) || "result.jpg", data.summary as string, data.detections_count, data.perf_total_ms, extractGeo(data));
    if (Array.isArray(data.items)) {
      (data.items as ToolResultItemData[]).forEach(item => { if (item.image_url) addRecord(item.image_url, item.image_name ?? "result.jpg", item.summary ?? "", item.detections_count, item.perf_total_ms, extractGeo(item as unknown as Record<string, unknown>)); });
    }
  };

  const applySse = (event: AgentSseEvent) => {
    switch (event.event) {
      case "start": setProgress("uploading"); break;
      case "token": appendToken(event.data.text); setProgress("reasoning"); break;
      case "tool": handleToolEvent(event.data as Record<string, unknown>); setProgress("detecting"); break;
      case "done": finalizeAssistant(`完成 · ${event.data.duration_ms} ms`); setProgress("done"); break;
      case "error": setMessages(prev => [...prev, msg("error", event.data.message, "错误")]); finalizeAssistant("出错"); setProgress("error"); break;
    }
  };

  const submitRequest = async () => {
    const hasInput = uploadFiles.length > 0 || selectedSample;
    if (!hasInput) { setValidationMsg("请至少选择一张样片或上传图片。"); return; }
    setValidationMsg("");
    setIsSubmitting(true);
    setRecords([]);
    setProgress("uploading");

    // build preview images for this round
    const roundPreviews: PreviewImage[] = [];
    if (uploadFiles.length > 0) {
      uploadFiles.forEach(f => roundPreviews.push({ id: uid(), url: f.previewUrl, label: f.file.name }));
    } else if (selectedSample) {
      roundPreviews.push({ id: uid(), url: normPath(selectedSample.relativePath), label: selectedSample.fileName });
    }
    setPreviewImages(roundPreviews);

    const imageCount = uploadFiles.length + (uploadFiles.length === 0 && selectedSample ? 1 : 0);
    setMessages(prev => [...prev, msg("user", draft || "请分析这些图片中的目标。", "你", `${imageCount} 张图片`)]);
    setDraft("");
    scrollToBottom();

    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    try {
      const fd = new FormData();
      fd.append("message", draft || "请分析这些图片中的目标。");
      fd.append("thread_id", threadId.trim() || createThreadId());
      for (const f of uploadFiles) fd.append("images", f.file);
      if (uploadFiles.length === 0 && selectedSample) {
        const r = await fetch(normPath(selectedSample.relativePath), { cache: "no-cache" });
        if (r.ok) fd.append("images", await r.blob(), selectedSample.fileName);
      }
      const response = await fetch(`${agentBaseUrl}/api/v1/chat/stream`, { method: "POST", body: fd, signal: ctrl.signal });
      if (!response.ok) throw new Error(`请求失败 (${response.status}): ${await response.text()}`);
      const reader = response.body?.getReader();
      if (!reader) throw new Error("响应体不可读");
      const dec = new TextDecoder();
      let buf = "", evType = "";
      setMessages(prev => [...prev, msg("assistant", "", "Agent")]);
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n"); buf = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("event:")) { evType = line.slice(6).trim(); continue; }
          if (line.startsWith("data:")) { try { applySse({ event: evType, data: JSON.parse(line.slice(5)) } as AgentSseEvent); } catch { /* skip */ } }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") setMessages(prev => [...prev, msg("error", (err as Error).message, "错误")]);
      setIsSubmitting(false);
    }
  };

  const clearConversation = () => {
    setMessages([]);
    setThreadId(createThreadId());
    setRecords([]);
    setPreviewImages([]);
    setUploadFiles([]);
  };

  const downloadRecord = (rec: DetectionRecord) => { const a = document.createElement("a"); a.href = rec.imageUrl; a.download = rec.downloadName; a.click(); };

  return (
    <div className="page">
      {/* Lightbox */}
      {lightboxUrl && (
        <div className="lightbox" onClick={() => setLightboxUrl(null)}>
          <div className="lightbox-card" onClick={e => e.stopPropagation()}>
            <button className="lightbox-close" onClick={() => setLightboxUrl(null)}>×</button>
            <img src={lightboxUrl} alt="preview" className="lightbox-image" />
          </div>
        </div>
      )}

      {/* Header */}
      <header className="header card">
        <div className="header-left">
          <img src="https://pub-c98d5902eedf42f6a9765dfad981fd88.r2.dev/Icon/oglink.png" alt="logo" className="header-logo" />
          <div>
            <div className="header-eyebrow">OGLINK · 星上算力平台</div>
            <h1>低轨遥感图片实时推理识别 Agent</h1>
          </div>
        </div>
        <div className="header-controls">
          <div className="header-field"><span>Agent 地址</span><input value={agentBaseUrl} onChange={e => setAgentBaseUrl(e.target.value)} /></div>
          <div className="header-field"><span>线程 ID</span><input value={threadId} onChange={e => setThreadId(e.target.value)} style={{ width: 190 }} /></div>
          <button className="btn-outline" onClick={() => void runHealthCheck()}>刷新健康</button>
          <span className="header-status">健康：{healthText}</span>
        </div>
      </header>

      {/* Main grid */}
      <div className="main-grid">
        {/* Left: samples */}
        <section className="card left-panel">
          <h2>FAIR1M 样片库（{fair1mSamples.length} 张）</h2>
          <div className="category-row">
            {(["all", "train", "val"] as Fair1mSplit[]).map(k => (
              <button key={k} className={fair1mSplit === k ? "active" : ""} onClick={() => { setFair1mSplit(k); setSamplePage(0); }}>{SPLIT_LABELS[k]}</button>
            ))}
          </div>
          <div className="sample-list">
            {pagedSamples.map(item => (
              <button key={item.fileName} className={`sample-item ${selectedFair1mFile === item.fileName ? "selected" : ""}`} onClick={() => setSelectedFair1mFile(item.fileName)}>
                <img src={normPath(item.relativePath)} alt={item.fileName} />
                <div><strong>{item.fileName}</strong><span>{item.centerLon.toFixed(4)}°E, {item.centerLat.toFixed(4)}°N</span><span>分辨率 {item.resolutionXm}m · {item.split === "train" ? "训练" : "验证"}</span></div>
              </button>
            ))}
          </div>
          <div className="sample-pagination">
            <button disabled={currentPage === 0} onClick={() => setSamplePage(p => p - 1)}>上一页</button>
            <span>{currentPage + 1} / {totalPages}</span>
            <button disabled={currentPage >= totalPages - 1} onClick={() => setSamplePage(p => p + 1)}>下一页</button>
          </div>
        </section>

        {/* Middle: preview + chat */}
        <section className="card middle-panel">
          {/* Preview block */}
          <div className="preview-block">
            <h2>输入预览</h2>
            {previewImages.length > 0 ? (
              <div className="preview-grid">
                {previewImages.map(pi => (
                  <div key={pi.id} className={`preview-tile ${pi.isResult ? "is-result" : ""}`} onClick={() => setLightboxUrl(pi.url)}>
                    <img src={pi.url} alt={pi.label} />
                    {pi.isResult && <span className="result-badge">检测结果</span>}
                  </div>
                ))}
              </div>
            ) : selectedSample ? (
              <div style={{ textAlign: "center" }}>
                <div className="preview-single" onClick={() => setLightboxUrl(normPath(selectedSample.relativePath))}>
                  <img src={normPath(selectedSample.relativePath)} alt={selectedSample.fileName} className="preview-image" />
                </div>
                <div className="preview-geo-info">
                  📍 {selectedSample.centerLon.toFixed(5)}°E, {selectedSample.centerLat.toFixed(5)}°N · 分辨率 {selectedSample.resolutionXm}m
                </div>
              </div>
            ) : (
              <div className="preview-placeholder"><p>请选择样片或上传图片</p></div>
            )}
          </div>

          <div className="panel-divider" />

          {/* Chat block */}
          <div className="chat-block">
            <div className="chat-header">
              <h2>Agent 对话</h2>
              <button className="btn-outline small" onClick={clearConversation}>清空会话</button>
            </div>
            <div className="suggestion-row">
              {SUGGESTIONS.map(s => <button key={s} className="suggestion" onClick={() => setDraft(s)}>{s}</button>)}
            </div>
            <div className="message-viewport" ref={msgViewRef}>
              {messages.map(m => (
                <article key={m.id} className={`message-card role-${m.role}`}>
                  <div className="message-topline"><strong>{m.label}</strong><span>{m.meta}</span></div>
                  <p>{m.content}</p>
                  {m.items && m.items.length > 0 && (
                    <div className="tool-items">
                      {m.items.map((item, i) => (
                        <div key={i} className="tool-item">
                          {item.image_url && <img src={item.image_url} alt={item.image_name ?? ""} onClick={() => setLightboxUrl(item.image_url!)} style={{ cursor: "pointer" }} />}
                          <div><strong>{item.image_name ?? `结果 ${i + 1}`}</strong><span>{item.summary}</span></div>
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </div>
            <div className="composer-area">
              <textarea value={draft} onChange={e => setDraft(e.target.value)} placeholder="输入问题或指令..." />
              {validationMsg && <div className="error-box">{validationMsg}</div>}
              {uploadFiles.length > 0 && (
                <div className="upload-chips">
                  {uploadFiles.map(f => (
                    <div key={f.id} className="upload-chip">
                      <img src={f.previewUrl} alt={f.file.name} />
                      <button className="chip-remove" onClick={() => removeUpload(f.id)}>×</button>
                    </div>
                  ))}
                </div>
              )}
              <div className="composer-actions">
                <button className="btn-primary" onClick={() => void submitRequest()} disabled={isSubmitting}>{isSubmitting ? "分析中..." : "发送"}</button>
                <button className="btn-outline" onClick={() => ctrlRef.current?.abort()} disabled={!isSubmitting}>中止</button>
                <button className="btn-outline" onClick={() => fileInputRef.current?.click()}>选择图片</button>
              </div>
              <ProgressBar status={progress} />
              <input ref={fileInputRef} hidden type="file" accept=".jpg,.jpeg,.png,.webp,.bmp" multiple onChange={e => { if (e.target.files) applyFiles(e.target.files); e.target.value = ""; }} />
            </div>
          </div>
        </section>

        {/* Right: records */}
        <section className="card right-panel">
          <h2>检测结果</h2>
          <div className="result-tab-bar"><span className="result-tab active">检测记录</span></div>
          <div className="record-list">
            {records.length === 0 ? <p className="muted">工具返回的检测图会沉淀在这里。</p> : records.map(rec => (
              <article key={rec.id} className="record-card">
                <div className="record-thumb" onClick={() => setLightboxUrl(rec.imageUrl)}>
                  <img src={rec.imageUrl} alt={rec.fileName} />
                </div>
                <div className="record-meta">
                  <strong>{rec.fileName}</strong>
                  <span>{rec.summary}</span>
                  <span>目标数 {rec.detectionsCount ?? "无"}{rec.perfTotalMs != null ? ` · ${rec.perfTotalMs} ms` : ""}</span>
                  {rec.geoCenter && (
                    <span className="geo-tag">📍 {rec.geoCenter[0].toFixed(4)}°E, {rec.geoCenter[1].toFixed(4)}°N</span>
                  )}
                  {rec.detectionGeos && rec.detectionGeos.length > 0 && (
                    <details className="geo-details">
                      <summary>目标经纬度（{rec.detectionGeos.length}个）</summary>
                      {rec.detectionGeos.map((g, i) => (
                        <div key={i} className="geo-item">{g.class_name} [{g.geo_center[0].toFixed(5)}, {g.geo_center[1].toFixed(5)}] {(g.confidence * 100).toFixed(1)}%</div>
                      ))}
                    </details>
                  )}
                </div>
                <div className="record-actions">
                  <button className="btn-outline small" onClick={() => setLightboxUrl(rec.imageUrl)}>预览</button>
                  <button className="btn-outline small" onClick={() => downloadRecord(rec)}>下载</button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
