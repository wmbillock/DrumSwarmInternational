import { useState, useEffect } from "react";
import * as api from "../services/api";

function formatRole(role: string): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function timeAgo(ts?: string): string {
  if (!ts) return "";
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

const STATUS_LABELS: Record<string, string> = { active: "Active", retired: "Retired" };

function StatusBadge({ status }: { status: string }) {
  const label = STATUS_LABELS[status] || status;
  return <span className={`badge ${status}`}>{label}</span>;
}

export function Performers() {
  const [performers, setPerformers] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [ledger, setLedger] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    api.getPerformers().then(setPerformers).catch(() => setPerformers([]));
  }, []);

  const handleSelect = async (id: string) => {
    try {
      const [detail, led, st] = await Promise.all([
        api.getPerformer(id),
        api.getPerformerLedger(id).catch(() => []),
        api.getPerformerStats(id).catch(() => null),
      ]);
      setSelected(detail);
      setLedger(led);
      setStats(st);
    } catch { setSelected(null); }
  };

  const handleRetire = async (id: string) => {
    await api.retirePerformer(id);
    api.getPerformers().then(setPerformers);
    setSelected(null);
  };

  return (
    <div className="page-content">
      <h2>Performers</h2>
      <div className="table-wrapper">
        <table className="styled-table">
          <thead><tr><th>Name</th><th>Role</th><th>Trust</th><th>Status</th><th>Sessions</th></tr></thead>
          <tbody>
            {performers.map((p: any) => (
              <tr key={p.id} onClick={() => handleSelect(p.id)} className="clickable">
                <td className="cell-primary">{p.name || p.id.slice(0, 8)}</td>
                <td>{formatRole(p.role_type || "")}</td>
                <td><span className="trust-score">{p.trust_score ?? "-"}</span></td>
                <td><StatusBadge status={p.status || "active"} /></td>
                <td>{p.total_sessions ?? 0}</td>
              </tr>
            ))}
            {performers.length === 0 && <tr><td colSpan={5} className="dim">No performers yet.</td></tr>}
          </tbody>
        </table>
      </div>
      {selected && (
        <div className="detail-panel">
          <h3>{selected.name || selected.id.slice(0, 8)}</h3>
          <p className="dim" style={{ marginBottom: 8 }}>{formatRole(selected.role_type || "")}</p>
          <button className="small danger" onClick={() => handleRetire(selected.id)}>Retire</button>
          {stats && (
            <div className="stats-grid">
              <div><strong>Total Sessions</strong><span>{stats.total_sessions ?? 0}</span></div>
              <div><strong>Success Rate</strong><span>{stats.success_rate != null ? `${(stats.success_rate * 100).toFixed(0)}%` : "-"}</span></div>
              <div><strong>Avg Score</strong><span>{stats.avg_score != null ? stats.avg_score.toFixed(1) : "-"}</span></div>
            </div>
          )}
          {ledger.length > 0 && (
            <>
              <h4>Capability Ledger</h4>
              <div className="table-wrapper">
                <table>
                  <thead><tr><th>Capability</th><th>Level</th><th>Updated</th></tr></thead>
                  <tbody>
                    {ledger.map((entry: any, i: number) => (
                      <tr key={i}>
                        <td>{entry.capability || entry.tool_name || "-"}</td>
                        <td>{entry.level ?? entry.score ?? "-"}</td>
                        <td>{entry.updated_at ? timeAgo(entry.updated_at) : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
