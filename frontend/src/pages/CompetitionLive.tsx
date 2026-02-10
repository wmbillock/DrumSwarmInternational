import { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import * as v1 from "../services/v1";
import { Tabs, Badge, DataTable } from "../ui";
import type { TabItem } from "../ui";
import { formatCaption, slugToTitle } from "../utils/formatters";

const CAPTION_ORDER = ["brass", "percussion", "guard", "visual", "general_effect", "ensemble_technique"];

export function CompetitionLive() {
  const { competitionId } = useParams<{ competitionId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [standings, setStandings] = useState<v1.V1Standings | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "standings");
  const [error, setError] = useState("");
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    if (!competitionId) return;
    const ac = new AbortController();
    setLoading(true);
    setError("");
    v1.getScores(competitionId, ac.signal)
      .then(setStandings)
      .catch(e => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [competitionId, refreshToken]);

  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab && tab !== activeTab) {
      setActiveTab(tab);
    }
  }, [searchParams, activeTab]);

  const tabs: TabItem[] = [
    { key: "standings", label: "Standings" },
    { key: "scorecards", label: "Scorecards" },
    { key: "tapes", label: "Judges Tapes" },
    { key: "critique", label: "Critique" },
    { key: "recap", label: "Recap" },
  ];

  if (loading) return <div className="page-loading">Loading competition...</div>;
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
        <button className="back-btn" onClick={() => navigate("/tour")}>Back</button>
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          {standings?.show_slug ? slugToTitle(standings.show_slug) : competitionId}
        </h1>
        {standings && (
          <Badge variant="info" title={standings.season_id}>{slugToTitle(standings.season_id)}</Badge>
        )}
      </div>

      <Tabs
        items={tabs}
        active={activeTab}
        onChange={(tab) => {
          setActiveTab(tab);
          const next = new URLSearchParams(searchParams);
          next.set("tab", tab);
          setSearchParams(next, { replace: true });
        }}
      />

      {activeTab === "standings" && standings && (
        <div style={{ marginTop: 16 }}>
          <DataTable<v1.V1StandingEntry & Record<string, unknown>>
            columns={[
              { key: "rank", label: "Rank", render: (v) => <span className={`standings-rank rank-${String(v)}`}>{v}</span> },
              { key: "corps_id", label: "Corps", render: (_v, row) => (
                <span style={{ fontWeight: 600 }} title={row.corps_id}>
                  {row.display_name || `Corps • ${row.corps_id.slice(0, 8)}`}
                </span>
              ) },
              { key: "final_score", label: "Score", render: (v) => <span className="standings-score">{Number(v).toFixed(2)}</span> },
              { key: "caption_scores", label: "Captions", render: (v) => (
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                  {Object.entries((v as Record<string, number>) || {}).map(([cap, score]) => (
                    <span key={cap} className={`standings-caption caption-${cap}`}>
                      {cap}: {Number(score).toFixed(1)}
                    </span>
                  ))}
                </div>
              ) },
            ]}
            data={standings.results as (v1.V1StandingEntry & Record<string, unknown>)[]}
            emptyMessage="No standings yet."
          />
        </div>
      )}

      {activeTab === "scorecards" && standings && (
        <div style={{ marginTop: 16 }}>
          {standings.results.map(r => (
            <ScoreCard key={r.corps_id} competitionId={competitionId!} entry={r} />
          ))}
        </div>
      )}

      {activeTab === "tapes" && standings && competitionId && (
        <div style={{ marginTop: 16 }}>
          <JudgesTapesPanel competitionId={competitionId} results={standings.results} />
        </div>
      )}

      {activeTab === "critique" && standings && competitionId && (
        <div style={{ marginTop: 16 }}>
          <CritiquePanel competitionId={competitionId} results={standings.results} />
        </div>
      )}

      {activeTab === "recap" && competitionId && (
        <div style={{ marginTop: 16 }}>
          <RecapPanel competitionId={competitionId} />
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
        <h3 style={{ margin: 0 }} title={entry.corps_id}>
          {entry.display_name || `Corps • ${entry.corps_id.slice(0, 8)}`}
        </h3>
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

function JudgesTapesPanel({ competitionId, results }: { competitionId: string; results: v1.V1StandingEntry[] }) {
  const [selectedCorps, setSelectedCorps] = useState<string | null>(null);
  const [tape, setTape] = useState<v1.V1TapeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

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
    } catch { /* ignore */ }
  };

  if (results.length === 0) return <p className="text-muted">No results yet.</p>;

  return (
    <div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        {results.map(r => (
          <button
            key={r.corps_id}
            className={selectedCorps === r.corps_id ? "primary" : "secondary"}
            onClick={() => loadTape(r.corps_id)}
            style={{ fontSize: 12, padding: "4px 10px" }}
          >
            #{r.rank} {r.display_name || `Corps • ${r.corps_id.slice(0, 8)}`}
          </button>
        ))}
      </div>

      {loading && <p className="text-muted">Loading tape...</p>}

      {tape && !loading && (
        <div className="competition-card" style={{ padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Judges Tape</h3>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="secondary" style={{ fontSize: 11 }} onClick={() => handleExport(tape.corps_id)}>
                Export MD
              </button>
              <button className="secondary" style={{ fontSize: 11 }} onClick={() => navigate(`/critique/${competitionId}/${tape.corps_id}`)}>
                Start Critique
              </button>
            </div>
          </div>

          {tape.overall_assessment && (
            <div style={{ marginBottom: 16, padding: 12, background: "var(--surface-2, #1a1a2e)", borderRadius: 4 }}>
              <strong style={{ fontSize: 12 }}>Overall Assessment</strong>
              <p style={{ margin: "4px 0 0", fontSize: 13 }}>{tape.overall_assessment}</p>
            </div>
          )}

          <div style={{ display: "grid", gap: 8 }}>
            {Object.entries(tape.caption_feedbacks).map(([caption, info]) => (
              <div key={caption} style={{ padding: 10, border: "1px solid var(--border, #333)", borderRadius: 4 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <strong style={{ textTransform: "uppercase", fontSize: 11, letterSpacing: 1 }}>
                    {formatCaption(caption)}
                  </strong>
                  <span style={{ fontFamily: "var(--font-mono, monospace)", fontWeight: 700 }}>
                    {info.value.toFixed(1)}
                    {info.rep_score != null && info.perf_score != null && (
                      <span style={{ fontSize: 10, opacity: 0.7 }}>
                        {" "}(R:{info.rep_score.toFixed(0)} P:{info.perf_score.toFixed(0)})
                      </span>
                    )}
                  </span>
                </div>
                {info.feedback && <p style={{ margin: 0, fontSize: 12, opacity: 0.8 }}>{info.feedback}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CritiquePanel({ competitionId, results }: { competitionId: string; results: v1.V1StandingEntry[] }) {
  const [selectedCorps, setSelectedCorps] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const loadCritique = async (corpsId: string) => {
    setSelectedCorps(corpsId);
    setLoading(true);
    try {
      const result = await v1.exportTape(competitionId, corpsId);
      setMarkdown(result.markdown || "");
    } catch {
      setMarkdown("");
    } finally {
      setLoading(false);
    }
  };

  if (results.length === 0) return <p className="text-muted">No results yet.</p>;

  return (
    <div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        {results.map(r => (
          <button
            key={r.corps_id}
            className={selectedCorps === r.corps_id ? "primary" : "secondary"}
            onClick={() => loadCritique(r.corps_id)}
            style={{ fontSize: 12, padding: "4px 10px" }}
          >
            #{r.rank} {r.display_name || `Corps • ${r.corps_id.slice(0, 8)}`}
          </button>
        ))}
      </div>

      {loading && <p className="text-muted">Loading critique...</p>}

      {!loading && markdown && (
        <div className="competition-card" style={{ padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Critique Report</h3>
          </div>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, margin: 0 }}>{markdown}</pre>
        </div>
      )}

      {!loading && selectedCorps && !markdown && (
        <p className="text-muted">No critique available yet.</p>
      )}
    </div>
  );
}

function RecapPanel({ competitionId }: { competitionId: string }) {
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
      `${(import.meta as any).env?.VITE_API_URL || "http://localhost:4224"}/api/v1/competitions/${competitionId}/recap?format=csv`,
      "_blank"
    );
  };

  if (loading) return <p className="text-muted">Loading recap...</p>;
  if (rows.length === 0) return <p className="text-muted">No recap data available.</p>;

  const allCaptions = new Set<string>();
  rows.forEach(r => Object.keys(r.caption_scores).forEach(c => allCaptions.add(c)));
  const captions = CAPTION_ORDER.filter(c => allCaptions.has(c));
  const recapRows = rows.map(r => {
    const row: Record<string, unknown> = {
      rank: r.rank,
      corps: r.corps_name || "Unknown Corps",
      penalties: r.penalties_total,
      raw: r.raw_total,
      final: r.final_score,
    };
    captions.forEach(c => {
      const cs = r.caption_scores[c] || { rep: 0, perf: 0, tot: 0 };
      row[`${c}_rep`] = cs.rep;
      row[`${c}_perf`] = cs.perf;
      row[`${c}_tot`] = cs.tot;
    });
    return row;
  });

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <button className="secondary" style={{ fontSize: 12 }} onClick={handleCSV}>Download CSV</button>
      </div>
      <DataTable<Record<string, unknown>>
        columns={[
          { key: "rank", label: "Rank", render: (v) => <strong>{String(v)}</strong> },
          { key: "corps", label: "Corps" },
          ...captions.flatMap((c) => ([
            { key: `${c}_rep`, label: `${formatCaption(c)} R`, render: (v) => Number(v).toFixed(1) },
            { key: `${c}_perf`, label: `${formatCaption(c)} P`, render: (v) => Number(v).toFixed(1) },
            { key: `${c}_tot`, label: `${formatCaption(c)} T`, render: (v) => Number(v).toFixed(1) },
          ])),
          { key: "penalties", label: "Pen", render: (v) => Number(v).toFixed(1) },
          { key: "raw", label: "Raw", render: (v) => Number(v).toFixed(1) },
          { key: "final", label: "Final", render: (v) => <span className="standings-score">{Number(v).toFixed(1)}</span> },
        ]}
        data={recapRows}
        emptyMessage="No recap data available."
      />
    </div>
  );
}
