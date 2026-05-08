/**
 * VisionarySTEM API client.
 *
 * Mọi request đi qua Next.js Route Handler proxy `/api/proxy/...` để:
 * - Ẩn backend URL khỏi browser
 * - Tránh CORS issue
 * - Giúp inject auth header sau (Sprint 8.4 multi-tenant)
 */

export const PROXY_BASE = "/api/proxy/api/v1";

// ============ Types ============

export type BlockType = "text" | "math" | "chart" | "table" | "figure";

export interface Coordinates {
  page: number;
  x: number;
  y: number;
  w: number;
  h: number;
  region: string;
}

export interface ContentBlock {
  id: string;
  type: BlockType;
  raw_content: string;
  latex: string | null;
  spoken_text: string;
  language: string;
  confidence: number;
  coordinates: Coordinates;
  // Sprint 4 extensions
  reading_order?: number | null;
  importance?: "primary" | "secondary" | "decorative" | null;
  alt_text_long?: string | null;
  mathml?: string | null;
  parent_id?: string | null;
  aria_role?: string | null;
  // Sprint 8.2 critique
  critique_score?: number | null;
  needs_review?: boolean | null;
  critique_issues?: string[] | null;
  // Sprint 8.3 sonification
  sonification_data?: Record<string, unknown> | null;
}

export interface DocumentMetadata {
  filename: string;
  total_pages: number;
  processing_time_ms: number;
  model_used: string;
}

export interface AnalyzeResult {
  document_id: string;
  document_metadata: DocumentMetadata;
  content_blocks: ContentBlock[];
  spatial_index: { regions: Record<string, string[]> };
}

export interface SpatialQueryResult {
  query: string;
  matched_blocks: ContentBlock[];
  spoken_answer: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  cited_blocks?: string[];
}

export interface ChatResponse {
  reply_text: string;
  suggested_followups: string[];
  cited_blocks: string[];
}

// ============ Health ============

export async function getHealth(): Promise<{
  status: string;
  service: string;
  version: string;
  gemini_model: string;
}> {
  const r = await fetch(`${PROXY_BASE}/health`, { cache: "no-store" });
  if (!r.ok) throw new Error(`Backend health check failed: ${r.status}`);
  return r.json();
}

// ============ Mock + Analyze ============

export async function mockAnalyze(): Promise<AnalyzeResult> {
  const r = await fetch(`${PROXY_BASE}/mock/analyze`, { cache: "no-store" });
  if (!r.ok) throw new Error("Mock analyze failed");
  const data = await r.json();
  return { ...data, document_id: "mock_doc" };
}

export async function analyzeFile(file: File): Promise<AnalyzeResult> {
  const formData = new FormData();
  formData.append("file", file);
  const r = await fetch(`${PROXY_BASE}/analyze`, {
    method: "POST",
    body: formData,
  });
  if (!r.ok) throw new Error(`Analyze failed: ${r.status} ${await r.text()}`);
  const data = await r.json();
  return {
    ...data,
    document_id:
      data.document_id ?? r.headers.get("X-Document-Id") ?? "",
  };
}

// ============ Spatial query ============

