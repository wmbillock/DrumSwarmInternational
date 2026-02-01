/**
 * Typed v1 API client with AbortController cancellation support.
 * Coexists with the existing api.ts — use this for all /api/v1/ endpoints.
 */

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
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
  corps_type?: "competing" | "system";
}

export interface V1ShowInfo {
  show_id: string;
  title: string;
  status: string;
  description?: string;
}

export interface V1CorpsDetail extends V1Corps {
  roster_size: number;
  history_count: number;
  history: V1Placement[];
  mascot?: string;
  theme_id?: string;
  mode?: string;
  rehearsal_mode?: string;
  current_show?: V1ShowInfo | null;
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
  summary?: string;
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
  display_name?: string;
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

export const listCorps = (signal?: AbortSignal, includeSystem = false) =>
  request<V1Corps[]>(`/api/v1/corps${includeSystem ? "?include_system=true" : ""}`, { signal });

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

export const generateSummary = (slug: string) =>
  request<{ summary: string }>(`/api/v1/design/threads/${slug}/generate-summary`, { method: "POST" });

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
  request<CorpsCommandResult>(`/api/v1/corps/${corpsId}/command`, { method: "POST", body: JSON.stringify({ command }) });

export interface CorpsCommands {
  [key: string]: { label: string; description: string; category: string };
}

export const listCorpsCommands = (signal?: AbortSignal) =>
  request<CorpsCommands>("/api/v1/corps-commands", { signal });

// --- Seasons ---

export interface V1Season {
  season_id: string;
  name?: string;
  dir_name: string;
  metadata: Record<string, unknown>;
}

export const listSeasons = (signal?: AbortSignal) =>
  request<V1Season[]>("/api/v1/seasons", { signal });

export const createSeason = (name: string) =>
  request<V1Season>("/api/v1/seasons", { method: "POST", body: JSON.stringify({ name }) });

export const getSeason = (id: string, signal?: AbortSignal) =>
  request<V1Season & { registered_corps?: string[] }>(`/api/v1/seasons/${id}`, { signal });

export const registerSeasonCorps = (seasonId: string, corpsId: string) =>
  request<{ status: string }>(`/api/v1/seasons/${seasonId}/corps`, { method: "POST", body: JSON.stringify({ corps_id: corpsId }) });

// --- Messaging ---

export interface MessagingThreadMessage {
  message_id: string;
  sender_type: string;
  sender_role: string;
  sender_name: string;
  body: string;
  created_at: string;
}

export interface MessagingThread {
  thread_id: string;
  originator_role: string;
  subject: string;
  status: "pending" | "completed" | "archived";
  created_at: string;
  updated_at: string;
  completed_at?: string;
  completed_by?: string;
  messages: MessagingThreadMessage[];
}

export interface ArchivedThreadSummary {
  archived_thread_id: string;
  original_thread_id: string;
  originator_role: string;
  subject: string;
  summary: string;
  message_count: number;
  created_at: string;
  archived_at: string;
  tags?: string[];
  decision?: string;
}

export interface CreateThreadRequest {
  originator_role: string;
  subject: string;
  initial_message_body: string;
  initial_sender_name?: string;
  user_role: string;
}

export const createMessagingThread = (req: CreateThreadRequest) =>
  request<MessagingThread>("/api/v1/messaging/threads", {
    method: "POST",
    body: JSON.stringify(req),
  });

export const listMessagingThreads = (
  status?: string,
  originatorRole?: string,
  limit: number = 50,
  offset: number = 0,
  signal?: AbortSignal
) => {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (originatorRole) params.append("originator_role", originatorRole);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());
  return request<{ threads: MessagingThread[]; total: number }>(
    `/api/v1/messaging/threads?${params}`,
    { signal }
  );
};

export const getMessagingThread = (threadId: string, signal?: AbortSignal) =>
  request<MessagingThread>(`/api/v1/messaging/threads/${threadId}`, { signal });

