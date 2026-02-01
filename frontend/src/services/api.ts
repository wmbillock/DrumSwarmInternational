// API client for DCI Swarm backend

import type { Show, AgentSession, Corps, CorpsMode, SegmentNode, WorkLogEntry, ChatMessage, Scoresheet, SystemHealth } from "../types";

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
