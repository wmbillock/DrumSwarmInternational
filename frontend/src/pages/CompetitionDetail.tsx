import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Panel, Tabs } from "../ui";
import * as v1 from "../services/v1";

const CAPTION_ORDER = ["brass", "percussion", "guard", "visual", "general_effect"];

function CaptionBars({ scores }: { scores: Record<string, number> }) {
  return (
    <div className="caption-bars">
      {CAPTION_ORDER.map((cap) => {
        const val = scores[cap];
        if (val == null) return null;
        return (
          <div key={cap} className="caption-bar" title={`${cap}: ${val}`}>
            <div className="caption-bar-fill" style={{ width: `${val}%` }} />
          </div>
        );
      })}
    </div>
  );
}

function BreakdownRow({
  competitionId,
  entry,
}: {
  competitionId: string;
  entry: v1.V1StandingEntry;
}) {
  const [breakdown, setBreakdown] = useState<v1.V1CorpsBreakdown | null>(null);
  const [open, setOpen] = useState(false);

  const toggle = () => {
    if (!open && !breakdown) {
      v1.getCorpsBreakdown(competitionId, entry.corps_id)
        .then(setBreakdown)
        .catch(() => {});
    }
    setOpen(!open);
  };

  return (
    <>
      <tr className="clickable-row" onClick={toggle}>
        <td><strong>#{entry.rank}</strong></td>
        <td>{entry.corps_id}</td>
        <td className="show-score">{entry.final_score.toFixed(2)}</td>
        <td>{entry.raw_score.toFixed(2)}</td>
        <td><CaptionBars scores={entry.caption_scores} /></td>
      </tr>
      {open && (
        <tr className="breakdown-row">
          <td colSpan={5}>
            {breakdown ? (
              <div className="breakdown-detail">
                <table className="breakdown-table">
                  <thead>
                    <tr><th>Caption</th><th>Score</th><th>Weight</th><th>Weighted</th><th>Commentary</th></tr>
                  </thead>
                  <tbody>
                    {CAPTION_ORDER.map((cap) => {
                      const d = breakdown.caption_scores[cap];
                      if (!d) return null;
                      return (
                        <tr key={cap}>
                          <td>{cap}</td>
                          <td>{d.score}</td>
                          <td>{(d.weight * 100).toFixed(0)}%</td>
                          <td>{d.weighted.toFixed(2)}</td>
                          <td className="text-muted">{breakdown.commentary[cap]}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div className="breakdown-footer">
                  Penalties: {breakdown.penalties_total.toFixed(2)} | Final: {breakdown.final_score.toFixed(2)}
                </div>
              </div>
            ) : (
              <span className="text-muted">Loading breakdown...</span>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function StandingsTab({
  competitionId,
  results,
}: {
  competitionId: string;
  results: v1.V1StandingEntry[];
}) {
  if (results.length === 0) return <p className="empty">No standings yet.</p>;
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Rank</th><th>Corps</th><th>Score</th><th>Raw</th><th>Captions</th>
        </tr>
      </thead>
      <tbody>
        {results.map((r) => (
          <BreakdownRow key={r.corps_id} competitionId={competitionId} entry={r} />
        ))}
      </tbody>
    </table>
  );
}

function CaptionBreakdownTab({ results }: { results: v1.V1StandingEntry[] }) {
  if (results.length === 0) return <p className="empty">No data.</p>;
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Corps</th>
          {CAPTION_ORDER.map((c) => <th key={c}>{c}</th>)}
          <th>Final</th>
        </tr>
      </thead>
      <tbody>
        {results.map((r) => (
          <tr key={r.corps_id}>
            <td>{r.corps_id}</td>
            {CAPTION_ORDER.map((c) => (
              <td key={c}>{r.caption_scores[c]?.toFixed?.(1) ?? "—"}</td>
            ))}
            <td className="show-score">{r.final_score.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CompareTab({ results }: { results: v1.V1StandingEntry[] }) {
  const [leftId, setLeftId] = useState(results[0]?.corps_id ?? "");
  const [rightId, setRightId] = useState(results[1]?.corps_id ?? "");

  const left = results.find((r) => r.corps_id === leftId);
  const right = results.find((r) => r.corps_id === rightId);

  return (
    <div>
      <div className="compare-selectors">
        <select value={leftId} onChange={(e) => setLeftId(e.target.value)}>
          {results.map((r) => <option key={r.corps_id} value={r.corps_id}>{r.corps_id}</option>)}
        </select>
        <span>vs</span>
        <select value={rightId} onChange={(e) => setRightId(e.target.value)}>
          {results.map((r) => <option key={r.corps_id} value={r.corps_id}>{r.corps_id}</option>)}
        </select>
      </div>
      {left && right && (
        <table className="data-table">
          <thead>
            <tr><th>Caption</th><th>{left.corps_id}</th><th>{right.corps_id}</th><th>Diff</th></tr>
          </thead>
          <tbody>
            {CAPTION_ORDER.map((cap) => {
              const lv = left.caption_scores[cap] ?? 0;
              const rv = right.caption_scores[cap] ?? 0;
              const diff = lv - rv;
              return (
                <tr key={cap}>
                  <td>{cap}</td>
                  <td>{lv.toFixed(1)}</td>
                  <td>{rv.toFixed(1)}</td>
                  <td className={diff > 0 ? "text-success" : diff < 0 ? "text-danger" : ""}>
                    {diff > 0 ? "+" : ""}{diff.toFixed(1)}
                  </td>
                </tr>
              );
            })}
            <tr className="total-row">
              <td><strong>Final</strong></td>
              <td><strong>{left.final_score.toFixed(2)}</strong></td>
              <td><strong>{right.final_score.toFixed(2)}</strong></td>
              <td className={(left.final_score - right.final_score) > 0 ? "text-success" : "text-danger"}>
                <strong>
                  {(left.final_score - right.final_score) > 0 ? "+" : ""}
                  {(left.final_score - right.final_score).toFixed(2)}
                </strong>
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

export function CompetitionDetail() {
  const { competitionId } = useParams<{ competitionId: string }>();
  const navigate = useNavigate();
  const [scores, setScores] = useState<v1.V1Standings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState("standings");

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

  const results = scores?.results ?? [];

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

      <Panel title="Results">
        <Tabs
          active={tab}
          onChange={setTab}
          items={[
            { key: "standings", label: "Standings" },
            { key: "captions", label: "Caption Breakdown" },
            { key: "compare", label: "Compare" },
          ]}
        />
        <div className="tab-content">
          {tab === "standings" && competitionId && (
            <StandingsTab competitionId={competitionId} results={results} />
          )}
          {tab === "captions" && <CaptionBreakdownTab results={results} />}
          {tab === "compare" && results.length >= 2 && <CompareTab results={results} />}
          {tab === "compare" && results.length < 2 && (
            <p className="empty">Need at least 2 corps to compare.</p>
          )}
        </div>
      </Panel>
    </div>
  );
}