export const addMessageToThread = (
  threadId: string,
  senderRole: string,
  senderName: string,
  body: string,
  senderType: string = "user"
) =>
  request<MessagingThreadMessage>(`/api/v1/messaging/threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      sender_type: senderType,
      sender_role: senderRole,
      sender_name: senderName,
      body,
    }),
  });

export const markThreadComplete = (
  threadId: string,
  userRole: string,
  userId: string = "current-user"
) =>
  request<MessagingThread>(`/api/v1/messaging/threads/${threadId}`, {
    method: "PATCH",
    body: JSON.stringify({
      completed_by_user_id: userId,
      completed_by_user_role: userRole,
    }),
  });

export const searchArchive = (
  query?: string,
  originatorRole?: string,
  limit: number = 50,
  offset: number = 0,
  signal?: AbortSignal
) => {
  const params = new URLSearchParams();
  if (query) params.append("search", query);
  if (originatorRole) params.append("originator_role", originatorRole);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());
  return request<{ archived_threads: ArchivedThreadSummary[]; total: number }>(
    `/api/v1/messaging/archive?${params}`,
    { signal }
  );
};

export const getArchivedThread = (archivedThreadId: string, signal?: AbortSignal) =>
  request<ArchivedThreadSummary>(`/api/v1/messaging/archive/${archivedThreadId}`, {
    signal,
  });

export const bulkArchiveThreads = (
  threadIds: string[],
  userRole: string,
  userId: string = "current-user"
) =>
  request<{ operation_id: string; count_archived: number; archived_threads: Array<{ archived_thread_id: string; original_thread_id: string; subject: string; summary: string }> }>(
    "/api/v1/messaging/archive/bulk-archive",
    {
      method: "POST",
      body: JSON.stringify({
        thread_ids: threadIds,
        archived_by_user_id: userId,
        archived_by_user_role: userRole,
      }),
    }
  );

export const getUnreadMessageCount = (signal?: AbortSignal) =>
  request<{ unread_count: number }>("/api/v1/messaging/unread-count", { signal });

// --- Admin ---

export interface CleanupResult {
  timed_out_sessions: number;
  disbanded_corps: number;
}

export const adminCleanup = () =>
  request<CleanupResult>("/api/v1/admin/cleanup", { method: "POST" });

// --- Staff Marketplace ---

export interface StaffMember {
  id: string;
  name: string;
  role_type: string;
  trust_score: number;
  total_sessions: number;
  successful_sessions: number;
  failed_sessions: number;
  status: string;
  age: number;
  experience_seasons: number;
  specialties?: string;
}

export const listMarketplace = (signal?: AbortSignal) =>
  request<StaffMember[]>("/api/v1/staff/marketplace", { signal });

export const getStaffProfile = (performerId: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/staff/${performerId}/profile`, { signal });

