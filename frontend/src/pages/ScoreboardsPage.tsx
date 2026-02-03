/**
 * Scoreboards Page — Rankings and leaderboards for corps and agents.
 */

import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Tabs, Badge, DataTable } from "../ui";
import type { TabItem } from "../ui";
import {
  getCorpsScoreboard,
  getAgentLeaderboard,
} from "../services/v1";
import type { CorpsScore, AgentLeaderEntry } from "../services/v1";
import { badgeForCorpsStatus, formatRole, formatStatus } from "../utils/formatters";

export function ScoreboardsPage() {
  const [corpsList, setCorpsList] = useState<CorpsScore[]>([]);
  const [agentsList, setAgentsList] = useState<AgentLeaderEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState(7);
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "corps");
  const navigate = useNavigate();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [corpsRes, agentsRes] = await Promise.all([
        getCorpsScoreboard(periodDays),
        getAgentLeaderboard(undefined, periodDays),
      ]);
      setCorpsList(corpsRes.scoreboard || []);
      setAgentsList(agentsRes.leaderboard || []);
    } catch (error) {
      console.error("Failed to fetch scoreboards:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [periodDays]);

  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab && tab !== activeTab) {
      setActiveTab(tab);
    }
  }, [searchParams, activeTab]);

  const tabs: TabItem[] = [
    { key: "corps", label: `Corps (${corpsList.length})` },
    { key: "agents", label: `Agents (${agentsList.length})` },
  ];

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

      {!loading && activeTab === "corps" && (
        <>
          <DataTable<CorpsScore & Record<string, unknown>>
            columns={[
              { key: "rank", label: "Rank", render: (v) => <span className={`standings-rank rank-${String(v)}`}>#{String(v)}</span> },
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
              { key: "efficiency_score", label: "Efficiency", render: (v) => `${Number(v).toFixed(1)}%` },
              { key: "completed_sessions", label: "Sessions", render: (_v, row) => `${row.completed_sessions}/${row.total_sessions}` },
              { key: "completed_reps", label: "Reps", render: (_v, row) => `${row.completed_reps}/${row.total_reps}` },
              { key: "composite_score", label: "Score", render: (v) => <span className="standings-score">{Number(v).toFixed(1)}</span> },
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
            { key: "rank", label: "Rank", render: (v) => <span className={`standings-rank rank-${String(v)}`}>#{String(v)}</span> },
            { key: "role", label: "Role", render: (v) => <span style={{ fontWeight: 600 }}>{formatRole(String(v))}</span> },
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
          emptyMessage="No agent data available"
        />
      )}
    </div>
  );
}

// Keep default export for backward compat with router
export default ScoreboardsPage;
