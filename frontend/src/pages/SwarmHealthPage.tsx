import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  SystemHealth as SystemHealthData,
  WorkLogEntry,
  LLMUsageResponse,
  ResourceHealth,
  AwardsSummary,
} from "../types";
import type { AgentLeaderEntry, CorpsScore, RoleBottleneck, V1Award } from "../services/v1";
import * as v1 from "../services/v1";
import { Badge, DataTable, Panel, Tabs } from "../ui";
import type { Column } from "../ui";
import { formatStatus, formatTimestamp, formatRole, relativeTime } from "../utils/formatters";
import { TrophyShowcase } from "../components/TrophyShowcase";
import "../styles/Metrics.css";

const REFRESH_MS = 30_000;

const TAB_ITEMS = [
  { key: "overview", label: "Overview" },
  { key: "providers", label: "Providers" },
  { key: "agents", label: "Agents" },
  { key: "resources", label: "Resources" },
  { key: "trophies", label: "Trophies" },
];

const PERIOD_OPTIONS = [
  { value: 1, label: "1h" },
  { value: 7, label: "6h" },
  { value: 24, label: "24h" },
  { value: 168, label: "7d" },
];

type AgentOverview = {
  id: string;
  role: string;
  nickname?: string;
  status?: string;
  corps_id?: string;
  corps_name?: string;
  model_tier?: string;
  started_at?: string;
};

function MetricsCard({
  label,
  value,
  subtitle,
  variant,
}: {
  label: string;
  value: string | number;
  subtitle?: string;
  variant?: "good" | "warning" | "critical";
}) {
  const cls = variant ? `metrics-card metrics-card-${variant}` : "metrics-card";
  return (
    <div className={cls}>
      <div className="metrics-card-header">
        <span className="metrics-label">{label}</span>
      </div>
      <span className="metrics-value">{value}</span>
      {subtitle && <span className="metrics-subtitle">{subtitle}</span>}
    </div>
  );
}

// ---- Overview Tab ----