export async function spatialQuery(
  query: string,
  document_id?: string,
): Promise<SpatialQueryResult> {
  const r = await fetch(`${PROXY_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, document_id }),
  });
  if (!r.ok) throw new Error(`Query failed: ${r.status}`);
  return r.json();
}

// ============ TTS URLs ============

export function ttsBlockUrl(
  block_id: string,
  document_id?: string,
  rate = "+0%",
  pitch = "+0Hz",
): string {
  const params = new URLSearchParams({ rate, pitch });
  if (document_id) params.set("document_id", document_id);
  return `${PROXY_BASE}/tts/block/${block_id}?${params}`;
}

export function ttsPageUrl(
  page: number,
  document_id?: string,
  rate = "+0%",
  pitch = "+0Hz",
): string {
  const params = new URLSearchParams({ rate, pitch });
  if (document_id) params.set("document_id", document_id);
  return `${PROXY_BASE}/tts/page/${page}?${params}`;
}

export function sonifyBlockUrl(
  block_id: string,
  document_id?: string,
  duration = 3.0,
): string {
  const params = new URLSearchParams({ duration: String(duration) });
  if (document_id) params.set("document_id", document_id);
  return `${PROXY_BASE}/sonify/${block_id}?${params}`;
}

export async function ttsSpeakBlob(
  text: string,
  rate = "+0%",
  pitch = "+0Hz",
): Promise<Blob> {
  const params = new URLSearchParams({ text, rate, pitch });
  const r = await fetch(`${PROXY_BASE}/tts/speak?${params}`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(`TTS speak failed: ${r.status}`);
  return r.blob();
}

/**
 * Gemini TTS V2 — giọng tự nhiên, có cảm xúc.
 * Dùng cho dialog, hỏi-đáp, welcome message — bất cứ chỗ nào cần giọng người.
 *
 * - voice: Aoede | Despina | Charon | Puck | Leda | ... (xem /tts/v2/voices)
 * - mood: auto | warm | calm | empathetic | encouraging | excited | thoughtful | friendly
 *
 * Auto-detect mood theo text nếu mood='auto'.
 */
export async function ttsSpeakV2Blob(
  text: string,
  voice: string = "Aoede",
  mood: string = "auto",
): Promise<Blob> {
  const params = new URLSearchParams({ text, voice, mood });
  const r = await fetch(`${PROXY_BASE}/tts/v2/speak?${params}`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(`Gemini TTS failed: ${r.status}`);
  return r.blob();
}

// ============ Chat (Sprint 8.1) ============

export async function chat(
  document_id: string,
  session_id: string,
  message: string,
): Promise<ChatResponse> {
  const r = await fetch(`${PROXY_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id, session_id, message }),
  });
  if (!r.ok) throw new Error(`Chat failed: ${r.status}`);
  return r.json();
}

// ============ Camera (Sprint 8.4) ============

export async function cameraSnapshot(blob: Blob): Promise<{
  spoken_text: string;
  raw_content: string;
  confidence: number;
  has_math?: boolean;
  has_chart?: boolean;
}> {
  const formData = new FormData();
  formData.append("file", blob, "snapshot.jpg");
  const r = await fetch(`${PROXY_BASE}/camera/snapshot`, {
    method: "POST",
    body: formData,
  });
  if (!r.ok) throw new Error(`Camera analyze failed: ${r.status}`);
  return r.json();
}

// ============ Library + URL upload (Session B) ============

export interface LibraryItem {
  slug: string;
  title: string;
  description: string;
  ordinal: number;
  voice_aliases: string[];
}

export async function listLibrary(): Promise<{ items: LibraryItem[]; count: number }> {
  const r = await fetch(`${PROXY_BASE}/library`, { cache: "no-store" });
  if (!r.ok) throw new Error(`Library list failed: ${r.status}`);
  return r.json();
}

