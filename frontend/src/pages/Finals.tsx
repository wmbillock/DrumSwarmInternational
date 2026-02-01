import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge } from "../ui";

export function Finals() {
  const navigate = useNavigate();
  const [seasons, setSeasons] = useState<v1.V1Season[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ac = new AbortController();
    v1.listSeasons(ac.signal)
      .then(setSeasons)
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, []);

  if (loading) return <div className="page-loading">Loading finals...</div>;

  const completedSeasons = seasons.filter(s => {
    const status = (s.metadata as Record<string, unknown>)?.status as string;
    return status === "completed" || status === "touring" || status === "review";
  });
  const allSeasons = seasons;

  return (
    <div className="finals-page">
      <h1 className="page-title">Finals</h1>

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
          const status = (s.metadata as Record<string, unknown>)?.status as string || "unknown";
          return (
            <div
              key={s.season_id}
              className="competition-card"
              onClick={() => navigate(`/finals/${s.season_id}`)}
            >
              <h3>{s.season_id}</h3>
              <Badge variant={
                status === "completed" ? "success"
                : status === "touring" ? "warning"
                : "default"
              }>{status}</Badge>
            </div>
          );
        })}
      </div>
    </div>
  );
}
