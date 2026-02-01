import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { Show, WorkLogEntry, SystemHealth } from "../types";
import * as v1 from "../services/v1";

function timeAgo(ts?: string): string {
  if (!ts) return "";
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 0) return "just now";
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

function formatRole(role: string): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

const MODE_LABELS: Record<string, string> = {
  design_room: "Design Room",
  show_mode: "Show Mode",
  rehearsal_mode: "Rehearsal",
  judging: "Judging",
  offseason_review: "Offseason Review",
};

export function CommandCenter() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [shows, setShows] = useState<Show[]>([]);
  const [workLog, setWorkLog] = useState<WorkLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cleanupMsg, setCleanupMsg] = useState<string | null>(null);
  const [cleaning, setCleaning] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [h, s, l] = await Promise.allSettled([
        v1.getSystemHealth(),
        v1.listDBShows(),
        v1.getGlobalWorkLog(30),
      ]);
      if (h.status === "fulfilled") setHealth(h.value);
      if (s.status === "fulfilled") setShows(s.value);
      if (l.status === "fulfilled") setWorkLog(l.value);

      const anyFailed = [h, s, l].some(r => r.status === "rejected");
      if (anyFailed) {
        const reasons = [h, s, l]
          .filter((r): r is PromiseRejectedResult => r.status === "rejected")
          .map(r => r.reason?.message || "Unknown error");
        setError(`Some data failed to load: ${reasons.join("; ")}`);
      } else {
        setError(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const iv = setInterval(refresh, 15000);
    return () => clearInterval(iv);
  }, [refresh]);

  if (loading) return <div className="page-loading">Loading Command Center...</div>;

  const activeShows = shows.filter(s => s.status === "active");

  return (
    <div className="command-center">
      <h1 className="page-title">Command Center</h1>

      {error && <div className="error-banner">{error}</div>}

      {/* System Vitals */}
      <div className="vitals-grid">
        <div className="vital-card">
          <span className="vital-value">{health?.active_corps ?? 0}</span>
          <span className="vital-label">Active Corps</span>
        </div>
        <div className="vital-card">
          <span className="vital-value">{health?.active_agents ?? 0}</span>
          <span className="vital-label">Agents on Field</span>
        </div>
        <div className="vital-card">
          <span className="vital-value">{health?.completed_reps ?? 0}/{health?.total_reps ?? 0}</span>
          <span className="vital-label">Reps Completed</span>
        </div>
        <div className="vital-card">
          <span className="vital-value">{health?.failed_reps ?? 0}</span>
          <span className="vital-label">Failed Reps</span>
        </div>
        <div className="vital-card">
          <span className="vital-value">{health?.stale_reps ?? 0}</span>
          <span className="vital-label">Stale Reps</span>
        </div>
        <div className="vital-card">
          <span className="vital-value">{((health?.failure_rate ?? 0) * 100).toFixed(1)}%</span>
          <span className="vital-label">Failure Rate</span>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8, gap: 8, alignItems: "center" }}>
        {cleanupMsg && <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{cleanupMsg}</span>}
        <button
          className="small"
          disabled={cleaning}
          onClick={async () => {
            setCleaning(true);
            setCleanupMsg(null);
            try {
              const r = await v1.adminCleanup();
              setCleanupMsg(`Cleaned: ${r.timed_out_sessions} stale sessions, ${r.disbanded_corps} orphan corps`);
              refresh();
            } catch (e: any) {
              setCleanupMsg(`Cleanup failed: ${e.message}`);
            } finally {
              setCleaning(false);
            }
          }}
        >
          {cleaning ? "Cleaning..." : "Clean Up Stale"}
        </button>
      </div>

      {/* Corps Status */}
      {health?.corps_summaries && health.corps_summaries.length > 0 && (
        <section className="cc-section">
          <h2>Corps on the Field</h2>
          <div className="corps-status-grid">
            {health.corps_summaries.map(c => (
              <div key={c.id} className="corps-status-card clickable" onClick={() => navigate(`/corps/${c.id}`)}>
                <div className="corps-status-header">
                  <span className="corps-status-name">{c.name}</span>
                  {c.mode && <span className={`badge mode-${c.mode}`}>{MODE_LABELS[c.mode] || c.mode}</span>}
                </div>
                <div className="corps-status-stats">
                  <span>{c.agents_active}/{c.agents_total} agents</span>
                  <span>{c.reps_completed}/{c.reps_total} reps</span>
                  {c.failures > 0 && <span className="text-danger">{c.failures} failures</span>}
                </div>
                {c.reps_total > 0 && (
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${(c.reps_completed / c.reps_total) * 100}%` }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Active Shows */}
      <section className="cc-section">
        <h2>Active Shows ({activeShows.length})</h2>
        {activeShows.length === 0 && <p className="empty">No active shows. Create and activate a show to begin.</p>}
        <div className="cc-table-wrap">
          <table className="cc-table">
            <thead>
              <tr>
                <th>Show</th>
                <th>Corps</th>
                <th>Progress</th>
                <th>Score</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {activeShows.map(s => (
                <tr key={s.id} className="clickable" onClick={() => s.corps_id && navigate(`/corps/${s.corps_id}`)}>
                  <td>{s.title}</td>
                  <td>{s.corps_name || "—"}</td>
                  <td>{s.reps_completed ?? 0}/{s.reps_total ?? 0}</td>
                  <td>{s.final_score != null ? s.final_score.toFixed(1) : "—"}</td>
                  <td>{timeAgo(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Recent Activity */}
      <section className="cc-section">
        <h2>Recent Activity</h2>
        {workLog.length === 0 && <p className="empty">No activity recorded yet.</p>}
        <div className="activity-list">
          {workLog.slice(0, 20).map(w => (
            <div key={w.id} className="activity-row">
              <span className="activity-type">{w.event_type}</span>
              <span className="activity-role">{w.nickname || formatRole(w.role)}</span>
              <span className="activity-detail">{w.details?.slice(0, 120)}</span>
              <span className="activity-time">{timeAgo(w.timestamp)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
