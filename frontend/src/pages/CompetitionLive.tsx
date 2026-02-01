import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Tabs, Badge } from "../ui";
import type { TabItem } from "../ui";

export function CompetitionLive() {
  const { competitionId } = useParams<{ competitionId: string }>();
  const navigate = useNavigate();
  const [standings, setStandings] = useState<v1.V1Standings | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("standings");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!competitionId) return;
    const ac = new AbortController();
    v1.getScores(competitionId, ac.signal)
      .then(setStandings)
      .catch(e => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [competitionId]);

  const tabs: TabItem[] = [
    { key: "standings", label: "Standings" },
    { key: "scorecards", label: "Scorecards" },
  ];

  if (loading) return <div className="page-loading">Loading competition...</div>;
  if (error) return <div className="page-error"><div className="error-banner">{error}</div></div>;

  return (
    <div className="tour-dashboard">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate("/tour")}>Back</button>
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          {standings?.show_slug || competitionId}
        </h1>
        {standings && (
          <Badge variant="info">{standings.season_id}</Badge>
        )}
      </div>

      <Tabs items={tabs} active={activeTab} onChange={setActiveTab} />

      {activeTab === "standings" && standings && (
        <div style={{ marginTop: 16 }}>
          <table className="standings-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Corps</th>
                <th>Score</th>
                <th>Captions</th>
              </tr>
            </thead>
            <tbody>
              {standings.results.map(r => (
                <tr key={r.corps_id}>
                  <td>
                    <span className={`standings-rank rank-${r.rank}`}>{r.rank}</span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{r.display_name || r.corps_id}</td>
                  <td><span className="standings-score">{r.final_score.toFixed(2)}</span></td>
                  <td>
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                      {Object.entries(r.caption_scores || {}).map(([cap, score]) => (
                        <span key={cap} className={`standings-caption caption-${cap}`}>
                          {cap}: {(score as number).toFixed(1)}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "scorecards" && standings && (
        <div style={{ marginTop: 16 }}>
          {standings.results.map(r => (
            <ScoreCard key={r.corps_id} competitionId={competitionId!} entry={r} />
          ))}
        </div>
      )}
    </div>
  );
}

function ScoreCard({ competitionId, entry }: { competitionId: string; entry: v1.V1StandingEntry }) {
  const [breakdown, setBreakdown] = useState<v1.V1CorpsBreakdown | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open || breakdown) return;
    v1.getCorpsBreakdown(competitionId, entry.corps_id)
      .then(setBreakdown)
      .catch(() => {});
  }, [open, competitionId, entry.corps_id, breakdown]);

  return (
    <div
      className="competition-card"
      style={{ marginBottom: 12, cursor: "pointer" }}
      onClick={() => setOpen(!open)}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>{entry.display_name || entry.corps_id}</h3>
        <span className="standings-score">{entry.final_score.toFixed(2)}</span>
      </div>
      {open && breakdown && (
        <div style={{ marginTop: 12 }}>
          {Object.entries(breakdown.caption_scores).map(([cap, data]) => (
            <div key={cap} style={{ display: "flex", gap: 12, fontSize: 12, padding: "4px 0" }}>
              <span className={`caption-${cap}`} style={{ width: 100, fontWeight: 600 }}>{cap}</span>
              <span>Score: {data.score.toFixed(1)}</span>
              <span className="text-muted">Weight: {data.weight}</span>
              <span>Weighted: {data.weighted.toFixed(2)}</span>
            </div>
          ))}
          {breakdown.penalties_total > 0 && (
            <div style={{ color: "var(--danger)", fontSize: 12, marginTop: 4 }}>
              Penalties: -{breakdown.penalties_total.toFixed(2)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
