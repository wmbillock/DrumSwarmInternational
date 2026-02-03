/**
 * Metrics Dashboard — Live visualization of swarm performance metrics.
 */

import { useEffect, useMemo, useState } from "react";
import "../styles/Metrics.css";
import * as v1 from "../services/v1";
import { MetricsCard, TrendChart, Leaderboard, AlertPanel } from "../components/metrics";

const REFRESH_MS = 30_000;

const RANGE_OPTIONS = [
  { key: "1h", label: "1h", periodDays: 1 },
  { key: "6h", label: "6h", periodDays: 1 },
  { key: "24h", label: "24h", periodDays: 1 },
  { key: "7d", label: "7d", periodDays: 7 },
];

const statusForValue = (value: number, good: number, warn: number) => {
  if (value >= good) return "good";
  if (value >= warn) return "warning";
  return "critical";
};

const MetricsDashboard = () => {
  const [range, setRange] = useState("24h");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [corpsScoreboard, setCorpsScoreboard] = useState<v1.CorpsScore[]>([]);
  const [agentLeaderboard, setAgentLeaderboard] = useState<v1.AgentLeaderEntry[]>([]);
  const [trends, setTrends] = useState<v1.MetricTrend[]>([]);
  const [bottlenecks, setBottlenecks] = useState<v1.RoleBottleneck[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  const periodDays = RANGE_OPTIONS.find(r => r.key === range)?.periodDays ?? 7;

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [corpsRes, agentRes, trendRes, bottleneckRes] = await Promise.all([
        v1.getCorpsScoreboard(periodDays),
        v1.getAgentLeaderboard(undefined, periodDays),
        v1.getMetricsTrends(undefined, undefined, periodDays),
        v1.getBottlenecks(undefined, periodDays),
      ]);
      setCorpsScoreboard(corpsRes.scoreboard || []);
      setAgentLeaderboard(agentRes.leaderboard || []);
      setTrends(trendRes.trends || []);
      setBottlenecks(bottleneckRes.role_bottlenecks || []);
    } catch (e: any) {
      setError(e?.message || "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(id);
  }, [periodDays]);

  useEffect(() => {
    const wsUrl = window.location.origin.replace(/^http/, "ws") + "/ws/metrics";
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
      ws.onerror = () => setWsConnected(false);
      ws.onmessage = () => refresh();
    } catch {
      setWsConnected(false);
    }
    return () => ws?.close();
  }, [periodDays]);

  const completionAvg = useMemo(() => {
    if (!corpsScoreboard.length) return 0;
    return corpsScoreboard.reduce((sum, c) => sum + (c.completion_score || 0), 0) / corpsScoreboard.length;
  }, [corpsScoreboard]);

  const agentSuccessAvg = useMemo(() => {
    if (!agentLeaderboard.length) return 0;
    return agentLeaderboard.reduce((sum, a) => sum + (a.success_rate || 0), 0) / agentLeaderboard.length;
  }, [agentLeaderboard]);

  const trendSparkline = (metricType: string) => {
    const metric = trends.find(t => t.metric_type === metricType);
    if (!metric) return [];
    const prev = metric.prev_period_avg ?? metric.avg_value ?? 0;
    const curr = metric.avg_value ?? prev;
    return [prev, (prev + curr) / 2, curr];
  };

  const topCorpsRows = corpsScoreboard.slice(0, 5).map(c => ({
    id: c.corps_id,
    rank: c.rank,
    label: c.corps_name,
    value: `${c.composite_score.toFixed(1)}`,
    status: statusForValue(c.composite_score, 80, 60),
  }));

  const alertRows = bottlenecks.slice(0, 5).map((b, idx) => ({
    id: `${b.role}-${idx}`,
    title: `${b.role} latency`,
    detail: `p95 ${b.p95_duration_s.toFixed(1)}s`,
    status: b.p95_duration_s >= 30 ? "critical" : b.p95_duration_s >= 10 ? "warning" : "good",
  }));

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Metrics Dashboard</h1>
        <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          <span className="text-muted">{wsConnected ? "Live" : "Polling"}</span>
          <select className="library-filter" value={range} onChange={(e) => setRange(e.target.value)}>
            {RANGE_OPTIONS.map(opt => <option key={opt.key} value={opt.key}>{opt.label}</option>)}
          </select>
          <button className="small" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="metrics-grid">
        <MetricsCard
          title="Corps Completion"
          value={`${completionAvg.toFixed(1)}%`}
          status={statusForValue(completionAvg, 80, 60)}
          subtitle="Average completion rate"
          sparkline={trendSparkline("rep_completed")}
        />
        <MetricsCard
          title="Agent Success"
          value={`${agentSuccessAvg.toFixed(1)}%`}
          status={statusForValue(agentSuccessAvg, 85, 70)}
          subtitle="Avg success rate"
          sparkline={trendSparkline("task_latency")}
        />
        <MetricsCard
          title="Bottlenecks"
          value={bottlenecks.length}
          status={bottlenecks.length > 5 ? "critical" : bottlenecks.length > 0 ? "warning" : "good"}
          subtitle="Roles exceeding p95"
        />
      </div>

      <div className="metrics-grid" style={{ marginTop: 16 }}>
        <MetricsCard
          title="Top Corps"
          value={corpsScoreboard.length}
          status="neutral"
          subtitle="Tracked in range"
        />
        <MetricsCard
          title="Agent Leaders"
          value={agentLeaderboard.length}
          status="neutral"
          subtitle="Active leaders"
        />
        <MetricsCard
          title="Refresh Interval"
          value="30s"
          status="neutral"
          subtitle="Auto refresh"
        />
      </div>

      <div style={{ marginTop: 24, display: "grid", gap: 16, gridTemplateColumns: "2fr 1fr" }}>
        <TrendChart
          title="Composite Trend"
          series={[
            {
              id: "completion",
              label: "Completion",
              color: "#16a34a",
              points: trendSparkline("rep_completed").map((y, i) => ({ x: i, y })),
            },
            {
              id: "latency",
              label: "Latency",
              color: "#f97316",
              points: trendSparkline("task_latency").map((y, i) => ({ x: i, y })),
            },
          ]}
        />
        <Leaderboard
          title="Top Corps"
          rows={topCorpsRows}
          onRowClick={(row) => window.location.assign(`/corps/${row.id}/overview`)}
        />
      </div>

      <div style={{ marginTop: 24 }}>
        <AlertPanel title="Alerts" alerts={alertRows} />
      </div>
    </div>
  );
};

export default MetricsDashboard;