export const getCorpsStaff = (corpsId: string, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/corps/${corpsId}/staff`, { signal });

export const hireStaff = (corpsId: string, performerId: string, role: string) =>
  request<any>(`/api/v1/corps/${corpsId}/staff/hire`, {
    method: "POST",
    body: JSON.stringify({ performer_id: performerId, role }),
  });

export const releaseStaff = (corpsId: string, performerId: string) =>
  request<any>(`/api/v1/corps/${corpsId}/staff/release`, {
    method: "POST",
    body: JSON.stringify({ performer_id: performerId }),
  });

// --- Metrics & Scoreboards ---

export interface CorpsScore {
  rank: number;
  corps_id: string;
  corps_name: string;
  corps_status: string;
  composite_score: number;
  completion_score: number;
  throughput_score: number;
  efficiency_score: number;
  error_penalty_score: number;
  total_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  total_reps: number;
  completed_reps: number;
  failed_reps: number;
  period_days: number;
}

export interface AgentLeaderEntry {
  rank: number;
  role: string;
  nickname: string;
  corps_id: string;
  total_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  success_rate: number;
  period_days: number;
}

export interface RoleBottleneck {
  role: string;
  session_count: number;
  p50_duration_s: number;
  p95_duration_s: number;
  max_duration_s: number;
  mean_duration_s: number;
}

export interface MetricTrend {
  metric_type: string;
  period_days: number;
  avg_value: number | null;
  prev_period_avg: number | null;
  rate_of_change: number | null;
  direction: string;
  corps_id: string | null;
}

export const getCorpsScoreboard = (periodDays = 7, signal?: AbortSignal) =>
  request<{ period_days: number; generated_at: string; scoreboard: CorpsScore[] }>(
    `/api/v1/metrics/scoreboard/corps?period_days=${periodDays}`,
    { signal },
  );

export const getAgentLeaderboard = (corpsId?: string, periodDays = 7, signal?: AbortSignal) => {
  const params = new URLSearchParams({ period_days: String(periodDays) });
  if (corpsId) params.set("corps_id", corpsId);
  return request<{ leaderboard: AgentLeaderEntry[] }>(`/api/v1/metrics/scoreboard/agents?${params}`, { signal });
};

export const getBottlenecks = (corpsId?: string, periodDays = 7, signal?: AbortSignal) => {
  const params = new URLSearchParams({ period_days: String(periodDays) });
  if (corpsId) params.set("corps_id", corpsId);
  return request<{ role_bottlenecks: RoleBottleneck[]; latency_bottlenecks: any[] }>(
    `/api/v1/metrics/bottlenecks?${params}`,
    { signal },
  );
};

export const getMetricsTrends = (metricType?: string, corpsId?: string, periodDays = 7, signal?: AbortSignal) => {
  const params = new URLSearchParams({ period_days: String(periodDays) });
  if (metricType) params.set("metric_type", metricType);
  if (corpsId) params.set("corps_id", corpsId);
  return request<{ trends: MetricTrend[] }>(`/api/v1/metrics/trends?${params}`, { signal });
};

// --- Asynchronous Messaging System ---

export interface MessageThread {
  id: string;
  corps_id?: string;
  initiator_agent_id?: string;
  originator_role: string;
  subject: string;
  status: "pending" | "completed";
  created_at: string;
  updated_at: string;
  viewed_at?: string;
  completed_at?: string;
  completed_by?: string;
  message_count: number;
}

export interface ThreadMessage {
  id: string;
  sender_type: "user" | "agent";
  sender_role: string;
  sender_name: string;
  body: string;
  created_at: string;
}

export interface ThreadDetail extends MessageThread {
  messages: ThreadMessage[];
}

export interface ArchivedThread {
  id: string;
  original_thread_id: string;
  originator_role: string;
  subject: string;
  summary: string;
  message_count: number;
  created_at: string;
  archived_at: string;
  tags: string[];
  decision?: string;
}

export interface ThreadCreateRequest {
  corps_id?: string;
  initiator_agent_id?: string;
  originator_role: string;
  subject: string;
  initial_message_body: string;
  sender_name: string;
}

export interface MessageAddRequest {
  sender_type: "user" | "agent";
  sender_role: string;
  sender_name: string;
  body: string;
}

// --- System & Overview ---

export const getSystemHealth = (signal?: AbortSignal) =>
  request<any>("/api/v1/system/health", { signal });

export const getAgentsOverview = (signal?: AbortSignal) =>
  request<any[]>("/api/v1/system/agents", { signal });

export const getGlobalWorkLog = (limit = 100, eventType?: string, signal?: AbortSignal) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (eventType) params.set("event_type", eventType);
  return request<any[]>(`/api/v1/system/work-log?${params}`, { signal });
};

// --- Corps Operations ---

export const getCorpsWorkLog = (corpsId: string, limit = 100, eventType?: string, signal?: AbortSignal) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (eventType) params.set("event_type", eventType);
  return request<any[]>(`/api/v1/corps/${corpsId}/work-log?${params}`, { signal });
};

export const getCorpsRoster = (corpsId: string, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/corps/${corpsId}/roster`, { signal });

export const switchCorpsMode = (corpsId: string, mode: string) =>
  request<{ corps_id: string; mode: string }>(`/api/v1/corps/${corpsId}/mode`, {
    method: "PUT",
    body: JSON.stringify({ mode }),
  });

export const getCorpsChatHistory = (corpsId: string, limit = 100, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/corps/${corpsId}/chat?limit=${limit}`, { signal });

export const getCorpsScoresheet = (corpsId: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/corps/${corpsId}/scoresheet`, { signal });

// --- Shows (DB-backed) ---

export const listDBShows = (signal?: AbortSignal) =>
  request<{ id: string; title: string; status: string; corps_id: string; description: string }[]>(
    "/api/v1/shows",
    { signal },
  );

// --- Performers ---

export const listPerformers = (status?: string, signal?: AbortSignal) => {
  const params = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<any[]>(`/api/v1/performers${params}`, { signal });
};

export const getPerformer = (id: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/performers/${id}`, { signal });

export const retirePerformer = (id: string) =>
  request<any>(`/api/v1/performers/${id}/retire`, { method: "POST" });

export const getPerformerLedger = (id: string, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/performers/${id}/ledger`, { signal });

