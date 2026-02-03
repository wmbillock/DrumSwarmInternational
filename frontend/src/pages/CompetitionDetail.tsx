import { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Panel, Tabs, DataTable } from "../ui";
import * as v1 from "../services/v1";
import { formatCaption, slugToTitle } from "../utils/formatters";

const CAPTION_ORDER = ["brass", "percussion", "guard", "visual", "general_effect", "ensemble_technique"];

function CaptionBars({ scores }: { scores: Record<string, number> }) {
  return (
    <div className="caption-bars">
      {CAPTION_ORDER.map((cap) => {
        const val = scores[cap];
        if (val == null) return null;
        return (
          <div key={cap} className="caption-bar" title={`${formatCaption(cap)}: ${val}`}>
            <div className="caption-bar-fill" style={{ width: `${val}%` }} />
          </div>
        );
      })}
    </div>
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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [breakdowns, setBreakdowns] = useState<Record<string, v1.V1CorpsBreakdown | null>>({});

  const handleSelect = async (entry: v1.V1StandingEntry) => {
    const nextId = entry.corps_id === selectedId ? null : entry.corps_id;
    setSelectedId(nextId);
    if (!nextId || breakdowns[nextId] !== undefined) return;
    setLoadingId(nextId);
    try {
      const breakdown = await v1.getCorpsBreakdown(competitionId, nextId);
      setBreakdowns(prev => ({ ...prev, [nextId]: breakdown }));
    } catch {
      setBreakdowns(prev => ({ ...prev, [nextId]: null }));
    } finally {
      setLoadingId(null);
    }
  };

  const selectedBreakdown = selectedId ? breakdowns[selectedId] : null;
  const breakdownRows = selectedBreakdown
    ? CAPTION_ORDER.map((cap) => {
        const d = selectedBreakdown.caption_scores[cap];
        if (!d) return null;
        return {
          caption: cap,
          score: d.score,
          weight: d.weight,
          weighted: d.weighted,
          commentary: selectedBreakdown.commentary[cap],
        };
      }).filter(Boolean) as Array<{ caption: string; score: number; weight: number; weighted: number; commentary?: string }>
    : [];

  return (
    <div>
      <DataTable<v1.V1StandingEntry & Record<string, unknown>>
        columns={[
          { key: "rank", label: "Rank", render: (v) => <strong>#{String(v)}</strong> },
          { key: "corps_id", label: "Corps", render: (_v, row) => (
            <span title={row.corps_id}>{row.display_name || `Corps • ${row.corps_id.slice(0, 8)}`}</span>
          ) },
          { key: "final_score", label: "Score", render: (v) => Number(v).toFixed(2) },
          { key: "raw_score", label: "Raw", render: (v) => Number(v).toFixed(2) },
          { key: "caption_scores", label: "Captions", render: (v) => <CaptionBars scores={v as Record<string, number>} /> },
        ]}
        data={results as (v1.V1StandingEntry & Record<string, unknown>)[]}
        onRowClick={handleSelect}
        emptyMessage="No standings yet."
      />
      {selectedId && (
        <div className="breakdown-detail" style={{ marginTop: 12 }}>
          {loadingId === selectedId && <span className="text-muted">Loading breakdown...</span>}
          {!loadingId && selectedBreakdown && (
            <>
              <DataTable<Record<string, unknown>>
                columns={[
                  { key: "caption", label: "Caption", render: (v) => formatCaption(String(v)) },
                  { key: "score", label: "Score", render: (v) => Number(v).toFixed(1) },
                  { key: "weight", label: "Weight", render: (v) => `${(Number(v) * 100).toFixed(0)}%` },
                  { key: "weighted", label: "Weighted", render: (v) => Number(v).toFixed(2) },
                  { key: "commentary", label: "Commentary", render: (v) => <span className="text-muted">{String(v ?? "")}</span> },
                ]}
                data={breakdownRows as Record<string, unknown>[]}
                emptyMessage="No breakdown data."
              />
              <div className="breakdown-footer">
                Penalties: {selectedBreakdown.penalties_total.toFixed(2)} | Final: {selectedBreakdown.final_score.toFixed(2)}
              </div>
            </>
          )}
          {!loadingId && !selectedBreakdown && <span className="text-muted">No breakdown available.</span>}
        </div>
      )}
    </div>
  );
}

function CaptionBreakdownTab({ results }: { results: v1.V1StandingEntry[] }) {
  if (results.length === 0) return <p className="empty">No data.</p>;
  const rows = results.map((r) => {
    const row: Record<string, unknown> = {
      corps: r.display_name || `Corps • ${r.corps_id.slice(0, 8)}`,
      final: r.final_score,
      corps_id: r.corps_id,
    };
    CAPTION_ORDER.forEach((c) => {
      row[c] = r.caption_scores[c];
    });
    return row;
  });
  return (
    <DataTable<Record<string, unknown>>
      columns={[
        { key: "corps", label: "Corps", render: (v, row) => <span title={String(row.corps_id)}>{String(v)}</span> },
        ...CAPTION_ORDER.map((c) => ({
          key: c,
          label: formatCaption(c),
          render: (v: unknown) => (typeof v === "number" ? v.toFixed(1) : "—"),
        })),
        { key: "final", label: "Final", render: (v) => <span className="show-score">{Number(v).toFixed(2)}</span> },
      ]}
      data={rows}
      emptyMessage="No data."
    />
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
          {results.map((r) => (
            <option key={r.corps_id} value={r.corps_id}>
              {r.display_name || `Corps • ${r.corps_id.slice(0, 8)}`}
            </option>
          ))}
        </select>
        <span>vs</span>
        <select value={rightId} onChange={(e) => setRightId(e.target.value)}>
          {results.map((r) => (
            <option key={r.corps_id} value={r.corps_id}>
              {r.display_name || `Corps • ${r.corps_id.slice(0, 8)}`}
            </option>
          ))}
        </select>
      </div>
      {left && right && (
        <DataTable<Record<string, unknown>>
          columns={[
            { key: "caption", label: "Caption", render: (v) => formatCaption(String(v)) },
            { key: "left", label: left.display_name || `Corps • ${left.corps_id.slice(0, 8)}` },
            { key: "right", label: right.display_name || `Corps • ${right.corps_id.slice(0, 8)}` },
            { key: "diff", label: "Diff", render: (v, row) => (
              <span className={(row as any).diffClass || ""}>{String(v)}</span>
            ) },
          ]}
          data={[
            ...CAPTION_ORDER.map((cap) => {
              const lv = left.caption_scores[cap] ?? 0;
              const rv = right.caption_scores[cap] ?? 0;
              const diff = lv - rv;
              return {
                caption: cap,
                left: lv.toFixed(1),
                right: rv.toFixed(1),
                diff: `${diff > 0 ? "+" : ""}${diff.toFixed(1)}`,
                diffClass: diff > 0 ? "text-success" : diff < 0 ? "text-danger" : "",
              };
            }),
            {
              caption: "final",
              left: left.final_score.toFixed(2),
              right: right.final_score.toFixed(2),
              diff: `${(left.final_score - right.final_score) > 0 ? "+" : ""}${(left.final_score - right.final_score).toFixed(2)}`,
              diffClass: (left.final_score - right.final_score) > 0 ? "text-success" : "text-danger",
            },
          ]}
          emptyMessage="No comparison data."
        />
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
            #{r.rank} {r.display_name || `Corps • ${r.corps_id.slice(0, 8)}`}
          </button>
        ))}
      </div>

      {loading && <p className="text-muted">Loading tape...</p>}

      {tape && !loading && (
        <div className="tape-detail">
          <div className="tape-header">
            <h3 title={tape.corps_id}>Judges Tape — Corps • {tape.corps_id.slice(0, 8)}</h3>
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
                  <strong>{formatCaption(caption)}</strong>
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
  const recapRows = rows.map((r) => {
    const row: Record<string, unknown> = {
      rank: r.rank,
      corps: r.corps_name || `Corps • ${r.corps_id.slice(0, 8)}`,
      corps_id: r.corps_id,
      penalties: r.penalties_total,
      raw: r.raw_total,
      final: r.final_score,
    };
    captions.forEach((c) => {
      const cs = r.caption_scores[c] || { rep: 0, perf: 0, tot: 0 };
      row[`${c}_rep`] = cs.rep;
      row[`${c}_perf`] = cs.perf;
      row[`${c}_tot`] = cs.tot;
    });
    return row;
  });

  return (
    <div className="recap-tab">
      <div className="recap-actions">
        <button className="secondary" onClick={handleCSV}>Download CSV</button>
      </div>
      <DataTable<Record<string, unknown>>
        columns={[
          { key: "rank", label: "Rank", render: (v) => <strong>#{String(v)}</strong> },
          { key: "corps", label: "Corps", render: (v, row) => <span title={String(row.corps_id)}>{String(v)}</span> },
          ...captions.flatMap((c) => ([
            { key: `${c}_rep`, label: `${formatCaption(c)} R`, render: (v: unknown) => Number(v).toFixed(1) },
            { key: `${c}_perf`, label: `${formatCaption(c)} P`, render: (v: unknown) => Number(v).toFixed(1) },
            { key: `${c}_tot`, label: `${formatCaption(c)} T`, render: (v: unknown) => Number(v).toFixed(1) },
          ])),
          { key: "penalties", label: "Pen", render: (v) => Number(v).toFixed(1) },
          { key: "raw", label: "Raw", render: (v) => Number(v).toFixed(1) },
          { key: "final", label: "Final", render: (v) => <span className="show-score">{Number(v).toFixed(1)}</span> },
        ]}
        data={recapRows}
        emptyMessage="No recap data."
      />
    </div>
  );
}

export function CompetitionDetail() {
  const { competitionId } = useParams<{ competitionId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [scores, setScores] = useState<v1.V1Standings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState(searchParams.get("tab") || "standings");
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    if (!competitionId) return;
    const ac = new AbortController();
    setLoading(true);
    setError("");
    v1.getScores(competitionId, ac.signal)
      .then(setScores)
      .catch((e) => {
        if (e.name !== "AbortError" && !(e instanceof v1.ApiError && e.status === 404)) {
          setError(e.message);
        }
      })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [competitionId, refreshToken]);

  useEffect(() => {
    const nextTab = searchParams.get("tab");
    if (nextTab && nextTab !== tab) {
      setTab(nextTab);
    }
  }, [searchParams, tab]);

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
        <h2>{scores?.show_slug ? slugToTitle(scores.show_slug) : competitionId}</h2>
        <button className="primary" onClick={handleRun} disabled={running}>
          {running ? "Running..." : "Run Competition"}
        </button>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
        </div>
      )}

      <Panel title="Results">
        <Tabs
          active={tab}
          onChange={(next) => {
            setTab(next);
            const params = new URLSearchParams(searchParams);
            params.set("tab", next);
            setSearchParams(params, { replace: true });
          }}
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
