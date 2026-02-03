import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge } from "../ui";
import { formatStatus, slugToTitle } from "../utils/formatters";

export function Finals() {
  const navigate = useNavigate();
  const [seasons, setSeasons] = useState<v1.V1Season[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    const ac = new AbortController();
    setError(null);
    v1.listSeasons(ac.signal)
      .then(setSeasons)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load seasons"))
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [refreshToken]);

  if (loading) return <div className="page-loading">Loading finals...</div>;
  if (error) {
    return (
      <div className="page-error">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
      </div>
    );
  }

  const completedSeasons = seasons.filter(s => {
    const status = (s.metadata as Record<string, unknown>)?.status as string;
    return status === "completed" || status === "touring" || status === "review";
  });
  const allSeasons = seasons;

  return (
    <div className="page-content finals-page">
      <div className="page-header">
        <h1 className="page-title">Finals</h1>
      </div>

      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{allSeasons.length}</span>
          <span className="summary-label">Total Seasons</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{completedSeasons.length}</span>
          <span className="summary-label">Awaiting Review</span>
        </div>
      </div>

      {allSeasons.length === 0 && (
        <p className="empty">No seasons to review. Complete a tour first.</p>
      )}

      <div className="competition-grid">
        {allSeasons.map(s => {
          const status = (s.metadata as Record<string, unknown>)?.status as string || "planning";
          return (
            <div
              key={s.season_id}
              className="competition-card"
              onClick={() => navigate(`/finals/${s.season_id}`)}
            >
              <h3 title={s.season_id}>{slugToTitle(s.season_id)}</h3>
              <Badge variant={status === "completed" ? "success" : status === "touring" ? "warning" : "default"}>
                {formatStatus(status)}
              </Badge>
            </div>
          );
        })}
      </div>
    </div>
  );
}
