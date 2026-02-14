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

export type CorpsMode = "design_room" | "show_mode" | "rehearsal_mode" | "judging" | "offseason_review";

export interface Corps {
  id: string;
  name: string;
  status: "initializing" | "winter_camps" | "on_tour" | "completed" | "disbanded";
  rehearsal_mode?: "basics" | "sectionals" | "full_ensemble" | "run_through";
  mode?: CorpsMode;
  theme_id?: string;
  mascot?: string;
  uniform_concept?: string;
}

export interface SystemHealth {
  active_corps: number;
  total_agents: number;      // unique agent definitions (roles)
  active_agents: number;     // definitions with an active session
  failed_agents: number;     // definitions whose latest session failed
  total_sessions: number;    // total session instances (for diagnostics)
  total_reps: number;
  completed_reps: number;
  failed_reps: number;
  stale_reps: number;
  failure_rate: number;
  corps_summaries: CorpsSummary[];
}

export interface CorpsSummary {
  id: string;
  name: string;
  status: string;
  mode: CorpsMode | null;
  agents_active: number;
  agents_total: number;
  reps_completed: number;
  reps_total: number;
  failures: number;
}

export type AgentClassification = "performing_member" | "instructional_staff" | "administrative_staff" | "logistics" | "dci_assigned";