export const getPerformerStats = (id: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/performers/${id}/stats`, { signal });

export const getPerformerGenome = (id: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/performers/${id}/genome`, { signal });

// --- Segments ---

export const getSegment = (id: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/segments/${id}`, { signal });

export const getSegmentChildren = (id: string, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/segments/${id}/children`, { signal });

export const getSegmentTree = (id: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/segments/${id}/tree`, { signal });

// --- Corps Chat (send) ---

export const sendCorpsChat = (corpsId: string, content: string, toRole = "executive_director") =>
  request<any>(`/api/v1/corps/${corpsId}/chat`, {
    method: "POST",
    body: JSON.stringify({ content, to_role: toRole }),
  });

// --- Metronome ---

export const metronomeTick = (corpsId: string) =>
  request<any>(`/api/v1/corps/${corpsId}/metronome/tick`, { method: "POST" });

// --- Evolution ---

export const getSelectionEvents = (performerId?: string, limit = 50, signal?: AbortSignal) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (performerId) params.set("performer_id", performerId);
  return request<any[]>(`/api/v1/evolution/selection-events?${params}`, { signal });
};

export const getMutations = (limit = 50, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/evolution/mutations?limit=${limit}`, { signal });

// --- Improvement: Basics, Critique, Banquet ---

export const runBasics = (corpsId: string, caption: string) =>
  request<any>(`/api/v1/corps/${corpsId}/basics/${caption}`, { method: "POST" });

export const getCritique = (repId: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/reps/${repId}/critique`, { signal });

export const getBanquet = (corpsId: string, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/corps/${corpsId}/banquet`, { signal });

// --- Messages: Polling ---

export const pollMessages = (corpsId: string, since?: string, signal?: AbortSignal) => {
  const params = since ? `?since=${encodeURIComponent(since)}` : "";
  return request<any[]>(`/api/v1/corps/${corpsId}/messages/poll${params}`, { signal });
};

// --- Shows: CRUD ---

export const listShows = (signal?: AbortSignal) =>
  request<any[]>(`/api/v1/shows`, { signal });

export const createShow = (payload: { slug?: string; title: string; description?: string }) =>
  request<any>(`/api/v1/shows`, { method: "POST", body: JSON.stringify(payload) });

export const activateShow = (slug: string) =>
  request<any>(`/api/v1/shows/${slug}/activate`, { method: "POST" });

export const deleteShow = (slug: string) =>
  request<any>(`/api/v1/shows/${slug}`, { method: "DELETE" });

// --- Judging ---

export const listJudgingTapes = (corpsId?: string, limit = 50, signal?: AbortSignal) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (corpsId) params.set("corps_id", corpsId);
  return request<any[]>(`/api/v1/judging/tapes?${params}`, { signal });
};

export const getJudgingTape = (tapeId: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/judging/tapes/${tapeId}`, { signal });

// --- Templates ---

export const listTemplates = (signal?: AbortSignal) =>
  request<any[]>(`/api/v1/templates`, { signal });

export const getTemplate = (templateId: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/templates/${templateId}`, { signal });

export const instantiateTemplate = (templateId: string, payload: { slug?: string; title?: string }) =>
  request<any>(`/api/v1/templates/${templateId}/instantiate`, { method: "POST", body: JSON.stringify(payload) });

// --- Seance ---

export const seanceQuery = (corpsId: string, question: string) =>
  request<any>(`/api/v1/seance/query`, { method: "POST", body: JSON.stringify({ corps_id: corpsId, question }) });

// --- Admin ---

export const adminListCorps = (signal?: AbortSignal) =>
  request<any[]>(`/api/v1/admin/corps`, { signal });

// --- Shows: Additional ---

export const getShowsOverview = (signal?: AbortSignal) =>
  request<any>(`/api/v1/shows-overview`, { signal });

export const getShow = (slug: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/shows/${slug}/detail`, { signal });

export const toggleTour = (slug: string, enable: boolean) =>
  request<any>(`/api/v1/shows/${slug}/tour`, { method: "POST", body: JSON.stringify({ enable }) });

export const completeShow = (slug: string) =>
  request<any>(`/api/v1/shows/${slug}/complete`, { method: "POST" });

// --- Admin: singleton corps ---

export const getAdminCorps = (signal?: AbortSignal) =>
  request<any>(`/api/v1/admin/admin-corps`, { signal });

// --- Judging: Critique actions & export ---

export const getCritiqueActions = (corpsId: string, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/judging/corps/${corpsId}/actions`, { signal });

