import { useState, useEffect } from "react";
import type { CorpsPlacement } from "../types";
import * as api from "../services/api";

export function TheHistory({ corpsId }: { corpsId: string }) {
  const [history, setHistory] = useState<CorpsPlacement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCorpsHistory(corpsId)
      .then(setHistory)
      .catch(e => setError(e instanceof Error ? e.message : "Failed to load history"))
      .finally(() => setLoading(false));
  }, [corpsId]);

  if (loading) return <div className="tab-loading">Loading competition history...</div>;
  if (error) return <div className="tab-error">{error}</div>;

  if (history.length === 0) {
    return (
      <div className="tab-empty">
        <p>No competition history recorded yet.</p>
        <p className="text-muted">Run a contest to generate placement history.</p>
      </div>
    );
  }

  return (
    <div className="history-tab">
      <h3>Competition History</h3>
      <table className="cc-table">
        <thead>
          <tr>
            <th>Season</th>
            <th>Placement</th>
            <th>Final Score</th>
            <th>Show</th>
          </tr>
        </thead>
        <tbody>
          {history.map((h, i) => (
            <tr key={i}>
              <td>{h.season_id}</td>
              <td>
                <span className={`placement placement-${h.placement}`}>
                  #{h.placement}
                </span>
              </td>
              <td>{h.final_score.toFixed(2)}</td>
              <td className="text-muted">{h.notes?.replace("show:", "") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="history-summary">
        <span>Seasons: {history.length}</span>
        <span>Best: #{Math.min(...history.map(h => h.placement))}</span>
        <span>Avg Score: {(history.reduce((s, h) => s + h.final_score, 0) / history.length).toFixed(2)}</span>
      </div>
    </div>
  );
}
