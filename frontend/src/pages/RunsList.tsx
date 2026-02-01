import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { RunManifest } from "../types";
import * as api from "../services/api";

function timeAgo(ts?: string): string {
  if (!ts) return "";
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 0) return "just now";
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

function formatTimestamp(ts?: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function RunsList() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunManifest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getRuns()
      .then(setRuns)
      .catch(e => setError(e instanceof Error ? e.message : "Failed to load runs"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading Runs & Rehearsals...</div>;

  return (
    <div className="runs-page">
      <h1 className="page-title">Runs & Rehearsals</h1>

      {error && <div className="error-banner">{error}</div>}

      {runs.length === 0 && !error && (
        <p className="empty">No runs found. Execute a show run to see results here.</p>
      )}

      {runs.length > 0 && (
        <div className="cc-table-wrap">
          <table className="cc-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Show</th>
                <th>Corps</th>
                <th>Season</th>
                <th>Status</th>
                <th>Started</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(r => {
                let duration = "—";
                if (r.started_at && r.completed_at) {
                  const ms = new Date(r.completed_at).getTime() - new Date(r.started_at).getTime();
                  if (ms < 60000) duration = `${Math.round(ms / 1000)}s`;
                  else duration = `${Math.round(ms / 60000)}m`;
                }
                return (
                  <tr key={r.run_id} className="clickable" onClick={() => navigate(`/runs/${encodeURIComponent(r.run_id)}`)}>
                    <td className="mono">{r.run_id}</td>
                    <td>{r.show_slug}</td>
                    <td>{r.corps_id}</td>
                    <td>{r.season_id}</td>
                    <td><span className={`badge ${r.status}`}>{r.status}</span></td>
                    <td title={formatTimestamp(r.started_at)}>{timeAgo(r.started_at)}</td>
                    <td>{duration}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
