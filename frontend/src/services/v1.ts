/**
 * Typed v1 API client with AbortController cancellation support.
 * Coexists with the existing api.ts — use this for all /api/v1/ endpoints.
 */

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit & { signal?: AbortSignal }): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  return res.json();
}

// --- V1 Response Types ---

export interface V1Corps {
  corps_id: string;
  display_name: string;
  philosophy: string;
  state: string;
}

export interface V1CorpsDetail extends V1Corps {
  roster_size: number;
  history_count: number;
  history: V1Placement[];
}

export interface V1Placement {
  season_id: string;
  placement: number;
  final_score: number;
  notes: string;
}

export interface V1HistoryIndex {
  corps_id: string;
  generated_at: string;
  entries: V1HistoryEntry[];
}

export interface V1HistoryEntry {
  entry_id: string;
  season_id: string;
  show_slug: string | null;
  placement: number;
  final_score: number;
  artifacts: Record<string, string>;
  runs: string[];
}

export interface V1Run {
  run_id: string;
  show_slug: string;
  corps_id: string;
  season_id: string;
  started_at: string;
  completed_at?: string;
  status: "running" | "completed" | "failed";
}

export interface V1RunDetail extends V1Run {
  config: Record<string, unknown>;
  inputs?: Record<string, string>;
  outputs?: string[];
  output: string;
}

export interface V1Thread {
  slug: string;
  status: string;
  has_spec: boolean;
}

export interface V1Messages {
  slug: string;
  messages: { role: string; content: string; tags: string[] }[];
}

export interface V1MessageResp {
  role: string;
  tags: string[];
  response: string;
}

export interface V1Seance {
  seance_id: string;
  corps_id: string;
  entry_id: string;
  season_id: string;
  show_slug: string | null;
  participant: string;
  created_at: string;
  status: "active" | "closed";
  context_binder: { path: string; type: string; loaded: boolean }[];
}

export interface V1Competition {
  competition_id: string;
  season_id: string;
  show_slug: string;
  corps_ids: string[];
  status: string;
}

export interface V1CompResult {
  competition_id: string;
  status: string;
  standings: V1StandingEntry[];
}

export interface V1StandingEntry {
  corps_id: string;
  rank: number;
  final_score: number;
  raw_score: number;
  caption_scores: Record<string, number>;
}

export interface V1Standings {
  competition_id: string;
  season_id: string;
  show_slug: string;
  generated_at: string;
  results: V1StandingEntry[];
}

export interface StartRunReq {
  show_slug: string;
  corps_id: string;
  season_id: string;
}

export interface CreateCompReq {
  season_id: string;
  show_slug: string;
  corps_ids: string[];
}

// --- Corps ---

export const listCorps = (signal?: AbortSignal) =>
  request<V1Corps[]>("/api/v1/corps", { signal });

export const getCorps = (id: string, signal?: AbortSignal) =>
  request<V1CorpsDetail>(`/api/v1/corps/${id}`, { signal });

export const getCorpsHistory = (id: string, signal?: AbortSignal) =>
  request<V1HistoryIndex>(`/api/v1/corps/${id}/history`, { signal });

// --- Runs ---

export const listRuns = (corpsId?: string, signal?: AbortSignal) =>
  request<V1Run[]>(`/api/v1/runs${corpsId ? `?corps_id=${corpsId}` : ""}`, { signal });

export const getRun = (id: string, signal?: AbortSignal) =>
  request<V1RunDetail>(`/api/v1/runs/${id}`, { signal });

export const startRun = (data: StartRunReq, signal?: AbortSignal) =>
  request<{ run_id: string; status: string }>("/api/v1/runs", { method: "POST", body: JSON.stringify(data), signal });

// --- Design ---

export const listThreads = (signal?: AbortSignal) =>
  request<V1Thread[]>("/api/v1/design/threads", { signal });

export const createThread = (title: string) =>
  request<{ slug: string }>("/api/v1/design/threads", { method: "POST", body: JSON.stringify({ title }) });

export const getMessages = (slug: string, signal?: AbortSignal) =>
  request<V1Messages>(`/api/v1/design/threads/${slug}/messages`, { signal });

export const postMessage = (slug: string, message: string) =>
  request<V1MessageResp>(`/api/v1/design/threads/${slug}/messages`, { method: "POST", body: JSON.stringify({ message }) });

export const getBrief = (slug: string, signal?: AbortSignal) =>
  request<{ slug: string; content: string }>(`/api/v1/design/threads/${slug}/artifacts/brief`, { signal });

export const updateBrief = (slug: string, content: string) =>
  request<{ status: string }>(`/api/v1/design/threads/${slug}/artifacts/brief`, { method: "PUT", body: JSON.stringify({ content }) });

export const approveThread = (slug: string) =>
  request<{ version: number }>(`/api/v1/design/threads/${slug}/approve`, { method: "POST" });

// --- Seances ---

export const createSeance = (corpsId: string, entryId: string) =>
  request<V1Seance>("/api/v1/seances", { method: "POST", body: JSON.stringify({ corps_id: corpsId, entry_id: entryId }) });

export const getSeance = (id: string, signal?: AbortSignal) =>
  request<V1Seance>(`/api/v1/seances/${id}`, { signal });

export const postSeanceMessage = (id: string, message: string, mode?: string) =>
  request<{ role: string; message: string; seance_id: string }>(`/api/v1/seances/${id}/messages`, { method: "POST", body: JSON.stringify({ message, mode: mode || "strict" }) });

export const getTranscript = (id: string, signal?: AbortSignal) =>
  request<{ transcript: string }>(`/api/v1/seances/${id}/transcript`, { signal });

// --- Competitions ---

export const listCompetitions = (signal?: AbortSignal) =>
  request<V1Competition[]>("/api/v1/competitions", { signal });

export const createCompetition = (data: CreateCompReq) =>
  request<V1Competition>("/api/v1/competitions", { method: "POST", body: JSON.stringify(data) });

export const runCompetition = (id: string) =>
  request<V1CompResult>(`/api/v1/competitions/${id}/run`, { method: "POST" });

export const getScores = (id: string, signal?: AbortSignal) =>
  request<V1Standings>(`/api/v1/competitions/${id}/scores`, { signal });
