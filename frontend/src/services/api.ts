// API client for DCI Swarm backend

import type { Show, AgentSession, Corps, CorpsMode, SegmentNode, WorkLogEntry, ChatMessage, Scoresheet, SystemHealth, RunManifest, RunDetail, CorpsWorkspace, CorpsPlacement, ShowSpec, DesignMessage, SpecVersion, JudgeTape, CritiqueDetail, CritiqueActionsResponse, PerformerGenome, SelectionEvent, MutationLog, MutationSimulationResult, HistoryIndex, SeanceSession, SeanceMessageResponse, ArtifactPreview } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(error.detail || resp.statusText);
  }
  return resp.json();
}

// Dashboard
export const getShowsOverview = () => request<Show[]>("/api/shows-overview");
export const getAgentsOverview = () => request<AgentSession[]>("/api/agents-overview");
export const getGlobalWorkLog = (limit = 50) => request<WorkLogEntry[]>(`/api/work-log?limit=${limit}`);

// Shows
export const createShow = (title: string, description?: string) =>
  request<Show>("/api/shows", { method: "POST", body: JSON.stringify({ title, description }) });
export const activateShow = (id: string) =>
  request<Show>(`/api/shows/${id}/activate`, { method: "POST" });
export const deleteShow = (id: string) =>
  request<{ deleted: string }>(`/api/shows/${id}`, { method: "DELETE" });
export const toggleTour = (id: string, enable: boolean) =>
  request(`/api/shows/${id}/tour`, { method: "POST", body: JSON.stringify({ enable }) });

// Shows (legacy compat)
export const listShows = () => request<Show[]>("/api/shows");
export const getShow = (id: string) => request<Show>(`/api/shows/${id}`);

// Admin corps ("the bar")
export const getAdminCorps = () => request<{ id: string; name: string; status: string; roster: AgentSession[] }>("/api/admin-corps");

// Corps
export const getCorps = (id: string) => request<Corps>(`/api/corps/${id}`);
export const getCorpsTheme = (corpsId: string) => request<any>(`/api/corps/${corpsId}/theme`);
export const updateCorpsTheme = (corpsId: string, data: { theme_id?: string; mascot?: string; uniform_concept?: string }) =>
  request<any>(`/api/corps/${corpsId}/theme`, { method: "PUT", body: JSON.stringify(data) });
export const getRoster = (corpsId: string) => request<AgentSession[]>(`/api/corps/${corpsId}/roster`);

// Segment tree
export const getSegmentTree = (coordId: string) =>
  request<SegmentNode>(`/api/segments/${coordId}/tree`);

// Work log
export const getWorkLog = (corpsId: string, limit = 100) =>
  request<WorkLogEntry[]>(`/api/corps/${corpsId}/work-log?limit=${limit}`);

// Chat
export const sendChat = (corpsId: string, content: string, toRole: string = "executive_director") =>
  request(`/api/corps/${corpsId}/chat`, {
    method: "POST", body: JSON.stringify({ content, to_role: toRole }),
  });
export const getChatHistory = (corpsId: string) =>
  request<ChatMessage[]>(`/api/corps/${corpsId}/chat`);

