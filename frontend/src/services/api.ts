// API client for DCI Swarm backend

import type { Show, AgentSession, SegmentNode, WorkLogEntry, ChatMessage, Scoresheet } from "../types";

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
export const getCorps = (id: string) => request(`/api/corps/${id}`);
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
