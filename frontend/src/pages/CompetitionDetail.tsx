import { useEffect, useState, Fragment } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Panel, Tabs } from "../ui";
import * as v1 from "../services/v1";

const CAPTION_ORDER = ["brass", "percussion", "guard", "visual", "general_effect", "ensemble_technique"];

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
        <td>{entry.display_name || entry.corps_id}</td>
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
            <td>{r.display_name || r.corps_id}</td>
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
          {results.map((r) => <option key={r.corps_id} value={r.corps_id}>{r.display_name || r.corps_id}</option>)}
        </select>
        <span>vs</span>
        <select value={rightId} onChange={(e) => setRightId(e.target.value)}>
          {results.map((r) => <option key={r.corps_id} value={r.corps_id}>{r.display_name || r.corps_id}</option>)}
        </select>
      </div>
      {left && right && (
        <table className="data-table">
          <thead>
            <tr><th>Caption</th><th>{left.display_name || left.corps_id}</th><th>{right.display_name || right.corps_id}</th><th>Diff</th></tr>
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

function JudgesTapesTab({ competitionId, results }: { competitionId: string; results: v1.V1StandingEntry[] }) {
  const [selectedCorps, setSelectedCorps] = useState<string | null>(null);
  const [tape, setTape] = useState<v1.V1TapeDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const loadTape = (corpsId: string) => {
    setSelectedCorps(corpsId);
    setLoading(true);
    v1.getTape(competitionId, corpsId)
      .then(setTape)
      .catch(() => setTape(null))
      .finally(() => setLoading(false));
  };

  const handleExport = async (corpsId: string) => {
    try {
      const result = await v1.exportTape(competitionId, corpsId);
      const blob = new Blob([result.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tape_${corpsId.slice(0, 8)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  if (results.length === 0) return <p className="empty">No results — run competition first.</p>;

  return (
    <div className="tapes-tab">
      <div className="tapes-corps-list">
        {results.map((r) => (
          <button
            key={r.corps_id}
            className={`tape-corps-btn ${selectedCorps === r.corps_id ? "active" : ""}`}
            onClick={() => loadTape(r.corps_id)}
          >
            #{r.rank} {r.display_name || r.corps_id.slice(0, 8)}
          </button>
        ))}
      </div>

      {loading && <p className="text-muted">Loading tape...</p>}

      {tape && !loading && (
        <div className="tape-detail">
          <div className="tape-header">
            <h3>Judges Tape — {tape.corps_id.slice(0, 8)}</h3>
            <button className="secondary" onClick={() => handleExport(tape.corps_id)}>
              Export MD
            </button>
          </div>

          <div className="tape-assessment">
            <h4>Overall Assessment</h4>
            <p>{tape.overall_assessment}</p>
          </div>

          <div className="tape-captions">
            {Object.entries(tape.caption_feedbacks).map(([caption, info]) => (
              <div key={caption} className="tape-caption-card">
                <div className="tape-caption-header">
                  <strong>{caption.replace("_", " ").toUpperCase()}</strong>
                  <span className="tape-score">
                    {info.value.toFixed(1)}
                    {info.rep_score != null && info.perf_score != null && (
                      <span className="tape-rep-perf">
                        {" "}(R:{info.rep_score.toFixed(0)} P:{info.perf_score.toFixed(0)})
                      </span>
                    )}
                  </span>
                </div>
                {info.feedback && <p className="tape-feedback">{info.feedback}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RecapTab({ competitionId }: { competitionId: string }) {
  const [rows, setRows] = useState<v1.V1RecapRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    v1.getRecap(competitionId)
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [competitionId]);

  const handleCSV = () => {
    window.open(
      `${(import.meta as any).env?.VITE_API_URL || "http://localhost:8000"}/api/v1/competitions/${competitionId}/recap?format=csv`,
      "_blank"
    );
  };

  if (loading) return <p className="text-muted">Loading recap...</p>;
  if (rows.length === 0) return <p className="empty">No recap data.</p>;

  // Collect all captions
  const allCaptions = new Set<string>();
  rows.forEach((r) => Object.keys(r.caption_scores).forEach((c) => allCaptions.add(c)));
  const captions = CAPTION_ORDER.filter((c) => allCaptions.has(c));

  return (
    <div className="recap-tab">
      <div className="recap-actions">
        <button className="secondary" onClick={handleCSV}>Download CSV</button>
      </div>
      <div className="recap-table-wrapper">
        <table className="data-table recap-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Corps</th>
              {captions.map((c) => (
                <th key={c} colSpan={3}>{c.replace("_", " ")}</th>
              ))}
              <th>Pen</th>
              <th>Raw</th>
              <th>Final</th>
            </tr>
            <tr className="sub-header">
              <th></th>
              <th></th>
              {captions.map((c) => (
                <Fragment key={c}><th>R</th><th>P</th><th>T</th></Fragment>
              ))}
              <th></th>
              <th></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.corps_id}>
                <td><strong>#{r.rank}</strong></td>
                <td>{r.corps_name || r.corps_id.slice(0, 8)}</td>
                {captions.map((c) => {
                  const cs = r.caption_scores[c] || { rep: 0, perf: 0, tot: 0 };
                  return (
                    <Fragment key={c}><td>{cs.rep.toFixed(1)}</td><td>{cs.perf.toFixed(1)}</td><td>{cs.tot.toFixed(1)}</td></Fragment>
                  );
                })}
                <td>{r.penalties_total.toFixed(1)}</td>
                <td>{r.raw_total.toFixed(1)}</td>
                <td className="show-score">{r.final_score.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
            { key: "tapes", label: "Judges Tapes" },
            { key: "recap", label: "Recap" },
            { key: "compare", label: "Compare" },
          ]}
        />
        <div className="tab-content">
          {tab === "standings" && competitionId && (
            <StandingsTab competitionId={competitionId} results={results} />
          )}
          {tab === "captions" && <CaptionBreakdownTab results={results} />}
          {tab === "tapes" && competitionId && (
            <JudgesTapesTab competitionId={competitionId} results={results} />
          )}
          {tab === "recap" && competitionId && (
            <RecapTab competitionId={competitionId} />
          )}
          {tab === "compare" && results.length >= 2 && <CompareTab results={results} />}
          {tab === "compare" && results.length < 2 && (
            <p className="empty">Need at least 2 corps to compare.</p>
          )}
        </div>
      </Panel>
    </div>
  );
}
