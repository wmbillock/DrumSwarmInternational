// DCI Swarm TypeScript Types

export interface Show {
  id: string;
  title: string;
  description?: string;
  status: "draft" | "active" | "completed" | "archived";
  corps_id?: string;
  corps_name?: string;
  coordinate_root_id?: string;
  created_at?: string;
  agents_active?: number;
  reps_total?: number;
  reps_completed?: number;
  reps_failed?: number;
}

export interface Corps {
  id: string;
  name: string;
  status: "initializing" | "rehearsal" | "tour" | "completed" | "disbanded";
  tour_mode: boolean;
  rehearsal_mode?: "basics" | "sectionals" | "full_ensemble" | "run_through";
}

export interface AgentSession {
  id: string;
  role: string;
  nickname?: string;
  model_tier?: string;
  status: "active" | "completed" | "failed" | "timed_out";
  corps_id?: string;
  parent_session_id?: string;
  started_at?: string;
  ended_at?: string;
}

export interface CoordinateNode {
  id: string;
  type: "show" | "movement" | "set" | "coordinate";
  title: string;
  description?: string;
  status: "pending" | "in_progress" | "review" | "completed" | "failed" | "blocked";
  caption?: string;
  reps: RepInfo[];
  children: CoordinateNode[];
}

export interface RepInfo {
  id: string;
  status: string;
  result?: string;
  error?: string;
  assigned_to?: string;
}

export interface WorkLogEntry {
  id: string;
  session_id: string;
  corps_id?: string;
  role: string;
  event_type: string;
  phase?: string;
  details?: string;
  timestamp?: string;
}

export interface ChatMessage {
  id: string;
  type: string;
  from_role: string;
  to_role?: string;
  subject: string;
  body?: string;
  priority?: string;
  created_at?: string;
}

export interface WebSocketEvent {
  type: string;
  corps_id?: string;
  session_id?: string;
  role?: string;
  nickname?: string;
  content?: string;
  status?: string;
  from_role?: string;
  to_role?: string;
  error?: string;
  tool?: string;
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
  phase?: string;
  [key: string]: unknown;
}

export type WebSocketMessage = {
  type: string;
  data?: unknown;
  [key: string]: unknown;
};
