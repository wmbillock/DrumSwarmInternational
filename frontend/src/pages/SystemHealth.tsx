import { useEffect, useState, useCallback } from "react";
import { Panel } from "../ui";
import { getSystemHealth } from "../services/api";
import type { SystemHealth as SystemHealthData } from "../types";

function statusColor(status: string): string {
  switch (status.toLowerCase()) {
    case "healthy":
    case "active":
    case "running":
      return "#22c55e";
    case "warning":
    case "degraded":
      return "#eab308";
    case "critical":
    case "failed":
    case "error":
      return "#ef4444";
    default:
      return "#94a3b8";
  }
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        color: "#fff",
        backgroundColor: statusColor(status),
        textTransform: "uppercase",
      }}
    >
      {status}
    </span>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ textAlign: "center", minWidth: 90 }}>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>{label}</div>
    </div>
  );
}

const REFRESH_MS = 15_000;

export function SystemHealth() {
  const [data, setData] = useState<SystemHealthData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const health = await getSystemHealth();
      setData(health);
      setError(null);
      setLastRefresh(new Date());
    } catch (e: any) {
      setError(e.message ?? "Failed to fetch system health");
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const id = setInterval(fetchHealth, REFRESH_MS);
    return () => clearInterval(id);
  }, [fetchHealth]);

  if (error && !data) {
    return (
      <div className="page-content">
        <h2>System Health</h2>
        <Panel title="Error">
          <p style={{ color: "#ef4444" }}>{error}</p>
        </Panel>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page-content">
        <h2>System Health</h2>
        <Panel title="Loading...">
          <p>Fetching system health data...</p>
        </Panel>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>System Health</h2>
        {lastRefresh && (
          <span style={{ fontSize: 11, opacity: 0.5 }}>
            Last updated: {lastRefresh.toLocaleTimeString()} (auto-refresh 15s)
          </span>
        )}
      </div>

      <Panel title="System Vitals">
        <div style={{ display: "flex", gap: 32, flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <span style={{ fontSize: 11, opacity: 0.7, marginRight: 8 }}>Status</span>
            <StatusBadge status={data.status} />
          </div>
          <Stat label="Active Corps" value={data.active_corps} />
          <Stat label="Total Agents" value={data.total_agents} />
          <Stat label="Active Agents" value={data.active_agents} />
          <Stat label="Failed Agents" value={data.failed_agents} />
          <Stat label="Sessions" value={data.total_sessions} />
          <Stat label="Total Reps" value={data.total_reps} />
          <Stat label="Completed" value={data.completed_reps} />
          <Stat label="Failed Reps" value={data.failed_reps} />
          <Stat label="Stale Reps" value={data.stale_reps} />
          <Stat label="Failure Rate" value={`${(data.failure_rate * 100).toFixed(1)}%`} />
        </div>
      </Panel>

      <Panel title="Corps Health" className="mt-4">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", textAlign: "left" }}>
                <th style={{ padding: "8px 12px" }}>Corps</th>
                <th style={{ padding: "8px 12px" }}>Status</th>
                <th style={{ padding: "8px 12px" }}>Mode</th>
                <th style={{ padding: "8px 12px" }}>Agents</th>
                <th style={{ padding: "8px 12px" }}>Sessions</th>
                <th style={{ padding: "8px 12px" }}>Reps</th>
                <th style={{ padding: "8px 12px" }}>Failures</th>
              </tr>
            </thead>
            <tbody>
              {data.corps_summaries.map((c) => (
                <tr key={c.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <td style={{ padding: "8px 12px", fontWeight: 600 }}>{c.name}</td>
                  <td style={{ padding: "8px 12px" }}>
                    <StatusBadge status={c.status} />
                  </td>
                  <td style={{ padding: "8px 12px" }}>{c.mode}</td>
                  <td style={{ padding: "8px 12px" }}>
                    {c.agents_active} / {c.agents_total}
                  </td>
                  <td style={{ padding: "8px 12px" }}>{c.sessions_total}</td>
                  <td style={{ padding: "8px 12px" }}>
                    {c.reps_completed} / {c.reps_total}
                  </td>
                  <td style={{ padding: "8px 12px" }}>
                    <span style={{ color: c.failures > 0 ? "#ef4444" : "inherit" }}>
                      {c.failures}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
