// API client for DCI Swarm backend

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

// Shows
export const createShow = (title: string, description?: string) =>
  request("/api/shows", { method: "POST", body: JSON.stringify({ title, description }) });

export const listShows = () => request("/api/shows");

export const getShow = (id: string) => request(`/api/shows/${id}`);

export const activateShow = (id: string) =>
  request(`/api/shows/${id}/activate`, { method: "POST" });

export const completeShow = (id: string) =>
  request(`/api/shows/${id}/complete`, { method: "POST" });

export const toggleTour = (id: string, enable: boolean) =>
  request(`/api/shows/${id}/tour`, { method: "POST", body: JSON.stringify({ enable }) });

// Corps
export const getCorps = (id: string) => request(`/api/corps/${id}`);

export const getRoster = (corpsId: string) => request(`/api/corps/${corpsId}/roster`);

export const setRehearsalMode = (corpsId: string, mode: string) =>
  request(`/api/corps/${corpsId}/rehearsal-mode`, {
    method: "POST", body: JSON.stringify({ mode }),
  });

// Coordinates
export const createCoordinate = (data: {
  type: string; title: string; description?: string; parent_id?: string; caption?: string;
}) => request("/api/coordinates", { method: "POST", body: JSON.stringify(data) });

export const getCoordinate = (id: string) => request(`/api/coordinates/${id}`);

export const getCoordinateChildren = (id: string) =>
  request(`/api/coordinates/${id}/children`);

// Reps
export const createRep = (coordinateId: string) =>
  request("/api/reps", { method: "POST", body: JSON.stringify({ coordinate_id: coordinateId }) });

export const transitionRep = (id: string, data: {
  new_status: string; assigned_to?: string; result?: string; error?: string;
}) => request(`/api/reps/${id}/transition`, { method: "POST", body: JSON.stringify(data) });

export const getRepsForCoordinate = (coordId: string) =>
  request(`/api/coordinates/${coordId}/reps`);

// Scores
export const getScoresForRep = (repId: string) => request(`/api/reps/${repId}/scores`);

export const getComposite = (repId: string) => request(`/api/reps/${repId}/composite`);

// Messages
export const sendMessage = (corpsId: string, data: {
  from_role: string; type: string; subject: string;
  body?: string; to_role?: string; priority?: string;
}) => request(`/api/corps/${corpsId}/messages`, { method: "POST", body: JSON.stringify(data) });

export const pollMessages = (corpsId: string, role?: string) => {
  const params = role ? `?role=${role}` : "";
  return request(`/api/corps/${corpsId}/messages${params}`);
};

// Chat
export const sendChat = (corpsId: string, content: string, toRole: string = "executive_director") =>
  request(`/api/corps/${corpsId}/chat`, {
    method: "POST", body: JSON.stringify({ content, to_role: toRole }),
  });

export const getChatHistory = (corpsId: string) =>
  request(`/api/corps/${corpsId}/chat`);

// Session Activity
export const getSessionActivity = (sessionId: string) =>
  request(`/api/sessions/${sessionId}/activity`);

// Improvement
export const runBasics = (corpsId: string, caption: string) =>
  request(`/api/corps/${corpsId}/basics/${caption}`, { method: "POST" });

export const runCritique = (repId: string, corpsId?: string) =>
  request(`/api/reps/${repId}/critique${corpsId ? `?corps_id=${corpsId}` : ""}`);

export const runBanquet = (corpsId: string) => request(`/api/corps/${corpsId}/banquet`);

// Metronome
export const metronomeTick = (corpsId: string) =>
  request(`/api/corps/${corpsId}/metronome/tick`, { method: "POST" });

// Merge monitor
export const mergeCheck = (corpsId: string) =>
  request(`/api/corps/${corpsId}/merge-check`, { method: "POST" });
