/**
 * Scoreboards Page — Rankings and leaderboards for corps and agents.
 */

import { useState, useEffect } from "react";
import { Tabs, Badge } from "../ui";
import type { TabItem } from "../ui";
import {
  getCorpsScoreboard,
  getAgentLeaderboard,
  CorpsScore,
  AgentLeaderEntry,
} from "../services/v1";

export function ScoreboardsPage() {
  const [corpsList, setCorpsList] = useState<CorpsScore[]>([]);
  const [agentsList, setAgentsList] = useState<AgentLeaderEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState(7);
  const [activeTab, setActiveTab] = useState("corps");
  const [selectedCorps, setSelectedCorps] = useState<CorpsScore | null>(null);

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

  const tabs: TabItem[] = [
    { key: "corps", label: `Corps (${corpsList.length})` },
    { key: "agents", label: `Agents (${agentsList.length})` },
  ];

  return (
    <div className="page-content">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 className="page-title">Scoreboards</h2>
        <div style={{ display: "flex", gap: 8 }}>
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

      <Tabs items={tabs} active={activeTab} onChange={setActiveTab} />

      {loading && <div className="page-loading">Loading...</div>}

      {!loading && activeTab === "corps" && (
        <>
          <table className="standings-table" style={{ marginTop: 16 }}>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Corps</th>
                <th>Status</th>
                <th>Completion</th>
                <th>Efficiency</th>
                <th>Sessions</th>
                <th>Reps</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {corpsList.length === 0 && (
                <tr><td colSpan={8} className="empty">No corps data available</td></tr>
              )}
              {corpsList.map(c => (
                <tr key={c.corps_id} className="clickable" onClick={() => setSelectedCorps(selectedCorps?.corps_id === c.corps_id ? null : c)}>
                  <td><span className={`standings-rank rank-${c.rank}`}>#{c.rank}</span></td>
                  <td style={{ fontWeight: 600 }}>{c.corps_name}</td>
                  <td><Badge variant={c.corps_status === "on_tour" ? "success" : "default"}>{c.corps_status.replace(/_/g, " ")}</Badge></td>
                  <td>
                    <div className="progress-bar" style={{ width: 80 }}>
                      <div className="progress-fill" style={{ width: `${Math.round(c.completion_score)}%` }} />
                    </div>
                    <span style={{ fontSize: 11, marginLeft: 4 }}>{Math.round(c.completion_score)}%</span>
                  </td>
                  <td>{c.efficiency_score.toFixed(1)}%</td>
                  <td>{c.completed_sessions}/{c.total_sessions}</td>
                  <td>{c.completed_reps}/{c.total_reps}</td>
                  <td><span className="standings-score">{c.composite_score.toFixed(1)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>

          {selectedCorps && (
            <div className="competition-card" style={{ marginTop: 16 }}>
              <h3 style={{ marginBottom: 12 }}>{selectedCorps.corps_name} — Performance Breakdown</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 12 }}>
                <div className="vital-card">
                  <span className="vital-value">#{selectedCorps.rank}</span>
                  <span className="vital-label">Rank</span>
                </div>
                <div className="vital-card">
                  <span className="vital-value" style={{ color: "var(--accent)" }}>{selectedCorps.composite_score.toFixed(1)}</span>
                  <span className="vital-label">Composite</span>
                </div>
                <div className="vital-card">
                  <span className="vital-value">{Math.round(selectedCorps.completion_score)}%</span>
                  <span className="vital-label">Completion</span>
                </div>
                <div className="vital-card">
                  <span className="vital-value">{Math.round(selectedCorps.efficiency_score)}%</span>
                  <span className="vital-label">Efficiency</span>
                </div>
                <div className="vital-card">
                  <span className="vital-value">{selectedCorps.completed_sessions}</span>
                  <span className="vital-label">Sessions Done</span>
                </div>
                <div className="vital-card">
                  <span className="vital-value" style={{ color: selectedCorps.failed_sessions > 0 ? "var(--danger)" : undefined }}>{selectedCorps.failed_sessions}</span>
                  <span className="vital-label">Failed</span>
                </div>
              </div>
              <button className="small" style={{ marginTop: 12 }} onClick={() => setSelectedCorps(null)}>Close</button>
            </div>
          )}
        </>
      )}

      {!loading && activeTab === "agents" && (
        <table className="standings-table" style={{ marginTop: 16 }}>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Role</th>
              <th>Nickname</th>
              <th>Sessions</th>
              <th>Completed</th>
              <th>Failed</th>
              <th>Success Rate</th>
            </tr>
          </thead>
          <tbody>
            {agentsList.length === 0 && (
              <tr><td colSpan={7} className="empty">No agent data available</td></tr>
            )}
            {agentsList.map(a => (
              <tr key={`${a.role}-${a.corps_id}`}>
                <td><span className={`standings-rank rank-${a.rank}`}>#{a.rank}</span></td>
                <td style={{ fontWeight: 600 }}>{a.role.replace(/_/g, " ")}</td>
                <td>{a.nickname}</td>
                <td>{a.total_sessions}</td>
                <td>{a.completed_sessions}</td>
                <td style={{ color: a.failed_sessions > 0 ? "var(--danger)" : undefined }}>{a.failed_sessions}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div className="progress-bar" style={{ width: 80 }}>
                      <div className="progress-fill" style={{
                        width: `${Math.round(a.success_rate)}%`,
                        background: a.success_rate >= 80 ? "var(--success)" : a.success_rate >= 50 ? "var(--warning)" : "var(--danger)",
                      }} />
                    </div>
                    <span>{Math.round(a.success_rate)}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// Keep default export for backward compat with router
export default ScoreboardsPage;
