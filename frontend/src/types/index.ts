// DCI Swarm TypeScript Types

export interface Show {
  id: string;
  title: string;
  description?: string;
  status: "draft" | "active" | "completed" | "archived";
  corps_id?: string;
  coordinate_root_id?: string;
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
  status: "active" | "completed" | "failed" | "timed_out";
  parent_session_id?: string;
  started_at?: string;
}

export interface Coordinate {
  id: string;
  type: "show" | "movement" | "set" | "coordinate";
  title: string;
  description?: string;
  status: "pending" | "in_progress" | "review" | "completed" | "failed" | "blocked";
  parent_id?: string;
  caption?: string;
}

export interface Rep {
  id: string;
  status: "pending" | "assigned" | "in_progress" | "review" | "completed" | "failed";
  coordinate_id: string;
  assigned_to?: string;
  result?: string;
  error?: string;
}

export interface Score {
  id: string;
  judge_type: "brass" | "percussion" | "guard" | "visual" | "general_effect" | "timing";
  value: number;
  box: number;
  feedback?: string;
}

export interface CompositeScore {
  raw_total: number;
  penalties_total: number;
  final_score: number;
  needs_rework: boolean;
  needs_escalation: boolean;
}

export interface Message {
  id: string;
  type: "handoff" | "escalation" | "flag" | "status" | "directive" | "feedback";
  from_role: string;
  to_role?: string;
  subject: string;
  priority: "critical" | "high" | "normal" | "low";
  acknowledged_at?: string;
}

export interface BasicsResult {
  caption: string;
  definitions_reviewed: number;
  improvements_suggested: number;
  suggestions: string[];
}

export interface CritiqueFeedback {
  judge_type: string;
  score: number;
  strengths: string[];
  weaknesses: string[];
  action_items: string[];
}

export interface CritiqueResult {
  rep_id: string;
  overall_assessment: string;
  needs_rework: boolean;
  feedbacks: CritiqueFeedback[];
}

export interface BanquetReport {
  corps_id: string;
  total_reps: number;
  completed_reps: number;
  failed_reps: number;
  average_score: number;
  top_caption?: string;
  what_worked: string[];
  what_failed: string[];
  improvements: string[];
}

export interface MetronomeResult {
  checked: number;
  reclaimed: number;
  reclaimed_rep_ids: string[];
}

export interface MergeResult {
  checked: number;
  merged: number;
  conflicts: number;
  merged_coordinate_ids: string[];
  conflict_coordinate_ids: string[];
}

export type WebSocketMessage = {
  type: string;
  data: unknown;
};
