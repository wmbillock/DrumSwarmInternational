import { useEffect, useMemo, useState } from "react";
import type { SystemHealth as SystemHealthData, WorkLogEntry } from "../types";
import * as v1 from "../services/v1";
import { Badge, DataTable } from "../ui";
import { formatStatus, formatTimestamp } from "../utils/formatters";

const REFRESH_MS = 30_000;

type AgentOverview = {
  id: string;
  role: string;
  nickname?: string;
  status?: string;
};

export function SystemHealthDashboard() {
  const [health, setHealth] = useState<SystemHealthData | null>(null);
  const [llmUsage, setLlmUsage] = useState<import("../types").LLMUsageResponse | null>(null);
  const [agents, setAgents] = useState<AgentOverview[]>([]);
  const [workLog, setWorkLog] = useState<WorkLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  const statusVariant = (status?: string) => {
    switch ((status || "").toLowerCase()) {
      case "ok":
      case "healthy":
        return "success";
      case "warning":
      case "degraded":
        return "warning";
      case "error":
      case "critical":
      case "failed":
        return "danger";
      default:
        return "default";
    }
  };

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, l, a, w] = await Promise.all([
        v1.getSystemHealth(),
        v1.getLLMUsage(),
        v1.getAgentsOverview(),
        v1.getGlobalWorkLog(20),
      ]);
      setHealth(h as SystemHealthData);
      setLlmUsage(l);
      setAgents(a as AgentOverview[]);
      setWorkLog(w as WorkLogEntry[]);
      setLastRefresh(new Date().toISOString());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load system health");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(id);
  }, []);

  const providerRows = useMemo(() => {
    if (!llmUsage) return [];
    return llmUsage.providers.map(p => ({
      name: p.name,
      status: p.name === llmUsage.active_provider ? "ACTIVE" : "standby",
      requests: p.stats.requests,
      ok: p.stats.successes,
      fail: p.stats.failures,
      tokens: `${p.stats.total_input_tokens.toLocaleString()} / ${p.stats.total_output_tokens.toLocaleString()} / ${p.stats.total_cached_tokens.toLocaleString()}`,
      capabilities: p.capabilities,
    }));
  }, [llmUsage]);

  if (loading && !health) return <div className="page-loading">Loading system health...</div>;

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">System Health</h1>
        <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          {lastRefresh && (
            <span className="text-muted" title={formatTimestamp(lastRefresh).title}>
              Updated {formatTimestamp(lastRefresh).label}
            </span>
          )}
          <button className="small" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={refresh}>Retry</button>
        </div>
      )}

      <section className="dash-section">
        <h2>Status</h2>
        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <Badge variant={statusVariant((health as any)?.status)}>
            {formatStatus((health as any)?.status || "unknown")}
          </Badge>
          <span className="text-muted">Auto-refresh every 30s</span>
        </div>
      </section>

      {health && (
        <section className="dash-section">
          <h2>Swarm Stats</h2>
          <div className="summary-bar">
            <div className="summary-stat"><span className="summary-value">{health.active_corps}</span><span className="summary-label">Active Corps</span></div>
            <div className="summary-stat"><span className="summary-value">{health.total_agents}</span><span className="summary-label">Total Agents</span></div>
            <div className="summary-stat"><span className="summary-value">{health.active_agents}</span><span className="summary-label">Active Agents</span></div>
            <div className="summary-stat"><span className="summary-value">{health.total_sessions}</span><span className="summary-label">Sessions</span></div>
            <div className="summary-stat"><span className="summary-value">{health.completed_reps}</span><span className="summary-label">Reps Done</span></div>
            <div className="summary-stat"><span className="summary-value">{health.failed_reps}</span><span className="summary-label">Reps Failed</span></div>
          </div>
        </section>
      )}

      <section className="dash-section">
        <h2>LLM Providers</h2>
        <DataTable<Record<string, unknown>>
          columns={[
            { key: "name", label: "Provider" },
            { key: "status", label: "Status" },
            { key: "capabilities", label: "Capabilities", render: (_v, row) => (
              <>
                {row.capabilities.supports_images && <Badge variant="info">IMG</Badge>}
                {row.capabilities.supports_native_tools && <Badge variant="info">TOOLS</Badge>}
                {row.capabilities.supports_caching && <Badge variant="info">CACHE</Badge>}
                {!row.capabilities.supports_images && !row.capabilities.supports_native_tools && !row.capabilities.supports_caching && (
                  <span className="text-muted">text-only</span>
                )}
              </>
            ) },
            { key: "requests", label: "Requests" },
            { key: "ok", label: "OK" },
            { key: "fail", label: "Fail" },
            { key: "tokens", label: "Tokens (in/out/cached)" },
          ]}
          data={providerRows}
          emptyMessage="No provider data available."
        />
      </section>

      <section className="dash-section">
        <h2>Agents</h2>
        <DataTable<Record<string, unknown>>
          columns={[
            { key: "role", label: "Role" },
            { key: "nickname", label: "Nickname" },
            { key: "status", label: "Status", render: (v) => <Badge>{formatStatus(String(v || "unknown"))}</Badge> },
          ]}
          data={agents as Record<string, unknown>[]}
          emptyMessage="No agents reported."
        />
      </section>

      <section className="dash-section">
        <h2>Work Log</h2>
        <DataTable<Record<string, unknown>>
          columns={[
            { key: "timestamp", label: "Time", render: (v) => {
              const ts = formatTimestamp(String(v));
              return <span title={ts.title}>{ts.label}</span>;
            } },
            { key: "event_type", label: "Event" },
            { key: "role", label: "Role" },
            { key: "details", label: "Details", render: (v) => <span title={String(v || "")}>{String(v || "").slice(0, 120)}</span> },
          ]}
          data={workLog as Record<string, unknown>[]}
          emptyMessage="No work log entries."
        />
      </section>
    </div>
  );
}

export default SystemHealthDashboard;
