// DCI Swarm TypeScript Types

export interface Show {
  id: string;
  title: string;
  description?: string;
  status: "draft" | "active" | "completed" | "archived";
  corps_id?: string;
  corps_name?: string;
  segment_root_id?: string;
  created_at?: string;
  agents_active?: number;
  reps_total?: number;
  reps_completed?: number;
  reps_failed?: number;
  final_score?: number | null;
}

export interface Corps {
  id: string;
  name: string;
  status: "initializing" | "winter_camps" | "on_tour" | "completed" | "disbanded";
  rehearsal_mode?: "basics" | "sectionals" | "full_ensemble" | "run_through";
  theme_id?: string;
  mascot?: string;
  uniform_concept?: string;
}

export type AgentClassification = "performing_member" | "instructional_staff" | "administrative_staff" | "logistics" | "dci_assigned";

export interface AgentSession {
  id: string;
  role: string;
  nickname?: string;
  model_tier?: string;
  classification?: AgentClassification;
  status: "active" | "completed" | "failed" | "timed_out";
  corps_id?: string;
  parent_session_id?: string;
  started_at?: string;
  ended_at?: string;
}

export interface SegmentNode {
  id: string;
  type: "show" | "movement" | "set" | "segment";
  title: string;
  description?: string;
  status: "pending" | "in_progress" | "review" | "completed" | "failed" | "blocked";
  caption?: string;
  reps: RepInfo[];
  children: SegmentNode[];
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
  nickname?: string;
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

export interface CaptionScore {
  count: number;
  average: number;
  min: number;
  max: number;
  avg_box: number;
  weight: number;
  latest_feedback?: string | null;
}

export interface Scoresheet {
  corps_id: string;
  corps_name: string;
  caption_scores: Record<string, CaptionScore>;
  composite: {
    raw_total: number;
    penalties_total: number;
    final_score: number;
    needs_rework: boolean;
    needs_escalation: boolean;
  };
  penalties: Record<string, { count: number; total: number; reasons: string[] }>;
  execution: {
    reps_total: number;
    reps_completed: number;
    reps_failed: number;
    reps_in_progress: number;
    completion_rate: number;
    failure_rate: number;
    segments_total: number;
  };
  roster: Record<string, { nickname?: string; model_tier: string; status: string; session_id: string }>;
  activity: {
    total_events: number;
    tool_calls: number;
    handoffs: number;
    failures: number;
  };
}

export type WebSocketMessage = {
  type: string;
  data?: unknown;
  [key: string]: unknown;
};