export const exportJudgeTape = (corpsId: string, repId: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/judging/corps/${corpsId}/tapes/${repId}/export`, { signal });

// --- Evolution: Simulate ---

export const simulateMutation = (definitionId: string, changes: Record<string, unknown>, reason: string) =>
  request<any>(`/api/v1/evolution/simulate-mutation`, {
    method: "POST",
    body: JSON.stringify({ definition_id: definitionId, changes, reason }),
  });

// --- Sessions ---

export const getSessionActivity = (sessionId: string, signal?: AbortSignal) =>
  request<any>(`/api/v1/sessions/${sessionId}/activity`, { signal });

// --- Judges Tapes & Recap ---

export interface V1TapeSummary {
  id: string;
  competition_id: string;
  corps_id: string;
  overall_assessment: string;
  caption_count: number;
  created_at: string;
}

export interface V1TapeDetail {
  id: string;
  competition_id: string;
  corps_id: string;
  caption_feedbacks: Record<string, {
    value: number;
    rep_score: number | null;
    perf_score: number | null;
    feedback: string;
    box: number;
  }>;
  overall_assessment: string;
  created_at: string;
}

export interface V1RecapRow {
  rank: number;
  corps_id: string;
  corps_name: string;
  caption_scores: Record<string, { rep: number; perf: number; tot: number }>;
  penalties_total: number;
  raw_total: number;
  final_score: number;
}

export const listTapes = (competitionId: string, signal?: AbortSignal) =>
  request<V1TapeSummary[]>(`/api/v1/competitions/${competitionId}/tapes`, { signal });

export const getTape = (competitionId: string, corpsId: string, signal?: AbortSignal) =>
  request<V1TapeDetail>(`/api/v1/competitions/${competitionId}/tapes/${corpsId}`, { signal });

export const exportTape = (competitionId: string, corpsId: string) =>
  request<{ markdown: string; corps_id: string }>(`/api/v1/competitions/${competitionId}/tapes/${corpsId}/export`);

export const getRecap = (competitionId: string, format: string = "json", signal?: AbortSignal) =>
  request<V1RecapRow[]>(`/api/v1/competitions/${competitionId}/recap?format=${format}`, { signal });

export const getRecapMarkdown = (competitionId: string) =>
  request<{ markdown: string }>(`/api/v1/competitions/${competitionId}/recap?format=markdown`);

// --- Critique Sessions ---

export interface V1CritiqueSession {
  id: string;
  competition_id: string;
  corps_id: string;
  judge_type: string;
  staff_role: string;
  status: string;
  conversation: Array<{ role: string; content: string }>;
  action_items: string;
  created_at: string;
  is_automated?: boolean;
}

export const startCritique = (competitionId: string, corpsId: string, judgeType: string) =>
  request<V1CritiqueSession>(`/api/v1/competitions/${competitionId}/critique`, {
    method: "POST",
    body: JSON.stringify({ corps_id: corpsId, judge_type: judgeType }),
  });

export const getCritiqueSession = (sessionId: string, signal?: AbortSignal) =>
  request<V1CritiqueSession>(`/api/v1/critique/${sessionId}`, { signal });

export const sendCritiqueMessage = (sessionId: string, message: string) =>
  request<V1CritiqueSession>(`/api/v1/critique/${sessionId}/message`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });

export const completeCritique = (sessionId: string) =>
  request<V1CritiqueSession>(`/api/v1/critique/${sessionId}/complete`, {
    method: "POST",
  });

export const getAdaptationHistory = (corpsId: string, signal?: AbortSignal) =>
  request<any[]>(`/api/v1/corps/${corpsId}/adaptation-history`, { signal });

// --- Ad-hoc Corps Feedback ---

export const sendCorpsFeedback = (corpsId: string, feedback: string) =>
  request<{ status: string; session_id: string }>(`/api/v1/corps/${corpsId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ feedback }),
  });

export const startEDChat = (corpsId: string) =>
  request<V1CritiqueSession>(`/api/v1/corps/${corpsId}/ed-chat`, {
    method: "POST",
  });