export interface AgentSession {
  id: string;
  definition_id?: string;
  role: string;
  nickname?: string;
  model_tier?: string;
  classification?: AgentClassification;
  status: "active" | "completed" | "failed" | "timed_out" | "dormant";
  corps_id?: string;
  corps_name?: string;
  parent_session_id?: string;
  started_at?: string;
  ended_at?: string;
  session_count?: number;  // how many instances this agent has had
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

// Types used by sub-components (TheField, TheReps, TheLot, TheMet, TheBanquet)

export interface Segment {
  id: string;
  type: "show" | "movement" | "set" | "segment";
  title: string;
  description?: string;
  status: "pending" | "in_progress" | "review" | "completed" | "failed" | "blocked";
  caption?: string;
  parent_id?: string;
}

export interface Rep {
  id: string;
  segment_id: string;
  status: "pending" | "assigned" | "in_progress" | "review" | "completed" | "failed";
  assigned_to?: string;
  result?: string;
  error?: string;
}

export interface Message {
  id: string;
  type: string;
  from_role: string;
  to_role?: string;
  subject: string;
  body?: string;
  priority?: string;
  acknowledged_at?: string;
  created_at?: string;
}

export interface MetronomeResult {
  checked: number;
  reclaimed: number;
  reclaimed_rep_ids: string[];
}

export interface BanquetReport {
  total_reps: number;
  completed_reps: number;
  failed_reps: number;
  average_score: number;
  top_caption?: string;
  what_worked: string[];
  what_failed: string[];
  improvements: string[];
}

// --- Workspace view models (filesystem-sourced) ---

export interface RunManifest {
  run_id: string;
  show_slug: string;
  corps_id: string;
  season_id: string;
  started_at: string;
  completed_at?: string;
  status: "running" | "completed" | "failed";
  config: { max_iterations?: number; timeout?: number };
  inputs?: Record<string, string>;
  outputs?: string[];
}

export interface RunDetail extends RunManifest {
  output: string;
}

export interface CorpsWorkspace {
  corps_id: string;
  display_name: string;
  philosophy: string;
  state: string;
  history: CorpsPlacement[];
  roster_size: number;
}

export interface CorpsPlacement {
  season_id: string;
  placement: number;
  final_score: number;
  notes: string;
}

// --- Design Room types ---

export interface ShowSpec {
  content: string;
}

export interface DesignMessage {
  role: string;
  tags: string[];
  response: string;
  spec_updates: {
    decisions: string[];
    open_questions: string[];
    constraints: string[];
  };
}

export interface SpecVersion {
  version: number;
  path: string;
}

// --- Judging & Critique types ---

export interface JudgeTape {
  rep_id: string;
  segment_id: string | null;
  segment_title: string | null;
  segment_type: string | null;
  rep_status: string;
  captions: Record<string, { value: number; box: number; feedback: string | null }[]>;
  composite: {
    final_score: number;
    needs_rework: boolean;
    needs_escalation: boolean;
  };
  score_count: number;
}

export interface CritiqueFeedback {
  judge_type: string;
  score_value: number;
  box: number;
  feedback: string;
  strengths: string[];
  weaknesses: string[];
  action_items: string[];
}

export interface CritiqueDetail {
  rep_id: string;
  overall_assessment: string;
  needs_rework: boolean;
  feedbacks: CritiqueFeedback[];
}

export interface CritiqueAction {
  rep_id: string;
  judge_type: string;
  target_role: string;
  score: number;
  weaknesses: string[];
  action_items: string[];
  strengths: string[];
}

export interface CritiqueActionsResponse {
  total_actions: number;
  by_role: Record<string, CritiqueAction[]>;
  actions: CritiqueAction[];
}

// --- Evolution & Talent Pool types ---

export interface PerformerGenome {
  performer_id: string;
  name: string;
  role_type: string;
  status: string;
  age: number;
  experience_seasons: number;
  trust_score: number;
  specialties: string | null;
  performance: {
    total_sessions: number;
    successful_sessions: number;
    failed_sessions: number;
    success_rate: number;
    reps_completed: number;
    reps_failed: number;
    avg_score: number | null;
    gupp_violations: number;
  };
  definition: {
    definition_id: string;
    role: string;
    model_tier: string;
    tools_allowed: string[];
    version: number;
    classification: string | null;
    nickname: string | null;
    system_prompt_length: number;
    corps_id: string | null;
  } | null;
}

export interface SelectionEvent {
  id: string;
  performer_id: string | null;
  performer_name: string | null;
  role_type: string;
  entry_type: string;
  corps_id: string | null;
  session_id: string | null;
  rep_id: string | null;
  score: number | null;
  trust_before: number | null;
  trust_after: number | null;
  details: string | null;
  created_at: string | null;
}

export interface MutationLog {
  id: string;
  definition_id: string;
  role: string;
  nickname: string | null;
  old_version: number;
  new_version: number;
  changes: Record<string, unknown>;
  reason: string;
  status: string;
  approved_by: string | null;
  created_at: string | null;
}

// --- Corps History & Seance types ---

export interface HistoryIndexEntry {
  entry_id: string;
  season_id: string;
  show_slug: string | null;
  placement: number;
  final_score: number;
  artifacts: Record<string, string>;
  runs: string[];
}

export interface HistoryIndex {
  corps_id: string;
  generated_at: string;
  entries: HistoryIndexEntry[];
}

export interface ContextBinderItem {
  path: string;
  type: string;
  loaded: boolean;
}

export interface SeanceSession {
  seance_id: string;
  corps_id: string;
  entry_id: string;
  season_id: string;
  show_slug: string | null;
  participant: string;
  created_at: string;
  status: "active" | "closed";
  context_binder: ContextBinderItem[];
}

export interface SeanceMessageResponse {
  role: string;
  message: string;
  seance_id: string;
}

export interface ArtifactPreview {
  path: string;
  content: string;
  truncated: boolean;
}

export interface MutationSimulationResult {
  definition_id: string;
  role: string;
  current_version: number;
  proposed_version: number;
  reason: string;
  risk_level: string;
  requires_approval: boolean;
  impacts: {
    field: string;
    impact: string;
    description: string;
    risk: string;
    [key: string]: unknown;
  }[];
  sandbox: boolean;
  applied: boolean;
}

// --- Rehearsal Mode Types ---

export interface BasicsResult {
  summary: string;
  caption?: string;
  definitions_reviewed?: number;
  improvements_suggested?: number;
  suggestions?: Array<{
    aspect?: string;
    suggestion?: string;
    [key: string]: unknown;
  }>;
  items: Array<{
    aspect: string;
    status: string;
    detail: string;
  }>;
}

export interface CritiqueResult {
  summary: string;
  overall_assessment?: string;
  needs_rework?: boolean;
  feedbacks: Array<CritiqueFeedback & { score?: number }>;
}

export interface SessionActivity {
  session_id: string;
  role: string;
  status: string;
  iterations?: Array<{ [key: string]: unknown }>;
  tool_calls?: Array<{ [key: string]: unknown }>;
  final_response?: string;
  messages?: Array<{ [key: string]: unknown }>;
  activity: Array<{
    timestamp: string;
    event_type: string;
    detail: string;
  }>;
}

// --- Resource Health types ---

export interface GuardMetrics {
  sync_guard_activations: number;
  async_guard_activations: number;
  total_cascades: number;
  total_children_cascaded: number;
  unhandled_exceptions_caught: number;
}

export interface ProcessStats {
  active_processes: number;
  warn_threshold: number;
  over_threshold: boolean;
  orphans_reaped: number;
  instance_id: string;
  pid_file: string;
}

export interface SessionSaturation {
  active_sessions: number;
  max_concurrent: number;
  utilization_pct: number;
}

export interface ResourceHealth {
  guard_metrics: GuardMetrics;
  process_stats: ProcessStats;
  budget: Record<string, unknown>;
  session_saturation: SessionSaturation;
}

// --- Awards Summary types ---

export interface AwardCategorySummary {
  total: number;
  tiers: Record<string, number>;
  highest_tier: string | null;
}

export interface AwardRecentUnlock {
  name: string;
  category: string;
  tier: string;
  recipient_name: string;
  awarded_at: string | null;
}

export interface AwardTopRecipient {
  name: string;
  count: number;
}

export interface AwardsSummary {
  total_awards: number;
  by_category: Record<string, AwardCategorySummary>;
  by_tier: Record<string, number>;
  recent_unlocks: AwardRecentUnlock[];
  top_recipients: AwardTopRecipient[];
}

// --- LLM Usage types ---

export interface LLMProviderStats {
  requests: number;
  successes: number;
  failures: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_tokens: number;
}

export interface LLMProviderInfo {
  name: string;
  capabilities: {
    supports_images: boolean;
    supports_native_tools: boolean;
    supports_caching: boolean;
  };
  stats: LLMProviderStats;
}

export interface LLMFailoverEvent {
  timestamp: string;
  from_provider: string;
  to_provider: string;
  error_snippet: string;
}

export interface LLMUsageResponse {
  active_provider: string;
  started_at: string | null;
  providers: LLMProviderInfo[];
  failover_events: LLMFailoverEvent[];
  total_requests: number;
  total_failures: number;
}
