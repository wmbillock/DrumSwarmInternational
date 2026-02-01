import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Panel, DataTable, Badge } from "../ui";
import * as v1 from "../services/v1";

export function CompetitionDetail() {
  const { competitionId } = useParams<{ competitionId: string }>();
  const navigate = useNavigate();
  const [scores, setScores] = useState<v1.V1Standings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!competitionId) return;
    const ac = new AbortController();
    v1.getScores(competitionId, ac.signal)
      .then(setScores)
      .catch((e) => {
        if (e.name !== "AbortError" && !(e instanceof v1.ApiError && e.status === 404)) {
          setError(e.message);
        }
      })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [competitionId]);

  const handleRun = async () => {
    if (!competitionId) return;
    setRunning(true);
    try {
      const result = await v1.runCompetition(competitionId);
      setScores({
        competition_id: competitionId,
        season_id: competitionId.split("-")[0] || "",
        show_slug: competitionId.split("-").slice(1).join("-"),
        generated_at: new Date().toISOString(),
        results: result.standings,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <div className="page-loading">Loading competition...</div>;

  return (
    <div className="page-content">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate("/competitions")}>Back</button>
        <h2>{competitionId}</h2>
        <button className="primary" onClick={handleRun} disabled={running}>
          {running ? "Running..." : "Run Competition"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {scores ? (
        <Panel title="Standings">
          <DataTable<v1.V1StandingEntry & Record<string, unknown>>
            columns={[
              { key: "rank", label: "Rank", render: (v) => <strong>#{String(v)}</strong> },
              { key: "corps_id", label: "Corps" },
              {
                key: "final_score",
                label: "Score",
                render: (v) => <span className="show-score">{Number(v).toFixed(2)}</span>,
              },
              { key: "raw_score", label: "Raw", render: (v) => Number(v).toFixed(2) },
            ]}
            data={scores.results as (v1.V1StandingEntry & Record<string, unknown>)[]}
            emptyMessage="No standings yet"
          />
        </Panel>
      ) : (
        <Panel title="Standings">
          <p className="empty">No scores yet. Run the competition to generate standings.</p>
        </Panel>
      )}
    </div>
  );
}