function OverviewTab({
  health,
  corpsScoreboard,
  awardsSummary,
}: {
  health: SystemHealthData | null;
  corpsScoreboard: CorpsScore[];
  awardsSummary: AwardsSummary | null;
}) {
  if (!health) return <p className="empty">Loading...</p>;

  const failRate = health.failure_rate ?? 0;
  const successRate = health.total_reps > 0 ? ((health.completed_reps / health.total_reps) * 100) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="metrics-grid">
        <MetricsCard
          label="Status"
          value={failRate > 20 ? "Degraded" : "Healthy"}
          variant={failRate > 20 ? "critical" : "good"}
        />
        <MetricsCard label="Active Corps" value={health.active_corps} />
        <MetricsCard label="Active Agents" value={health.active_agents} />
        <MetricsCard
          label="Failure Rate"
          value={`${failRate.toFixed(1)}%`}
          variant={failRate > 20 ? "critical" : failRate > 10 ? "warning" : "good"}
        />
        <MetricsCard
          label="Success Rate"
          value={`${successRate.toFixed(1)}%`}
          variant={successRate < 50 ? "critical" : successRate < 80 ? "warning" : "good"}
        />
        <MetricsCard
          label="Total Trophies"
          value={awardsSummary?.total_awards ?? 0}
        />
      </div>

      {health.corps_summaries.length > 0 && (
        <Panel title="Corps Leaderboard">
          <div className="leaderboard-list">
            {corpsScoreboard.slice(0, 5).map((c) => (
              <div key={c.corps_id} className="leaderboard-row">
                <span className="leaderboard-rank">#{c.rank}</span>
                <span className="leaderboard-label">{c.corps_name}</span>
                <span className="leaderboard-value">{c.composite_score.toFixed(1)}</span>
                <Badge variant={c.corps_status === "on_tour" ? "success" : "default"}>
                  {formatStatus(c.corps_status)}
                </Badge>
              </div>
            ))}
            {corpsScoreboard.length === 0 && (
              <p className="empty">No scoreboard data yet</p>
            )}
          </div>
        </Panel>
      )}

      {health.stale_reps > 0 && (
        <Panel title="Alerts">
          <div className="alert-panel">
            <div className="alert-row">
              <Badge variant="warning">Stale</Badge>
              <div>
                <div className="alert-title">{health.stale_reps} stale rep(s)</div>
                <div className="alert-detail">Reps that haven't progressed recently</div>
              </div>
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}

// ---- Providers Tab ----

function ProvidersTab({
  llmUsage,
  batchStatus,
}: {
  llmUsage: LLMUsageResponse | null;
  batchStatus: any;
}) {
  if (!llmUsage) return <p className="empty">Loading...</p>;

  const totalTokens = llmUsage.providers.reduce(
    (s, p) => s + p.stats.total_input_tokens + p.stats.total_output_tokens,
    0
  );
  const cachedTokens = llmUsage.providers.reduce((s, p) => s + p.stats.total_cached_tokens, 0);
  const cacheRate = totalTokens > 0 ? ((cachedTokens / totalTokens) * 100) : 0;

  const providerRows = llmUsage.providers.map((p) => ({
    name: p.name,
    requests: p.stats.requests,
    successes: p.stats.successes,
    failures: p.stats.failures,
    input_tokens: p.stats.total_input_tokens,
    output_tokens: p.stats.total_output_tokens,
    cached_tokens: p.stats.total_cached_tokens,
  }));

  const providerCols: Column<(typeof providerRows)[0]>[] = [
    { key: "name", label: "Provider", sortable: true },
    { key: "requests", label: "Requests", sortable: true },
    { key: "successes", label: "OK", sortable: true },
    { key: "failures", label: "Fail", sortable: true },
    { key: "input_tokens", label: "In Tokens", sortable: true, render: (v) => (v as number).toLocaleString() },
    { key: "output_tokens", label: "Out Tokens", sortable: true, render: (v) => (v as number).toLocaleString() },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="metrics-grid">
        <MetricsCard label="Active Provider" value={llmUsage.active_provider} />
        <MetricsCard label="Total Requests" value={llmUsage.total_requests} />
        <MetricsCard
          label="Failures"
          value={llmUsage.total_failures}
          variant={llmUsage.total_failures > 0 ? "warning" : "good"}
        />
        <MetricsCard label="Cache Rate" value={`${cacheRate.toFixed(1)}%`} />
      </div>

      <Panel title="Provider Breakdown">
        <DataTable columns={providerCols} data={providerRows} emptyMessage="No providers" />
      </Panel>

      {llmUsage.failover_events.length > 0 && (
        <Panel title="Failover Events">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {llmUsage.failover_events.slice(0, 10).map((ev, i) => (
              <div key={i} style={{ fontSize: 12, display: "flex", gap: 8 }}>
                <Badge variant="warning">{ev.from_provider} → {ev.to_provider}</Badge>
                <span style={{ color: "var(--text-secondary)" }}>{ev.error_snippet}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {batchStatus && (
        <Panel title="Batch Status">
          <pre style={{ fontSize: 11, overflow: "auto" }}>{JSON.stringify(batchStatus, null, 2)}</pre>
        </Panel>
      )}
    </div>
  );
}

// ---- Agents Tab ----

function AgentsTab({
  agents,
  agentLeaderboard,
  bottlenecks,
  workLog,
}: {
  agents: AgentOverview[];
  agentLeaderboard: AgentLeaderEntry[];
  bottlenecks: RoleBottleneck[];
  workLog: WorkLogEntry[];
}) {
  const agentCols: Column<AgentOverview>[] = useMemo(
    () => [
      { key: "role" as any, label: "Role", sortable: true, render: (_v: any, r: AgentOverview) => formatRole(r.role) },
      { key: "nickname" as any, label: "Nickname", sortable: true },
      { key: "corps_name" as any, label: "Corps", sortable: true },
      { key: "model_tier" as any, label: "Tier", sortable: true },
      {
        key: "started_at" as any,
        label: "Started",
        sortable: true,
        render: (v: any) => {
          const ts = formatTimestamp(v as string);
          return <span title={ts.title}>{ts.label}</span>;
        },
      },
    ],
    []
  );

  const leaderCols: Column<AgentLeaderEntry>[] = useMemo(
    () => [
      { key: "rank" as any, label: "#", sortable: true },
      { key: "role" as any, label: "Role", sortable: true, render: (_v: any, r: AgentLeaderEntry) => formatRole(r.role) },
      { key: "nickname" as any, label: "Nickname", sortable: true },
      { key: "total_sessions" as any, label: "Sessions", sortable: true },
      {
        key: "success_rate" as any,
        label: "Success %",
        sortable: true,
        render: (v: any) => `${(v as number).toFixed(1)}%`,
      },
    ],
    []
  );

  const bnCols: Column<RoleBottleneck>[] = useMemo(
    () => [
      { key: "role" as any, label: "Role", sortable: true, render: (_v: any, r: RoleBottleneck) => formatRole(r.role) },
      { key: "session_count" as any, label: "Sessions", sortable: true },
      { key: "mean_duration_s" as any, label: "Mean (s)", sortable: true, render: (v: any) => (v as number).toFixed(1) },
      { key: "p95_duration_s" as any, label: "P95 (s)", sortable: true, render: (v: any) => (v as number).toFixed(1) },
    ],
    []
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Panel title={`Active Agents (${agents.length})`}>
        <DataTable columns={agentCols} data={agents as any[]} emptyMessage="No active agents" />
      </Panel>

      <Panel title="Agent Leaderboard">
        <DataTable columns={leaderCols} data={agentLeaderboard as any[]} emptyMessage="No agent data" />
      </Panel>

      <Panel title="Role Bottlenecks">
        <DataTable columns={bnCols} data={bottlenecks as any[]} emptyMessage="No bottleneck data" />
      </Panel>

      <Panel title="Recent Work Log">
        <div style={{ maxHeight: 300, overflow: "auto" }}>
          {workLog.length === 0 ? (
            <p className="empty">No work log entries</p>
          ) : (
            <table className="styled-table" style={{ fontSize: 12 }}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Role</th>
                  <th>Event</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {workLog.slice(0, 30).map((log) => {
                  const ts = formatTimestamp(log.timestamp);
                  return (
                    <tr key={log.id}>
                      <td title={ts.title}>{ts.label}</td>
                      <td>{log.nickname || log.role}</td>
                      <td><Badge>{log.event_type}</Badge></td>
                      <td style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {log.details}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Panel>
    </div>
  );
}

// ---- Resources Tab ----

function ResourcesTab({
  resourceHealth,
}: {
  resourceHealth: ResourceHealth | null;
}) {
  if (!resourceHealth) return <p className="empty">Loading...</p>;

  const { guard_metrics, process_stats, budget, session_saturation } = resourceHealth;

  const budgetEntries = Object.entries(budget).filter(
    ([k]) => !["instance_id", "pid_file"].includes(k)
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="metrics-grid">
        <MetricsCard
          label="Session Utilization"
          value={`${session_saturation.utilization_pct}%`}
          subtitle={`${session_saturation.active_sessions} / ${session_saturation.max_concurrent}`}
          variant={session_saturation.utilization_pct > 90 ? "critical" : session_saturation.utilization_pct > 70 ? "warning" : "good"}
        />
        <MetricsCard
          label="Active Processes"
          value={process_stats.active_processes}
          variant={process_stats.over_threshold ? "critical" : "good"}
        />
        <MetricsCard
          label="Orphans Reaped"
          value={process_stats.orphans_reaped}
          variant={process_stats.orphans_reaped > 0 ? "warning" : "good"}
        />
        <MetricsCard
          label="Guard Activations"
          value={guard_metrics.sync_guard_activations + guard_metrics.async_guard_activations}
          subtitle={`sync: ${guard_metrics.sync_guard_activations} / async: ${guard_metrics.async_guard_activations}`}
          variant={guard_metrics.sync_guard_activations + guard_metrics.async_guard_activations > 0 ? "warning" : "good"}
        />
        <MetricsCard
          label="Cascades"
          value={guard_metrics.total_cascades}
          subtitle={`${guard_metrics.total_children_cascaded} children affected`}
          variant={guard_metrics.total_cascades > 0 ? "warning" : "good"}
        />
        <MetricsCard
          label="Unhandled Exceptions"
          value={guard_metrics.unhandled_exceptions_caught}
          variant={guard_metrics.unhandled_exceptions_caught > 0 ? "critical" : "good"}
        />
      </div>

      {budgetEntries.length > 0 && (
        <Panel title="Budget">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
            {budgetEntries.map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", padding: "4px 0" }}>
                <span style={{ color: "var(--text-secondary)" }}>{k.replace(/_/g, " ")}</span>
                <span style={{ fontFamily: "JetBrains Mono, monospace" }}>
                  {typeof v === "number" ? v.toLocaleString() : String(v)}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

// ---- Trophies Tab ----

function TrophiesTab({
  awardsSummary,
  awards,
}: {
  awardsSummary: AwardsSummary | null;
  awards: V1Award[];
}) {
  if (!awardsSummary) return <p className="empty">Loading...</p>;

  const activeCats = Object.values(awardsSummary.by_category).filter((c) => c.total > 0).length;
  const highestTier = (() => {
    const tierOrder = ["diamond", "platinum", "gold", "silver", "bronze"];
    for (const t of tierOrder) {
      if ((awardsSummary.by_tier[t] || 0) > 0) return t;
    }
    return "none";
  })();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="metrics-grid">
        <MetricsCard label="Total Awards" value={awardsSummary.total_awards} />
        <MetricsCard label="Active Categories" value={`${activeCats} / 12`} />
        <MetricsCard label="Highest Tier" value={highestTier} />
      </div>

      <Panel title="Trophy Showcase">
        <TrophyShowcase summary={awardsSummary} />
      </Panel>

      {awards.length > 0 && (
        <Panel title="Recent Awards">
          <div style={{ maxHeight: 300, overflow: "auto" }}>
            <table className="styled-table" style={{ fontSize: 12 }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Tier</th>
                  <th>Recipient</th>
                  <th>Awarded</th>
                </tr>
              </thead>
              <tbody>
                {awards.slice(0, 20).map((a) => {
                  const ts = formatTimestamp(a.awarded_at || undefined);
                  return (
                    <tr key={a.id}>
                      <td>{a.name}</td>
                      <td>{a.category.replace(/_/g, " ")}</td>
                      <td><Badge>{a.tier}</Badge></td>
                      <td>{a.recipient_name}</td>
                      <td title={ts.title}>{ts.label}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}

// ---- Main Page ----

export function SwarmHealthPage() {
  const [tab, setTab] = useState("overview");
  const [periodDays, setPeriodDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  // Data state
  const [health, setHealth] = useState<SystemHealthData | null>(null);
  const [llmUsage, setLlmUsage] = useState<LLMUsageResponse | null>(null);
  const [batchStatus, setBatchStatus] = useState<any>(null);
  const [agents, setAgents] = useState<AgentOverview[]>([]);
  const [workLog, setWorkLog] = useState<WorkLogEntry[]>([]);
  const [resourceHealth, setResourceHealth] = useState<ResourceHealth | null>(null);
  const [awardsSummary, setAwardsSummary] = useState<AwardsSummary | null>(null);
  const [awards, setAwards] = useState<V1Award[]>([]);
  const [corpsScoreboard, setCorpsScoreboard] = useState<CorpsScore[]>([]);
  const [agentLeaderboard, setAgentLeaderboard] = useState<AgentLeaderEntry[]>([]);
  const [bottlenecks, setBottlenecks] = useState<RoleBottleneck[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, l, a, w, rh, as_, aw, cs, al, bn, batch] = await Promise.all([
        v1.getSystemHealth().catch(() => null),
        v1.getLLMUsage().catch(() => null),
        v1.getAgentsOverview().catch(() => []),
        v1.getGlobalWorkLog(30).catch(() => []),
        v1.getResourceHealth().catch(() => null),
        v1.getAwardsSummary().catch(() => null),
        v1.listAwards({}, undefined).catch(() => []),
        v1.getCorpsScoreboard(periodDays).catch(() => ({ scoreboard: [] })),
        v1.getAgentLeaderboard(undefined, periodDays).catch(() => ({ leaderboard: [] })),
        v1.getBottlenecks(undefined, periodDays).catch(() => ({ role_bottlenecks: [] })),
        v1.getLlmBatchStatus().catch(() => null),
      ]);

      setHealth(h as SystemHealthData | null);
      setLlmUsage(l);
      setAgents(a as AgentOverview[]);
      setWorkLog(w as WorkLogEntry[]);
      setResourceHealth(rh);
      setAwardsSummary(as_);
      setAwards(aw);
      setCorpsScoreboard((cs as any)?.scoreboard ?? []);
      setAgentLeaderboard((al as any)?.leaderboard ?? []);
      setBottlenecks((bn as any)?.role_bottlenecks ?? []);
      setBatchStatus(batch);
      setLastRefresh(new Date().toISOString());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [periodDays]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(id);
  }, [refresh]);

  // WebSocket for live refresh trigger
  useEffect(() => {
    let ws: WebSocket | null = null;
    try {
      const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const wsUrl = base.replace(/^http/, "ws") + "/ws/metrics";
      ws = new WebSocket(wsUrl);
      ws.onmessage = () => refresh();
      ws.onerror = () => {};
    } catch {
      // WS not available — polling will handle it
    }
    return () => {
      ws?.close();
    };
  }, [refresh]);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Swarm Health</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <div style={{ display: "flex", gap: 2 }}>
            {PERIOD_OPTIONS.map((p) => (
              <button
                key={p.value}
                className={`tab ${periodDays === p.value ? "active" : ""}`}
                onClick={() => setPeriodDays(p.value)}
                style={{ fontSize: 11, padding: "4px 8px" }}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            className="btn btn-sm"
            onClick={refresh}
            disabled={loading}
            style={{ fontSize: 11, padding: "4px 10px" }}
          >
            {loading ? "..." : "Refresh"}
          </button>
          {lastRefresh && (
            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
              {relativeTime(lastRefresh)}
            </span>
          )}
        </div>
      </div>

      {error && (
        <div style={{ padding: "8px 12px", marginBottom: 12, border: "1px solid var(--danger)", background: "rgba(255,0,0,0.05)" }}>
          {error}
        </div>
      )}

      <Tabs active={tab} onChange={setTab} items={TAB_ITEMS} />

      <div style={{ marginTop: 16 }}>
        {tab === "overview" && (
          <OverviewTab health={health} corpsScoreboard={corpsScoreboard} awardsSummary={awardsSummary} />
        )}
        {tab === "providers" && (
          <ProvidersTab llmUsage={llmUsage} batchStatus={batchStatus} />
        )}
        {tab === "agents" && (
          <AgentsTab agents={agents} agentLeaderboard={agentLeaderboard} bottlenecks={bottlenecks} workLog={workLog} />
        )}
        {tab === "resources" && (
          <ResourcesTab resourceHealth={resourceHealth} />
        )}
        {tab === "trophies" && (
          <TrophiesTab awardsSummary={awardsSummary} awards={awards} />
        )}
      </div>
    </div>
  );
}
