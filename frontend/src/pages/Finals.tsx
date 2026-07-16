import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge, DataTable, Panel } from "../ui";
import { formatStatus, slugToTitle } from "../utils/formatters";

function CorpsArtifactCard({ seasonId, corpsId, displayName }: {
  seasonId: string;
  corpsId: string;
  displayName: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [review, setReview] = useState<v1.V1ArtifactReview | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    if (review || loading) return;
    setLoading(true);
    v1.getCorpsArtifactReview(seasonId, corpsId)
      .then(setReview)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [seasonId, corpsId, review, loading]);

  const toggle = () => {
    setExpanded(prev => !prev);
    if (!expanded) load();
  };

  const reps = review?.reps;
  const completedPct = reps && reps.total > 0
    ? Math.round((reps.completed / reps.total) * 100)
    : 0;

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
      <div
        onClick={toggle}
        style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "10px 14px", cursor: "pointer",
          background: expanded ? "var(--bg-secondary, #f8f9fa)" : "transparent",
        }}
      >
        <div style={{ fontWeight: 600 }}>{displayName}</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {review && reps && (
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {reps.completed}/{reps.total} reps ({completedPct}%)
            </span>
          )}
          <span style={{ fontSize: 12, opacity: 0.5 }}>{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ padding: "0 14px 14px" }}>
          {loading && <p className="text-muted" style={{ fontSize: 13 }}>Loading artifacts...</p>}
          {review && (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* Rep Status Summary */}
              {reps && reps.total > 0 && (
                <div>
                  <h5 style={{ margin: "0 0 6px", fontSize: 13 }}>Reps</h5>
                  <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                    <Badge variant="default">{reps.pending} pending</Badge>
                    <Badge variant="warning">{reps.in_progress} in-progress</Badge>
                    <Badge variant="success">{reps.completed} completed</Badge>
                    {reps.failed > 0 && <Badge variant="error">{reps.failed} failed</Badge>}
                  </div>
                  {/* Progress bar */}
                  <div style={{ marginTop: 6, background: "var(--border)", borderRadius: 4, height: 6, overflow: "hidden" }}>
                    <div style={{ width: `${completedPct}%`, height: "100%", background: "var(--color-success, #22c55e)", transition: "width 0.3s" }} />
                  </div>
                </div>
              )}
              {reps && reps.total === 0 && (
                <p className="text-muted" style={{ fontSize: 13 }}>No reps created yet.</p>
              )}

              {/* Completed Rep Results */}
              {reps && reps.items.filter(r => r.status === "completed" && r.result).length > 0 && (
                <div>
                  <h5 style={{ margin: "0 0 6px", fontSize: 13 }}>Completed Work</h5>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    {reps.items.filter(r => r.status === "completed" && r.result).slice(0, 10).map(r => (
                      <div key={r.id} style={{ fontSize: 12, padding: "4px 8px", background: "var(--bg-secondary, #f8f9fa)", borderRadius: 4, borderLeft: "3px solid var(--color-success, #22c55e)" }}>
                        {r.result}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Segment Tree */}
              {review.segment_tree.length > 0 && (
                <div>
                  <h5 style={{ margin: "0 0 6px", fontSize: 13 }}>Segment Tree ({review.segment_tree.length} nodes)</h5>
                  <div style={{ fontSize: 12, maxHeight: 200, overflow: "auto" }}>
                    {review.segment_tree.slice(0, 20).map(seg => (
                      <div key={seg.id} style={{ display: "flex", gap: 8, alignItems: "center", padding: "2px 0" }}>
                        <Badge variant={seg.status === "completed" ? "success" : seg.status === "in_progress" ? "warning" : "default"}>
                          {seg.status}
                        </Badge>
                        <span>{seg.title}</span>
                        {seg.caption && <span className="text-muted">({seg.caption})</span>}
                      </div>
                    ))}
                    {review.segment_tree.length > 20 && (
                      <p className="text-muted">...and {review.segment_tree.length - 20} more</p>
                    )}
                  </div>
                </div>
              )}

              {/* Artifacts */}
              {review.artifacts.length > 0 && (
                <div>
                  <h5 style={{ margin: "0 0 6px", fontSize: 13 }}>Artifacts ({review.artifacts.length})</h5>
                  <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 2 }}>
                    {review.artifacts.slice(0, 10).map(a => (
                      <div key={a.id} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <Badge variant="default">{a.artifact_type}</Badge>
                        <span style={{ fontFamily: "monospace" }}>{a.file_path.split("/").pop()}</span>
                        {a.label && <span className="text-muted">— {a.label}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Score History */}
              {review.score_history.length > 0 && (
                <div>
                  <h5 style={{ margin: "0 0 6px", fontSize: 13 }}>Score History</h5>
                  <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 2 }}>
                    {review.score_history.map((sc, i) => (
                      <div key={i} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <span style={{ fontFamily: "monospace" }}>{(sc as Record<string, string>).source_file}</span>
                        {(sc as Record<string, number>).final_score != null && (
                          <Badge variant="success">Score: {Number((sc as Record<string, number>).final_score).toFixed(1)}</Badge>
                        )}
                        {(sc as Record<string, string>).type === "critique" && (
                          <Badge variant="default">Critique Round {(sc as Record<string, string>).round}</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Spec Completion */}
              {review.spec_completion && review.spec_completion.deliverables_total > 0 && (
                <div>
                  <h5 style={{ margin: "0 0 6px", fontSize: 13 }}>
                    Spec Completion: {review.spec_completion.completion_pct}%
                    ({review.spec_completion.deliverables_met}/{review.spec_completion.deliverables_total})
                  </h5>
                  <div style={{ marginBottom: 4, background: "var(--border)", borderRadius: 4, height: 6, overflow: "hidden" }}>
                    <div style={{
                      width: `${review.spec_completion.completion_pct}%`,
                      height: "100%",
                      background: review.spec_completion.completion_pct >= 60 ? "var(--color-success, #22c55e)" : "var(--color-warning, #f59e0b)",
                      transition: "width 0.3s",
                    }} />
                  </div>
                  <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 2 }}>
                    {review.spec_completion.details.map((d, i) => (
                      <div key={i} style={{ display: "flex", gap: 6, alignItems: "center" }}>
                        <span>{d.status === "met" ? "✓" : "✗"}</span>
                        <span style={{ opacity: d.status === "met" ? 1 : 0.6 }}>{d.deliverable}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          {!loading && !review && <p className="text-muted" style={{ fontSize: 13 }}>Failed to load artifact data.</p>}
        </div>
      )}
    </div>
  );
}

function ArtifactReviewPanel({ seasonId, overallRows, corpsById }: {
  seasonId: string;
  overallRows: v1.V1FinalsStandingRow[];
  corpsById: Record<string, v1.V1Corps>;
}) {
  return (
    <Panel title="Artifact Review" style={{ marginTop: 16 }}>
      {overallRows.length === 0 && <p className="empty">No corps to review yet.</p>}
      {overallRows.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {overallRows.map(row => (
            <CorpsArtifactCard
              key={row.corps_id}
              seasonId={seasonId}
              corpsId={row.corps_id}
              displayName={
                (row as Record<string, unknown>).display_name as string ||
                corpsById[row.corps_id]?.display_name ||
                `Corps • ${row.corps_id.slice(0, 8)}`
              }
            />
          ))}
        </div>
      )}
    </Panel>
  );
}

export function Finals() {
  const navigate = useNavigate();
  const { seasonId } = useParams<{ seasonId?: string }>();
  const [seasons, setSeasons] = useState<v1.V1Season[]>([]);
  const [finals, setFinals] = useState<v1.V1FinalsData | null>(null);
  const [corps, setCorps] = useState<v1.V1Corps[]>([]);
  const [runs, setRuns] = useState<v1.V1Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const [entering, setEntering] = useState(false);
  const [declaring, setDeclaring] = useState(false);
  const [selectedWinner, setSelectedWinner] = useState<string>("");
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState<v1.V1DeployResult | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    setError(null);
    setLoading(true);

    if (seasonId) {
      Promise.allSettled([
        v1.getSeasonFinals(seasonId, ac.signal),
        v1.listCorps(ac.signal),
        v1.listRuns(undefined, ac.signal),
      ]).then(([finalsRes, corpsRes, runsRes]) => {
        if (ac.signal.aborted) return;
        if (finalsRes.status === "fulfilled") setFinals(finalsRes.value);
        else setFinals(null);
        if (corpsRes.status === "fulfilled") setCorps(corpsRes.value);
        if (runsRes.status === "fulfilled") setRuns(runsRes.value);
      }).finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    } else {
      v1.listSeasons(ac.signal)
        .then((data) => { if (!ac.signal.aborted) setSeasons(data); })
        .catch((e) => { if (!ac.signal.aborted) setError(e instanceof Error ? e.message : "Failed to load seasons"); })
        .finally(() => { if (!ac.signal.aborted) setLoading(false); });
    }
    return () => ac.abort();
  }, [refreshToken, seasonId]);

  const corpsById = useMemo(
    () => Object.fromEntries(corps.map(c => [c.corps_id, c])),
    [corps],
  );

  const runsByCorps = useMemo(() => {
    if (!seasonId) return {};
    const filtered = runs.filter(r => r.season_id === seasonId);
    const grouped: Record<string, v1.V1Run> = {};
    for (const run of filtered) {
      const existing = grouped[run.corps_id];
      if (!existing || (run.started_at || "") > (existing.started_at || "")) {
        grouped[run.corps_id] = run;
      }
    }
    return grouped;
  }, [runs, seasonId]);

  const handleEnterFinals = async () => {
    if (!seasonId) return;
    setEntering(true);
    try {
      const data = await v1.enterSeasonFinals(seasonId);
      setFinals(data);
    } catch (e: any) {
      setError(e.message || "Failed to enter finals");
    } finally {
      setEntering(false);
    }
  };

  const handleDeclareWinner = async () => {
    if (!seasonId || !selectedWinner) return;
    setDeclaring(true);
    try {
      const data = await v1.declareSeasonWinner(seasonId, selectedWinner);
      setFinals(data);
    } catch (e: any) {
      setError(e.message || "Failed to declare winner");
    } finally {
      setDeclaring(false);
    }
  };

  const handleDeploy = async () => {
    if (!seasonId) return;
    setDeploying(true);
    setDeployResult(null);
    try {
      const result = await v1.deploySeasonWinner(seasonId);
      setDeployResult(result);
    } catch (e: any) {
      setError(e.message || "Failed to deploy winner");
    } finally {
      setDeploying(false);
    }
  };

  if (loading) return <div className="page-loading">Loading finals...</div>;
  if (error) {
    return (
      <div className="page-error">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
      </div>
    );
  }

  if (!seasonId) {
    const completedSeasons = seasons.filter(s => {
      const status = (s as any).status || (s.metadata as Record<string, unknown>)?.status as string;
      return status === "completed" || status === "touring" || status === "review" || status === "finals";
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
            const status = (s as any).status || (s.metadata as Record<string, unknown>)?.status as string || "planning";
            return (
              <div
                key={s.season_id}
                className="competition-card clickable"
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

  if (!finals) {
    return (
      <div className="page-content finals-page">
        <div className="page-header">
          <button className="back-btn" onClick={() => navigate("/finals")}>Back</button>
          <h1 className="page-title">{slugToTitle(seasonId)}</h1>
        </div>
        <p className="empty">Finals data not available yet.</p>
        <button className="primary" onClick={handleEnterFinals} disabled={entering}>
          {entering ? "Entering Finals..." : "Enter Finals"}
        </button>
      </div>
    );
  }

  const overallRows = finals.overall || [];
  const divisions = finals.divisions || [];
  const winner = finals.winner?.corps_id;

  return (
    <div className="page-content finals-page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate("/finals")}>Back</button>
        <h1 className="page-title">{slugToTitle(seasonId)}</h1>
        <Badge variant={winner ? "success" : "warning"}>{winner ? "Winner Declared" : "Finals In Progress"}</Badge>
      </div>

      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{overallRows.length}</span>
          <span className="summary-label">Corps</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{finals.required_scores}</span>
          <span className="summary-label">Required Scores</span>
        </div>
      </div>

      <Panel title="Declare Winner">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
          <select value={selectedWinner} onChange={(e) => setSelectedWinner(e.target.value)}>
            <option value="">Select corps...</option>
            {overallRows.map(row => (
              <option key={row.corps_id} value={row.corps_id}>
                {(row as any).display_name || corpsById[row.corps_id]?.display_name || `Corps • ${row.corps_id.slice(0, 8)}`}
              </option>
            ))}
          </select>
          <button className="primary" onClick={handleDeclareWinner} disabled={!selectedWinner || declaring}>
            {declaring ? "Declaring..." : "Declare Winner"}
          </button>
          {winner && (
            <>
              <Badge variant="success">
                Winner: {overallRows.find(r => r.corps_id === winner)?.display_name || corpsById[winner]?.display_name || `Corps • ${winner.slice(0, 8)}`}
              </Badge>
              <button className="primary" onClick={handleDeploy} disabled={deploying} style={{ fontSize: 12 }}>
                {deploying ? "Deploying..." : "Deploy Winner"}
              </button>
            </>
          )}
        </div>
        {deployResult && (
          <div className="success-banner" style={{ marginTop: 8, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span>
              Deployed! {deployResult.dispatched.length} agent(s) dispatched
              {deployResult.skipped.length > 0 && `, ${deployResult.skipped.length} skipped`}
            </span>
            <button onClick={() => setDeployResult(null)} style={{ background: "none", border: "none", cursor: "pointer", opacity: 0.7, color: "inherit" }}>x</button>
          </div>
        )}
      </Panel>

      <Panel title="Overall Rankings" style={{ marginTop: 16 }}>
        <DataTable<Record<string, unknown>>
          columns={[
            { key: "rank", label: "Rank", sortable: true, render: (v) => <strong>#{String(v)}</strong> },
            { key: "corps_id", label: "Corps", render: (_v, row) => (row as any).display_name || corpsById[row.corps_id as string]?.display_name || `Corps • ${String(row.corps_id).slice(0, 8)}` },
            { key: "score", label: "Score", sortable: true, render: (v) => Number(v || 0).toFixed(2) },
            { key: "qualified", label: "Qualified", render: (_v, row) => (
              <Badge variant={row.qualified ? "success" : "warning"}>
                {row.qualified ? "Qualified" : "Needs Scores"}
              </Badge>
            ) },
            { key: "scores_count", label: "Scores", render: (v) => `${v}/${finals.required_scores}` },
          ]}
          data={overallRows as Record<string, unknown>[]}
          defaultSortKey="rank"
          emptyMessage="No finals standings yet."
        />
      </Panel>

      <Panel title="Division Rankings" style={{ marginTop: 16 }}>
        {divisions.length === 0 && <p className="empty">No divisions assigned.</p>}
        {divisions.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {divisions.map((division) => (
              <div key={division.show_slug}>
                <h4 style={{ marginBottom: 8 }}>{slugToTitle(division.show_slug)}</h4>
                <DataTable<Record<string, unknown>>
                  columns={[
                    { key: "rank", label: "Rank", sortable: true, render: (v) => <strong>#{String(v)}</strong> },
                    { key: "corps_id", label: "Corps", render: (_v, row) => (row as any).display_name || corpsById[row.corps_id as string]?.display_name || `Corps • ${String(row.corps_id).slice(0, 8)}` },
                    { key: "score", label: "Score", sortable: true, render: (v) => Number(v || 0).toFixed(2) },
                    { key: "qualified", label: "Qualified", render: (_v, row) => (
                      <Badge variant={row.qualified ? "success" : "warning"}>
                        {row.qualified ? "Qualified" : "Needs Scores"}
                      </Badge>
                    ) },
                    { key: "scores_count", label: "Scores", render: (v) => `${v}/${finals.required_scores}` },
                  ]}
                  data={(division.standings || []) as Record<string, unknown>[]}
                  defaultSortKey="rank"
                  emptyMessage="No standings yet."
                />
              </div>
            ))}
          </div>
        )}
      </Panel>

      <ArtifactReviewPanel
        seasonId={seasonId}
        overallRows={overallRows}
        corpsById={corpsById}
      />
    </div>
  );
}
