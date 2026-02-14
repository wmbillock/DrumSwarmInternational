/**
 * Scoreboards Page — Rankings and leaderboards for corps, agents, and model specs.
 */

import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Tabs, Badge, DataTable } from "../ui";
import type { TabItem } from "../ui";
import "../styles/Metrics.css";
import {
  getCorpsScoreboard,
  getAgentLeaderboard,
  listModelSpecs,
  getLeaderboard,
} from "../services/v1";
import type { CorpsScore, AgentLeaderEntry, V1ModelSpec, V1LeaderboardEntry } from "../services/v1";
import { badgeForCorpsStatus, formatRole, formatStatus } from "../utils/formatters";

export function ScoreboardsPage() {
  const [corpsList, setCorpsList] = useState<CorpsScore[]>([]);
  const [agentsList, setAgentsList] = useState<AgentLeaderEntry[]>([]);
  const [modelSpecs, setModelSpecs] = useState<V1ModelSpec[]>([]);
  const [leaderboard, setLeaderboard] = useState<V1LeaderboardEntry[]>([]);
  const [leaderboardCategory, setLeaderboardCategory] = useState("overall");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [periodDays, setPeriodDays] = useState(7);
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "corps");
  const navigate = useNavigate();

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [corpsRes, agentsRes, specs] = await Promise.all([
        getCorpsScoreboard(periodDays),
        getAgentLeaderboard(undefined, periodDays),
        listModelSpecs().catch(() => []),
      ]);
      setCorpsList(corpsRes.scoreboard || []);
      setAgentsList(agentsRes.leaderboard || []);
      setModelSpecs(Array.isArray(specs) ? specs : []);
    } catch (error: any) {
      setError(error?.message || "Failed to fetch scoreboards");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds for live updates
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [periodDays]);

  // Load leaderboard when category changes and we're on model-specs tab
  useEffect(() => {
    if (activeTab !== "model-specs") return;
    const ac = new AbortController();
    getLeaderboard(leaderboardCategory, 20, ac.signal)
      .then((res) => setLeaderboard(res.entries || []))
      .catch(() => setLeaderboard([]));
    return () => ac.abort();
  }, [activeTab, leaderboardCategory]);

  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab && tab !== activeTab) {
      setActiveTab(tab);
    }
  }, [searchParams, activeTab]);

  const tabs: TabItem[] = [
    { key: "corps", label: `Corps (${corpsList.length})` },
    { key: "agents", label: `Agents (${agentsList.length})` },
    { key: "model-specs", label: `Model Specs (${modelSpecs.length})` },
  ];

  const medalForRank = (rank: number) => {
    if (rank === 1) return "🥇";
    if (rank === 2) return "🥈";
    if (rank === 3) return "🥉";
    return `#${rank}`;
  };

  // Collect unique task categories from model specs
  const taskCategories = Array.from(
    new Set(modelSpecs.flatMap((s) => s.task_categories))
  ).sort();

  return (
    <div className="page-content">
      <div className="page-header">
        <h2 className="page-title">Scoreboards</h2>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <select
            className="library-filter"
            value={periodDays}
            onChange={e => setPeriodDays(Number(e.target.value))}
          >
            <option value={7}>Last 7 Days</option>
            <option value={14}>Last 14 Days</option>
            <option value={30}>Last 30 Days</option>
          </select>
          <button className="small" onClick={fetchData}>Refresh</button>
        </div>
      </div>

      <Tabs
        items={tabs}
        active={activeTab}
        onChange={(tab) => {
          setActiveTab(tab);
          const next = new URLSearchParams(searchParams);
          next.set("tab", tab);
          setSearchParams(next, { replace: true });
        }}
      />

      {loading && <div className="page-loading">Loading...</div>}
      {error && <div className="error-banner">{error}</div>}

      {!loading && activeTab === "corps" && (
        <>
          <DataTable<CorpsScore & Record<string, unknown>>
            columns={[
              { key: "rank", label: "Rank", sortable: true, render: (v) => (
                <span className={`standings-rank rank-${String(v)}`}>{medalForRank(Number(v))}</span>
              ) },
              { key: "corps_name", label: "Corps", render: (v) => (
                <span className="link" style={{ fontWeight: 600, textDecoration: "underline" }}>
                  {String(v)}
                </span>
              ) },
              { key: "corps_status", label: "Status", render: (v) => <Badge variant={badgeForCorpsStatus(String(v))}>{formatStatus(String(v))}</Badge> },
              { key: "completion_score", label: "Completion", render: (v) => (
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <div className="progress-bar" style={{ width: 80 }}>
                    <div className="progress-fill" style={{ width: `${Math.round(Number(v))}%` }} />
                  </div>
                  <span style={{ fontSize: 11 }}>{Math.round(Number(v))}%</span>
                </div>
              ) },
              { key: "efficiency_score", label: "Efficiency", sortable: true, render: (v) => `${Number(v).toFixed(1)}%` },
              { key: "completed_sessions", label: "Sessions", render: (_v, row) => `${row.completed_sessions}/${row.total_sessions}` },
              { key: "completed_reps", label: "Reps", render: (_v, row) => `${row.completed_reps}/${row.total_reps}` },
              { key: "composite_score", label: "Score", sortable: true, render: (v) => <span className="standings-score">{Number(v).toFixed(1)}</span> },
            ]}
            data={corpsList as (CorpsScore & Record<string, unknown>)[]}
            onRowClick={(row) => navigate(`/corps/${row.corps_id}/overview`)}
            emptyMessage="No corps data available"
          />

        </>
      )}

      {!loading && activeTab === "agents" && (
        <DataTable<AgentLeaderEntry & Record<string, unknown>>
          columns={[
            { key: "rank", label: "Rank", sortable: true, render: (v) => <span className={`standings-rank rank-${String(v)}`}>{medalForRank(Number(v))}</span> },
            { key: "role", label: "Role", sortable: true, render: (v) => <span style={{ fontWeight: 600 }}>{formatRole(String(v))}</span> },
            { key: "nickname", label: "Nickname", render: (v) => String(v || "—") },
            { key: "total_sessions", label: "Sessions", render: (v) => String(v ?? 0) },
            { key: "completed_sessions", label: "Completed", render: (v) => String(v ?? 0) },
            { key: "failed_sessions", label: "Failed", render: (v) => (
              <span style={{ color: Number(v) > 0 ? "var(--danger)" : undefined }}>{String(v ?? 0)}</span>
            ) },
            { key: "success_rate", label: "Success Rate", render: (v) => (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div className="progress-bar" style={{ width: 80 }}>
                  <div className="progress-fill" style={{
                    width: `${Math.round(Number(v))}%`,
                    background: Number(v) >= 80 ? "var(--success)" : Number(v) >= 50 ? "var(--warning)" : "var(--danger)",
                  }} />
                </div>
                <span>{Math.round(Number(v))}%</span>
              </div>
            ) },
          ]}
          data={agentsList as (AgentLeaderEntry & Record<string, unknown>)[]}
          onRowClick={(row) => navigate(`/corps/${row.corps_id}`)}
          emptyMessage="No agent data available"
        />
      )}

      {!loading && activeTab === "model-specs" && (
        <div>
          <DataTable<V1ModelSpec & Record<string, unknown>>
            columns={[
              { key: "name", label: "Model", sortable: true, render: (v) => (
                <span style={{ fontWeight: 600 }}>{String(v)}</span>
              ) },
              { key: "provider", label: "Provider", sortable: true, render: (v) => (
                <Badge variant="default">{String(v)}</Badge>
              ) },
              { key: "model_id", label: "Model ID", render: (v) => (
                <span style={{ fontFamily: "monospace", fontSize: 12 }}>{String(v)}</span>
              ) },
              { key: "task_categories", label: "Categories", render: (v) => {
                const cats = v as unknown as string[];
                return cats?.length
                  ? <span style={{ fontSize: 12 }}>{cats.join(", ")}</span>
                  : <span className="text-muted">—</span>;
              } },
              { key: "is_active", label: "Status", render: (v) => (
                <Badge variant={v ? "success" : "default"}>{v ? "Active" : "Inactive"}</Badge>
              ) },
              { key: "performance", label: "Avg Score", sortable: true, render: (v) => {
                const perf = v as unknown as Record<string, { avg_score: number; total_attempts: number }>;
                if (!perf || Object.keys(perf).length === 0) return <span className="text-muted">—</span>;
                const scores = Object.values(perf).filter((p) => p.total_attempts > 0);
                if (scores.length === 0) return <span className="text-muted">—</span>;
                const avg = scores.reduce((s, p) => s + p.avg_score, 0) / scores.length;
                return <span className="standings-score">{avg.toFixed(1)}</span>;
              } },
            ]}
            data={modelSpecs as (V1ModelSpec & Record<string, unknown>)[]}
            emptyMessage="No model specs configured"
          />

          {/* Leaderboard section */}
          {taskCategories.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 16 }}>Leaderboard</h3>
                <select
                  className="library-filter"
                  value={leaderboardCategory}
                  onChange={(e) => setLeaderboardCategory(e.target.value)}
                >
                  <option value="overall">Overall</option>
                  {taskCategories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
              <DataTable<(V1LeaderboardEntry & { rank: number }) & Record<string, unknown>>
                columns={[
                  { key: "rank", label: "Rank", render: (v) => (
                    <span className={`standings-rank rank-${v}`}>{medalForRank(Number(v))}</span>
                  ) },
                  { key: "name", label: "Model", render: (v) => (
                    <span style={{ fontWeight: 600 }}>{String(v)}</span>
                  ) },
                  { key: "provider", label: "Provider", render: (v) => (
                    <Badge variant="default">{String(v)}</Badge>
                  ) },
                  { key: "avg_score", label: "Avg Score", sortable: true, render: (v) => (
                    <span className="standings-score">{Number(v).toFixed(1)}</span>
                  ) },
                  { key: "total_attempts", label: "Attempts", render: (v) => String(v ?? 0) },
                  { key: "success_rate", label: "Success Rate", render: (v) => (
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div className="progress-bar" style={{ width: 80 }}>
                        <div className="progress-fill" style={{
                          width: `${Math.round(Number(v))}%`,
                          background: Number(v) >= 80 ? "var(--success)" : Number(v) >= 50 ? "var(--warning)" : "var(--danger)",
                        }} />
                      </div>
                      <span>{Math.round(Number(v))}%</span>
                    </div>
                  ) },
                ]}
                data={leaderboard.map((e, i) => ({ ...e, rank: i + 1 })) as ((V1LeaderboardEntry & { rank: number }) & Record<string, unknown>)[]}
                emptyMessage="No leaderboard data for this category"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Keep default export for backward compat with router
export default ScoreboardsPage;
