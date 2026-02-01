import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge } from "../ui";

export function SeasonReview() {
  const { seasonId } = useParams<{ seasonId: string }>();
  const navigate = useNavigate();
  const [season, setSeason] = useState<(v1.V1Season & { registered_corps?: string[] }) | null>(null);
  const [competitions, setCompetitions] = useState<v1.V1Competition[]>([]);
  const [selectedShow, setSelectedShow] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!seasonId) return;
    const ac = new AbortController();
    Promise.allSettled([
      v1.getSeason(seasonId, ac.signal),
      v1.listCompetitions(ac.signal),
    ]).then(([sRes, cRes]) => {
      if (sRes.status === "fulfilled") setSeason(sRes.value);
      if (cRes.status === "fulfilled") {
        setCompetitions(cRes.value.filter(c => c.season_id === seasonId));
      }
      setLoading(false);
    });
    return () => ac.abort();
  }, [seasonId]);

  if (loading) return <div className="page-loading">Loading season review...</div>;
  if (!season) return <div className="page-error"><div className="error-banner">Season not found</div></div>;

  const shows = [...new Set(competitions.map(c => c.show_slug))];

  return (
    <div className="finals-page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate("/finals")}>Back</button>
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          Season Review: {seasonId}
        </h1>
      </div>

      <div className="review-layout">
        <div className="review-list">
          <div className="side-nav-section-label">SHOWS</div>
          {shows.length === 0 && <p className="empty">No shows in this season</p>}
          {shows.map(slug => (
            <div
              key={slug}
              className={`review-item ${selectedShow === slug ? "selected" : ""}`}
              onClick={() => setSelectedShow(slug)}
            >
              <span>{slug.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</span>
              <Badge variant="default">pending</Badge>
            </div>
          ))}
        </div>

        <div className="review-detail">
          {!selectedShow && (
            <p className="empty">Select a show to review its deliverables.</p>
          )}
          {selectedShow && (
            <>
              <h2 style={{ fontFamily: "var(--font-display)", marginBottom: 16 }}>
                {selectedShow.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
              </h2>

              <div className="dash-section">
                <h3 style={{ fontSize: 14, marginBottom: 8 }}>Competition Results</h3>
                {competitions
                  .filter(c => c.show_slug === selectedShow)
                  .map(c => (
                    <div key={c.competition_id} style={{ marginBottom: 8 }}>
                      <Badge variant={c.status === "scored" || c.status === "completed" ? "success" : "default"}>
                        {c.status}
                      </Badge>
                      <span className="text-muted" style={{ marginLeft: 8 }}>
                        {c.corps_ids.length} corps
                      </span>
                    </div>
                  ))
                }
              </div>

              <div className="review-actions">
                <button className="accept">Accept Deliverable</button>
                <button className="reject">Reject &amp; Reschedule</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
