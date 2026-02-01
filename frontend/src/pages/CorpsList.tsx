import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { CorpsWorkspace } from "../types";
import * as api from "../services/api";

const STATE_LABELS: Record<string, string> = {
  commissioned: "Commissioned",
  active: "Active",
  contending: "Contending",
  stagnant: "Stagnant",
  rebuilt: "Rebuilt",
  retired: "Retired",
};

export function CorpsList() {
  const navigate = useNavigate();
  const [corps, setCorps] = useState<CorpsWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCorpsWorkspaces()
      .then(setCorps)
      .catch(e => setError(e instanceof Error ? e.message : "Failed to load corps"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading Corps...</div>;

  return (
    <div className="corps-list-page">
      <h1 className="page-title">Corps</h1>

      {error && <div className="error-banner">{error}</div>}

      {corps.length === 0 && !error && (
        <p className="empty">No corps found. Initialize corps via the CLI to see them here.</p>
      )}

      {corps.length > 0 && (
        <div className="corps-card-grid">
          {corps.map(c => (
            <div key={c.corps_id} className="corps-list-card clickable" onClick={() => navigate(`/corps/${c.corps_id}`)}>
              <div className="corps-list-header">
                <span className="corps-list-name">{c.display_name}</span>
                <span className={`badge state-${c.state}`}>{STATE_LABELS[c.state] || c.state}</span>
              </div>
              {c.philosophy && <p className="corps-list-philosophy">{c.philosophy}</p>}
              <div className="corps-list-stats">
                <span>{c.roster_size} members</span>
                <span>{c.history.length} placements</span>
              </div>
              {c.history.length > 0 && (
                <div className="corps-list-best">
                  Best: #{Math.min(...c.history.map(h => h.placement))} ({Math.max(...c.history.map(h => h.final_score)).toFixed(1)} pts)
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
