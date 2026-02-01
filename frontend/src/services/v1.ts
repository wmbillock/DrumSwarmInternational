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

export interface V1AgentResp {
  role: string;
  display_name: string;
  tags: string[];
  response: string;
}

export interface V1MessageResp {
  role: string;
  tags: string[];
  response: string;
  responses?: V1AgentResp[];
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

export interface CorpsIdentity {
  name: string;
  mascot: string;
  color_scheme: { primary: string; secondary: string; accent: string };
  uniform_concept: string;
  icon_theme: string;
  icon_prompt: string;
}

export interface IconResult {
  source: string;
  description: string;
  image_url: string | null;
}

export interface V1CreatedCorps extends V1Corps {
  mascot?: string;
  color_scheme?: { primary: string; secondary: string; accent: string };
  uniform_concept?: string;
}

export const generateCorpsIdentity = () =>
  request<CorpsIdentity>("/api/v1/corps/generate-identity", { method: "POST" });

export const generateCorpsIcon = (icon_prompt: string) =>
  request<IconResult>("/api/v1/corps/generate-icon", { method: "POST", body: JSON.stringify({ icon_prompt }) });

export const createCorps = (data: {
  name: string;
  mascot?: string;
  color_scheme?: { primary: string; secondary: string; accent: string };
  uniform_concept?: string;
  philosophy?: string;
}) =>
  request<V1CreatedCorps>("/api/v1/corps", { method: "POST", body: JSON.stringify(data) });

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

export const getPrompt = (slug: string, signal?: AbortSignal) =>
  request<{ slug: string; content: string }>(`/api/v1/design/threads/${slug}/artifacts/prompt`, { signal });

export const updatePrompt = (slug: string, content: string) =>
  request<{ status: string }>(`/api/v1/design/threads/${slug}/artifacts/prompt`, { method: "PUT", body: JSON.stringify({ content }) });

export interface V1LintFinding { section: string; message: string; }
export interface V1LintReport { required_fix: V1LintFinding[]; nice_to_have: V1LintFinding[]; acceptable_risk: V1LintFinding[]; }

export const lintPrompt = (slug: string) =>
  request<V1LintReport>(`/api/v1/design/threads/${slug}/lint`, { method: "POST" });

export const publishThread = (slug: string) =>
  request<{ status: string }>(`/api/v1/design/threads/${slug}/publish`, { method: "POST" });

export const listVersions = (slug: string, signal?: AbortSignal) =>
  request<{ versions: number[] }>(`/api/v1/design/threads/${slug}/versions`, { signal });

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

export interface V1CorpsBreakdown {
  corps_id: string;
  caption_scores: Record<string, { score: number; weight: number; weighted: number }>;
  penalties_total: number;
  final_score: number;
  commentary: Record<string, string>;
}

export const getCorpsBreakdown = (competitionId: string, corpsId: string, signal?: AbortSignal) =>
  request<V1CorpsBreakdown>(`/api/v1/competitions/${competitionId}/corps/${corpsId}/breakdown`, { signal });

// --- Artifact Preview ---

export const previewArtifact = (seanceId: string, path: string, signal?: AbortSignal) =>
  request<{ path: string; content: string; truncated: boolean }>(
    `/api/v1/seances/${seanceId}/artifact-preview?path=${encodeURIComponent(path)}`, { signal }
  );

// --- Corps Seances ---

export const listCorpsSeances = (corpsId: string, signal?: AbortSignal) =>
  request<V1Seance[]>(`/api/v1/corps/${corpsId}/seances`, { signal });

// --- Corps Commands ---

export interface CorpsCommandResult {
  command: string;
  corps_id: string;
  status: string;
  detail: string;
}

export const executeCorpsCommand = (corpsId: string, command: string) =>
  request<CorpsCommandResult>(`/api/corps/${corpsId}/command`, { method: "POST", body: JSON.stringify({ command }) });

export interface CorpsCommands {
  [key: string]: { label: string; description: string; category: string };
}

export const listCorpsCommands = (signal?: AbortSignal) =>
  request<CorpsCommands>("/api/corps-commands", { signal });

// --- Seasons ---

export interface V1Season {
  season_id: string;
  dir_name: string;
  metadata: Record<string, unknown>;
}

export const listSeasons = (signal?: AbortSignal) =>
  request<V1Season[]>("/api/v1/seasons", { signal });

export const createSeason = (season_id: string, metadata?: Record<string, unknown>) =>
  request<V1Season>("/api/v1/seasons", { method: "POST", body: JSON.stringify({ season_id, metadata }) });

export const getSeason = (id: string, signal?: AbortSignal) =>
  request<V1Season & { registered_corps?: string[] }>(`/api/v1/seasons/${id}`, { signal });

export const registerSeasonCorps = (seasonId: string, corpsId: string) =>
  request<{ status: string }>(`/api/v1/seasons/${seasonId}/corps`, { method: "POST", body: JSON.stringify({ corps_id: corpsId }) });

// --- Admin ---

export interface CleanupResult {
  timed_out_sessions: number;
  disbanded_corps: number;
}

export const adminCleanup = () =>
  request<CleanupResult>("/api/v1/admin/cleanup", { method: "POST" });
