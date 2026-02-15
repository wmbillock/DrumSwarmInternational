import { useEffect, useState, useCallback } from "react";
import { Panel, DataTable } from "../ui";
import * as v1 from "../services/v1";
import type { SystemHealth as SystemHealthData } from "../types";
import { formatMode, formatStatus } from "../utils/formatters";

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
  const display = formatStatus(status);
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
      {display}
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

  const fetchHealth = useCallback(async (signal?: AbortSignal) => {
    try {
      const health = await v1.getSystemHealth(signal);
      if (signal?.aborted) return;
      setData(health);
      setError(null);
      setLastRefresh(new Date());
    } catch (e: any) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e.message ?? "Failed to fetch system health");
    }
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    fetchHealth(ac.signal);
    const id = setInterval(() => fetchHealth(), REFRESH_MS);
    return () => { ac.abort(); clearInterval(id); };
  }, [fetchHealth]);

  if (error && !data) {
    return (
      <div className="page-content">
        <div className="page-header">
          <h2 className="page-title">System Health</h2>
        </div>
        <Panel title="Error">
          <p style={{ color: "#ef4444" }}>{error}</p>
        </Panel>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page-content">
        <div className="page-header">
          <h2 className="page-title">System Health</h2>
        </div>
        <Panel title="Loading...">
          <p>Fetching system health data...</p>
        </Panel>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h2 className="page-title">System Health</h2>
        {lastRefresh && (
          <span style={{ marginLeft: "auto", fontSize: 11, opacity: 0.5 }}>
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
          <Stat label="Failure Rate" value={`${data.failure_rate.toFixed(1)}%`} />
        </div>
      </Panel>

      <Panel title="Corps Health" className="mt-4">
        <DataTable<SystemHealthData["corps_summaries"][number] & Record<string, unknown>>
          columns={[
            { key: "name", label: "Corps", render: (v) => <span style={{ fontWeight: 600 }}>{String(v)}</span> },
            { key: "status", label: "Status", render: (v) => <StatusBadge status={String(v)} /> },
            { key: "mode", label: "Mode", render: (v) => formatMode(String(v || "")) },
            { key: "agents_active", label: "Agents", render: (_v, row) => `${row.agents_active} / ${row.agents_total}` },
            { key: "sessions_total", label: "Sessions", render: (v) => String(v ?? 0) },
            { key: "reps_completed", label: "Reps", render: (_v, row) => `${row.reps_completed} / ${row.reps_total}` },
            { key: "failures", label: "Failures", render: (v) => (
              <span style={{ color: Number(v) > 0 ? "#ef4444" : "inherit" }}>{String(v ?? 0)}</span>
            ) },
          ]}
          data={data.corps_summaries as (SystemHealthData["corps_summaries"][number] & Record<string, unknown>)[]}
          emptyMessage="No corps health data."
        />
      </Panel>
    </div>
  );
}
