import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge } from "../ui";
import { formatStatus, slugToTitle } from "../utils/formatters";

export function TourDashboard() {
  const navigate = useNavigate();
  const [competitions, setCompetitions] = useState<v1.V1Competition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    const ac = new AbortController();
    setError(null);
    v1.listCompetitions(ac.signal)
      .then(setCompetitions)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load competitions"))
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [refreshToken]);

  const active = competitions.filter(c => c.status === "active" || c.status === "pending");
  const completed = competitions.filter(c => c.status === "completed" || c.status === "scored");

  if (loading) return <div className="page-loading">Loading tour dashboard...</div>;
  if (error) {
    return (
      <div className="page-error">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
      </div>
    );
  }

  return (
    <div className="page-content tour-dashboard">
      <div className="page-header">
        <h1 className="page-title">On Tour</h1>
      </div>

      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{competitions.length}</span>
          <span className="summary-label">Competitions</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{active.length}</span>
          <span className="summary-label">Active</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{completed.length}</span>
          <span className="summary-label">Completed</span>
        </div>
      </div>

      {active.length === 0 && completed.length === 0 && (
        <p className="empty">No competitions yet. Start a tour from the Season Workshop.</p>
      )}

      {active.length > 0 && (
        <div className="dash-section">
          <h2>Active Competitions</h2>
          <div className="competition-grid">
            {active.map(c => (
              <div
                key={c.competition_id}
                className="competition-card"
                onClick={() => navigate(`/tour/${c.competition_id}`)}
              >
                <h3 title={c.show_slug}>{slugToTitle(c.show_slug)}</h3>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                  <Badge variant="success">{formatStatus(c.status)}</Badge>
                  <span className="text-muted" title={c.season_id}>{slugToTitle(c.season_id)}</span>
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {c.corps_ids.length} corps competing
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {completed.length > 0 && (
        <div className="dash-section">
          <h2>Completed</h2>
          <div className="competition-grid">
            {completed.map(c => (
              <div
                key={c.competition_id}
                className="competition-card"
                onClick={() => navigate(`/tour/${c.competition_id}`)}
              >
                <h3 title={c.show_slug}>{slugToTitle(c.show_slug)}</h3>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <Badge variant="info">{formatStatus(c.status)}</Badge>
                  <span className="text-muted" title={c.season_id}>{slugToTitle(c.season_id)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
