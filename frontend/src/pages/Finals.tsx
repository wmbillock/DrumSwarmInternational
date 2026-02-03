import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge, DataTable, Panel } from "../ui";
import { formatStatus, slugToTitle } from "../utils/formatters";

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
        if (finalsRes.status === "fulfilled") setFinals(finalsRes.value);
        if (corpsRes.status === "fulfilled") setCorps(corpsRes.value);
        if (runsRes.status === "fulfilled") setRuns(runsRes.value);
        setLoading(false);
      }).catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load finals");
        setLoading(false);
      });
    } else {
      v1.listSeasons(ac.signal)
        .then(setSeasons)
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load seasons"))
        .finally(() => setLoading(false));
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
      const status = (s.metadata as Record<string, unknown>)?.status as string;
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
                {corpsById[row.corps_id]?.display_name || `Corps • ${row.corps_id.slice(0, 8)}`}
              </option>
            ))}
          </select>
          <button className="primary" onClick={handleDeclareWinner} disabled={!selectedWinner || declaring}>
            {declaring ? "Declaring..." : "Declare Winner"}
          </button>
          {winner && (
            <Badge variant="success">
              Winner: {corpsById[winner]?.display_name || `Corps • ${winner.slice(0, 8)}`}
            </Badge>
          )}
        </div>
      </Panel>

      <Panel title="Overall Rankings" style={{ marginTop: 16 }}>
        <DataTable<Record<string, unknown>>
          columns={[
            { key: "rank", label: "Rank", sortable: true, render: (v) => <strong>#{String(v)}</strong> },
            { key: "corps_id", label: "Corps", render: (_v, row) => corpsById[row.corps_id as string]?.display_name || `Corps • ${String(row.corps_id).slice(0, 8)}` },
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
                    { key: "corps_id", label: "Corps", render: (_v, row) => corpsById[row.corps_id as string]?.display_name || `Corps • ${String(row.corps_id).slice(0, 8)}` },
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

      <Panel title="Artifact Review" style={{ marginTop: 16 }}>
        {overallRows.length === 0 && <p className="empty">No corps to review yet.</p>}
        {overallRows.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {overallRows.map(row => {
              const run = runsByCorps[row.corps_id];
              return (
                <div
                  key={row.corps_id}
                  style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: 8 }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>
                      {corpsById[row.corps_id]?.display_name || `Corps • ${row.corps_id.slice(0, 8)}`}
                    </div>
                    <div className="text-muted" style={{ fontSize: 12 }}>
                      {run ? `${run.show_slug} • ${run.run_id}` : "No run artifacts yet."}
                    </div>
                  </div>
                  {run && (
                    <button className="secondary" onClick={() => navigate(`/runs/${run.run_id}`)}>
                      View Run
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