// Chat streaming (SSE)
export const sendChatStream = (
  corpsId: string,
  content: string,
  toRole: string = "executive_director",
  onMessage: (event: { type: string; id?: string; from_role?: string; content?: string }) => void,
  onDone?: () => void,
): AbortController => {
  const controller = new AbortController();
  fetch(`${BASE_URL}/api/corps/${corpsId}/chat-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, to_role: toRole }),
    signal: controller.signal,
  }).then(async resp => {
    if (!resp.ok || !resp.body) {
      onDone?.();
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            onMessage(data);
            if (data.type === "done" || data.type === "timeout") {
              onDone?.();
              return;
            }
          } catch {}
        }
      }
    }
    onDone?.();
  }).catch(() => onDone?.());
  return controller;
};

// Messages
export const pollMessages = (corpsId: string, role?: string) => {
  const params = role ? `?role=${role}` : "";
  return request(`/api/corps/${corpsId}/messages${params}`);
};

// Session activity
export const getSessionActivity = (sessionId: string) =>
  request(`/api/sessions/${sessionId}/activity`);

// Scoresheet
export const getScoresheet = (corpsId: string) =>
  request<Scoresheet>(`/api/corps/${corpsId}/scoresheet`);

// Corps commands
export const getCorpsCommands = () =>
  request<Record<string, { label: string; description: string; category: string }>>("/api/corps-commands");
export const executeCorpsCommand = (corpsId: string, command: string) =>
  request<{ command: string; corps_id: string; status: string; detail: string }>(
    `/api/corps/${corpsId}/command`, { method: "POST", body: JSON.stringify({ command }) }
  );

// Metronome
export const metronomeTick = (corpsId: string) =>
  request(`/api/corps/${corpsId}/metronome/tick`, { method: "POST" });

// Show templates
export const getShowTemplates = () => request<{ templates: string[] }>("/api/show-templates");
export const getShowTemplate = (name: string) => request(`/api/show-templates/${name}`);
export const instantiateTemplate = (name: string) =>
  request("/api/show-templates/instantiate", { method: "POST", body: JSON.stringify({ name }) });

// Performers
export const getPerformers = () => request<any[]>("/api/performers");
export const getPerformer = (id: string) => request<any>(`/api/performers/${id}`);
export const getPerformerLedger = (id: string) => request<any[]>(`/api/performers/${id}/ledger`);
export const getPerformerStats = (id: string) => request<any>(`/api/performers/${id}/stats`);
export const retirePerformer = (id: string) =>
  request(`/api/performers/${id}/retire`, { method: "POST" });

// System health
export const getSystemHealth = () => request<SystemHealth>("/api/system-health");

// Corps mode
export const switchCorpsMode = (corpsId: string, mode: CorpsMode) =>
  request<{ id: string; mode: string }>(`/api/corps/${corpsId}/mode`, {
    method: "POST", body: JSON.stringify({ mode }),
  });

// Seasons
export const createSeason = (name: string, year?: number) =>
  request<{ season_id: string; name: string; year?: number }>("/api/seasons", {
    method: "POST", body: JSON.stringify({ name, year }),
  });

// Metrics
export const getCorpsMetrics = (corpsId: string) => request<any>(`/api/corps/${corpsId}/metrics`);

// Seance
export const querySeance = (query: string, corpsId?: string) =>
  request<any>("/api/seance", { method: "POST", body: JSON.stringify({ query, corps_id: corpsId }) });

// Evaluate
export const evaluateCorps = (corpsId: string) =>
  request<any>(`/api/corps/${corpsId}/evaluate`, { method: "POST" });

// Lifecycle
export const seasonTransition = (corpsId: string) =>
  request<any>(`/api/corps/${corpsId}/season-transition`, { method: "POST" });
export const getAgeouts = (corpsId: string) => request<any[]>(`/api/corps/${corpsId}/ageouts`);
export const getPendingImprovements = () => request<any[]>("/api/self-improvement/pending");
export const approveImprovement = (id: string, approverSessionId: string) =>
  request<any>(`/api/self-improvement/${id}/approve`, {
    method: "POST", body: JSON.stringify({ approver_session_id: approverSessionId }),
  });
export const rejectImprovement = (id: string, approverSessionId: string) =>
  request<any>(`/api/self-improvement/${id}/reject`, {
    method: "POST", body: JSON.stringify({ approver_session_id: approverSessionId }),
  });

// Memory
export const getAgentMemories = (identity: string, memoryType?: string) =>
  request<any[]>(`/api/agents/${encodeURIComponent(identity)}/memories${memoryType ? `?memory_type=${memoryType}` : ""}`);
export const getAgentMemoryStats = (identity: string) =>
  request<any>(`/api/agents/${encodeURIComponent(identity)}/memory-stats`);
export const updateMemory = (id: string, content: string) =>
  request<any>(`/api/memories/${id}`, { method: "PUT", body: JSON.stringify({ content }) });
export const deleteMemory = (id: string) =>
  request<any>(`/api/memories/${id}`, { method: "DELETE" });

// Segments
export const getSegment = (id: string) => request<any>(`/api/segments/${id}`);
export const getSegmentChildren = (parentId: string) =>
  request<any[]>(`/api/segments/${parentId}/children`);

// Banquet (retrospective)
export const runBanquet = (corpsId: string) =>
  request<any>(`/api/corps/${corpsId}/banquet`, { method: "POST" });

// Complete show
export const completeShow = (id: string) =>
  request<any>(`/api/shows/${id}/complete`, { method: "POST" });

// Workspace: Runs & Rehearsals
export const getRuns = () => request<RunManifest[]>("/api/runs");
export const getRunDetail = (runId: string) => request<RunDetail>(`/api/runs/${encodeURIComponent(runId)}`);

// Workspace: Corps
export const getCorpsWorkspaces = () => request<CorpsWorkspace[]>("/api/corps-workspace");
export const getCorpsHistory = (corpsId: string) => request<CorpsPlacement[]>(`/api/corps-workspace/${encodeURIComponent(corpsId)}/history`);

// Design Room
export const createDesignShow = (title: string) =>
  request<{ slug: string; path: string }>("/api/design/shows", {
    method: "POST", body: JSON.stringify({ title }),
  });
export const getDesignSpec = (slug: string) =>
  request<ShowSpec>(`/api/design/shows/${encodeURIComponent(slug)}/spec`);
export const updateDesignSpec = (slug: string, content: string) =>
  request<{ status: string }>(`/api/design/shows/${encodeURIComponent(slug)}/spec`, {
    method: "PUT", body: JSON.stringify({ content }),
  });
export const sendDesignMessage = (slug: string, message: string, roleHint?: string) =>
  request<DesignMessage>(`/api/design/shows/${encodeURIComponent(slug)}/conversation`, {
    method: "POST", body: JSON.stringify({ message, role_hint: roleHint }),
  });
export const approveDesignSpec = (slug: string) =>
  request<SpecVersion>(`/api/design/shows/${encodeURIComponent(slug)}/approve`, { method: "POST" });
export const getDesignVersions = (slug: string) =>
  request<{ versions: number[] }>(`/api/design/shows/${encodeURIComponent(slug)}/versions`);

// Judging & Critique
export const getJudgeTapes = (corpsId: string) =>
  request<JudgeTape[]>(`/api/judging/corps/${corpsId}/tapes`);
export const getJudgeTape = (corpsId: string, repId: string) =>
  request<CritiqueDetail>(`/api/judging/corps/${corpsId}/tapes/${repId}`);
export const getCritiqueActions = (corpsId: string) =>
  request<CritiqueActionsResponse>(`/api/judging/corps/${corpsId}/actions`);
export const exportJudgeTape = (corpsId: string, repId: string) =>
  request<{ markdown: string; rep_id: string; corps_id: string }>(
    `/api/judging/corps/${corpsId}/tapes/${repId}/export`
  );

// Evolution & Talent Pool
export const getPerformerGenome = (performerId: string) =>
  request<PerformerGenome>(`/api/evolution/performers/${performerId}/genome`);
export const getSelectionEvents = (eventType?: string, limit = 50) =>
  request<SelectionEvent[]>(`/api/evolution/events?limit=${limit}${eventType ? `&event_type=${eventType}` : ""}`);
export const getMutations = (status?: string, limit = 50) =>
  request<MutationLog[]>(`/api/evolution/mutations?limit=${limit}${status ? `&status=${status}` : ""}`);
export const simulateMutation = (definitionId: string, changes: Record<string, unknown>, reason: string) =>
  request<MutationSimulationResult>("/api/evolution/simulate-mutation", {
    method: "POST", body: JSON.stringify({ definition_id: definitionId, changes, reason }),
  });

// Corps History & Seance
export const getCorpsHistoryIndex = (corpsId: string) =>
  request<HistoryIndex>(`/api/corps/${encodeURIComponent(corpsId)}/history-index`);
export const createSeance = (corpsId: string, entryId: string) =>
  request<SeanceSession>("/api/seances", {
    method: "POST", body: JSON.stringify({ corps_id: corpsId, entry_id: entryId }),
  });
export const getSeance = (seanceId: string) =>
  request<SeanceSession>(`/api/seances/${encodeURIComponent(seanceId)}`);
export const getSeanceBinder = (seanceId: string) =>
  request<{ seance_id: string; context_binder: SeanceSession["context_binder"] }>(
    `/api/seances/${encodeURIComponent(seanceId)}/binder`
  );
export const getSeanceTranscript = (seanceId: string) =>
  request<{ seance_id: string; transcript: string }>(
    `/api/seances/${encodeURIComponent(seanceId)}/transcript`
  );
export const sendSeanceMessage = (seanceId: string, message: string, mode: "strict" | "relaxed" = "strict") =>
  request<SeanceMessageResponse>(`/api/seances/${encodeURIComponent(seanceId)}/message`, {
    method: "POST", body: JSON.stringify({ message, mode }),
  });
export const previewSeanceArtifact = (seanceId: string, path: string) =>
  request<ArtifactPreview>(
    `/api/seances/${encodeURIComponent(seanceId)}/artifact-preview?path=${encodeURIComponent(path)}`
  );