export async function loadFromLibrary(slug: string): Promise<AnalyzeResult> {
  const r = await fetch(`${PROXY_BASE}/library/${slug}/analyze`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(`Library load failed: ${r.status} ${await r.text()}`);
  const data = await r.json();
  return {
    ...data,
    document_id: data.document_id ?? r.headers.get("X-Document-Id") ?? "",
  };
}

export async function analyzeUrl(url: string): Promise<AnalyzeResult> {
  const r = await fetch(`${PROXY_BASE}/analyze-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`URL analyze failed: ${r.status} ${text}`);
  }
  const data = await r.json();
  return {
    ...data,
    document_id: data.document_id ?? r.headers.get("X-Document-Id") ?? "",
  };
}

// ============ General Assistant (no doc) ============

// ============ Export & Sonification (hidden gems) ============

/** Tải EPUB3 file về máy (download Blob). Throws nếu HTTP fail. */
export async function exportEpub3(documentId: string): Promise<Blob> {
  const r = await fetch(`${PROXY_BASE}/export/epub3/${documentId}`);
  if (!r.ok) throw new Error(`Export EPUB failed: ${r.status}`);
  return r.blob();
}

/** Tải Braille text (.txt UTF-8) về máy. */
export async function exportBraille(documentId: string): Promise<Blob> {
  const r = await fetch(`${PROXY_BASE}/export/braille/${documentId}`);
  if (!r.ok) throw new Error(`Export Braille failed: ${r.status}`);
  return r.blob();
}

/** Sonify 1 block (chart/figure) → WAV audio. Trả Blob để Audio() phát inline. */
export async function sonifyBlock(documentId: string, blockId: string): Promise<Blob> {
  const r = await fetch(
    `${PROXY_BASE}/sonify/${blockId}?document_id=${encodeURIComponent(documentId)}`,
  );
  if (!r.ok) throw new Error(`Sonify failed: ${r.status}`);
  return r.blob();
}

/** Trigger browser download cho 1 Blob — no-op nếu trên server. */
export function triggerDownload(blob: Blob, filename: string): void {
  if (typeof document === "undefined") return;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ============ Multi-step Agent (Phase 3) ============

export type AgentEvent =
  | { event: "plan_ready"; data: { plan_overview: string; steps_count: number; steps: Array<{ tool: string; narration: string }> } }
  | { event: "step_start"; data: { index: number; narration: string; tool: string } }
  | { event: "step_done"; data: { index: number; summary: string; result_meta?: any } }
  | { event: "step_error"; data: { index: number; tool: string; error: string } }
  | { event: "plan_done"; data: { summary_narration: string; results: any[] } };

export async function* agentRun(
  request: string,
  signal?: AbortSignal,
): AsyncGenerator<AgentEvent> {
  const r = await fetch(`${PROXY_BASE}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request }),
    signal,
  });
  if (!r.ok || !r.body) {
    const text = await r.text().catch(() => "");
    throw new Error(`Agent run failed: ${r.status} ${text}`);
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    // Parse complete SSE event blocks (separated by \n\n)
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let evName = "message";
      let dataStr = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) evName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }
      if (!dataStr) continue;
      try {
        const data = JSON.parse(dataStr);
        yield { event: evName, data } as AgentEvent;
      } catch {
        // ignore malformed
      }
    }
  }
}

// ============ Web Search Agent (Phase 2) ============

export interface WebSource {
  title: string;
  url: string;
  snippet?: string;
}

export interface WebSearchResult {
  query: string;
  summary: string;
  sources: WebSource[];
  suggested_actions: string[];
  elapsed_ms: number;
}

export async function webSearch(
  query: string,
  maxSources: number = 5,
): Promise<WebSearchResult> {
  const r = await fetch(`${PROXY_BASE}/agent/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, max_sources: maxSources }),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`Web search failed: ${r.status} ${text}`);
  }
  return r.json();
}

export async function generalAssist(
  question: string,
  sessionId?: string,
): Promise<{ reply_text: string }> {
  const r = await fetch(`${PROXY_BASE}/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!r.ok) throw new Error(`Assist failed: ${r.status}`);
  return r.json();
}

// ============ QA (Sprint 6.4) — single-shot Q&A ============

export async function docQA(
  document_id: string,
  question: string,
): Promise<{ answer: string; cited_blocks: string[]; confidence: number }> {
  const r = await fetch(`${PROXY_BASE}/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id, question }),
  });
  if (!r.ok) throw new Error(`QA failed: ${r.status}`);
  return r.json();
}

// ============ Export (Sprint 6.1, 6.2) ============

export function epub3DownloadUrl(document_id: string): string {
  return `${PROXY_BASE}/export/epub3/${document_id}`;
}

export function brailleDocumentUrl(document_id: string): string {
  return `${PROXY_BASE}/export/braille/${document_id}`;
}

export async function brailleConvert(input: {
  text?: string;
  latex?: string;
}): Promise<{ input_kind: "text" | "latex"; braille: string; char_count: number }> {
  const r = await fetch(`${PROXY_BASE}/export/braille`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!r.ok) throw new Error(`Braille convert failed: ${r.status}`);
  return r.json();
}
