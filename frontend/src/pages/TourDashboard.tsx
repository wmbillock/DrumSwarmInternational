import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge, Panel, DataTable } from "../ui";
import { formatStatus, slugToTitle } from "../utils/formatters";
import { useOperations } from "../hooks/useOperations";

interface TourRound {
  round: number;
  competition_id: string;
  show_slug: string;
  corps_ids: string[];
  status: string;
  completed_at?: string;
  standings?: { corps_id: string; rank: number; final_score: number }[];
}

interface TourStatus {
  season_id: string;
  status: string;
  current_round: TourRound | null;
  history: TourRound[];
  upcoming: TourRound[];
  schedule: TourRound[];
}

interface TouringSeason {
  season_id: string;
  name: string;
  dir_name: string;
  metadata: Record<string, unknown>;
  tourStatus?: TourStatus;
  standings?: any;
  autoAdvance?: boolean;
}

export function TourDashboard() {
  const navigate = useNavigate();
  const [competitions, setCompetitions] = useState<v1.V1Competition[]>([]);
  const [allSeasons, setAllSeasons] = useState<TouringSeason[]>([]);
  const [corpsNames, setCorpsNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const [advancing, setAdvancing] = useState<string | null>(null);
  const [advanceResult, setAdvanceResult] = useState<{ seasonId: string; data: any } | null>(null);
  const [executionPhase, setExecutionPhase] = useState<Record<string, string>>({});
  const [hideCompleted, setHideCompleted] = useState(true);
  const ops = useOperations();

  // On mount, check if any season has an active "advance_round" operation
  // and restore the advancing state
  useEffect(() => {
    for (const op of ops.operations) {
      if (
        op.operation_type === "advance_round" &&
        op.target_type === "season" &&
        (op.status === "pending" || op.status === "running")
      ) {
        setAdvancing(op.target_id);
        setExecutionPhase((prev) => ({
          ...prev,
          [op.target_id!]: op.status === "pending" ? "Dispatching agents..." : "Judging & scoring...",
        }));
      } else if (
        op.operation_type === "advance_round" &&
        op.target_type === "season" &&
        op.status === "completed" &&
        op.result
      ) {
        // Restore completed result if it was recent (within 30s)
        const completedAt = op.completed_at ? new Date(op.completed_at).getTime() : 0;
        if (Date.now() - completedAt < 30000) {
          try {
            const data = JSON.parse(op.result);
            setAdvanceResult({ seasonId: op.target_id!, data });
            setExecutionPhase((prev) => ({ ...prev, [op.target_id!]: "Complete!" }));
          } catch { /* ignore parse errors */ }
        }
      }
    }
  }, [ops.operations]);

  useEffect(() => {
    const ac = new AbortController();
    setError(null);

    const loadData = async () => {
      try {
        const [comps, seasons, allCorps] = await Promise.all([
          v1.listCompetitions(ac.signal).catch(() => []),
          v1.listSeasons(ac.signal),
          v1.listCorps(ac.signal, true).catch(() => []),
        ]);

        setCompetitions(comps);
        const nameMap: Record<string, string> = {};
        for (const c of allCorps) {
          nameMap[c.corps_id] = c.display_name || c.corps_id;
        }
        setCorpsNames(nameMap);

        const enriched = await Promise.all(
          seasons.map(async (s: any) => {
            try {
              const [tourStatus, standings] = await Promise.all([
                v1.getSeasonTourStatus(s.season_id, ac.signal).catch(() => null),
                v1.getSeasonStandings(s.season_id, ac.signal).catch(() => null),
              ]);
              return {
                ...s,
                name: s.name || s.metadata?.name || s.season_id,
                tourStatus,
                standings,
                autoAdvance: !!s.metadata?.auto_advance || !!(tourStatus as any)?.auto_advance,
              } as TouringSeason;
            } catch {
              return { ...s, name: s.name || s.season_id } as TouringSeason;
            }
          })
        );

        setAllSeasons(enriched);
      } catch (e: any) {
        if (e.name !== "AbortError") setError(e.message || "Failed to load tour data");
      } finally {
        setLoading(false);
      }
    };

    loadData();

    const interval = setInterval(() => {
      loadData();
    }, 30000);

    return () => {
      ac.abort();
      clearInterval(interval);
    };
  }, [refreshToken]);

  const handleAdvance = useCallback(async (seasonId: string) => {
    // Check if there's already an active operation for this season
    if (ops.isActive("season", seasonId)) {
      setError("An operation is already in progress for this season.");
      return;
    }

    setAdvancing(seasonId);
    setAdvanceResult(null);
    setExecutionPhase((prev) => ({ ...prev, [seasonId]: "Dispatching agents..." }));
    try {
      // Update phase after a delay to show scoring phase
      const phaseTimer = setTimeout(() => {
        setExecutionPhase((prev) => ({ ...prev, [seasonId]: "Judging & scoring..." }));
      }, 3000);

      const result = await v1.advanceSeasonTour(seasonId);
      clearTimeout(phaseTimer);

      // Track the operation if one was returned
      if (result.operation_id) {
        ops.track(result.operation_id);
      }

      setExecutionPhase((prev) => ({ ...prev, [seasonId]: "Complete!" }));
      setAdvanceResult({ seasonId, data: result });
      setRefreshToken((t) => t + 1);

      // Clear phase after 3s
      setTimeout(() => {
        setExecutionPhase((prev) => {
          const next = { ...prev };
          delete next[seasonId];
          return next;
        });
      }, 3000);
    } catch (e: any) {
      setExecutionPhase((prev) => {
        const next = { ...prev };
        delete next[seasonId];
        return next;
      });
      if (e.message?.includes("timeout") || e.message?.includes("504")) {
        setAdvanceResult({
          seasonId,
          data: { status: "running", round: "?", message: "Round is being scored in the background. Refresh to check." },
        });
        setTimeout(() => setRefreshToken((t) => t + 1), 10000);
      } else {
        setError(e.message || "Failed to advance round");
      }
    } finally {
      setAdvancing(null);
    }
  }, [ops]);

  const handleAutoAdvance = useCallback(async (seasonId: string, enabled: boolean) => {
    try {
      await v1.setSeasonAutoAdvance(seasonId, enabled);
      setRefreshToken((t) => t + 1);
    } catch (e: any) {
      setError(e.message || "Failed to toggle auto-advance");
    }
  }, []);

  const active = competitions.filter((c) => c.status === "active" || c.status === "pending");
  const completed = competitions.filter((c) => c.status === "completed" || c.status === "scored");

  const touringSeasons = allSeasons.filter((s) => {
    const status = (s.metadata?.status as string) || s.tourStatus?.status || "";
    return status === "touring" || status === "finals";
  });
  const completedSeasons = allSeasons.filter((s) => {
    const status = (s.metadata?.status as string) || s.tourStatus?.status || "";
    return status === "completed" || status === "disbanded";
  });
  const otherSeasons = allSeasons.filter((s) => {
    const status = (s.metadata?.status as string) || s.tourStatus?.status || "";
    return status !== "touring" && status !== "finals" && status !== "completed" && status !== "disbanded";
  });

  if (loading) return <div className="page-loading">Loading tour dashboard...</div>;
  if (error) {
    return (
      <div className="page-error">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={() => { setError(null); setRefreshToken((t) => t + 1); }}>
          Retry
        </button>
      </div>
    );
  }

  const totalRounds = allSeasons.reduce(
    (sum, s) => sum + (s.tourStatus?.schedule?.length || 0),
    0
  );
  const completedRounds = allSeasons.reduce(
    (sum, s) => sum + (s.tourStatus?.history?.length || 0),
    0
  );

  return (
    <div className="page-content tour-dashboard">
      <div className="page-header">
        <h1 className="page-title">Tour & Competitions</h1>
        <button className="secondary" onClick={() => setRefreshToken((t) => t + 1)}>
          Refresh
        </button>
      </div>

      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{allSeasons.length}</span>
          <span className="summary-label">Seasons</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{touringSeasons.length}</span>
          <span className="summary-label">Active Tours</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{competitions.length}</span>
          <span className="summary-label">Competitions</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{completedRounds}/{totalRounds}</span>
          <span className="summary-label">Rounds</span>
        </div>
      </div>

      {/* Active Touring Seasons */}
      {touringSeasons.length > 0 && (
        <div className="dash-section">
          <h2>Tours in Progress</h2>
          {touringSeasons.map((season) => (
            <TourSeasonCard
              key={season.season_id}
              season={season}
              advancing={advancing === season.season_id}
              executionPhase={executionPhase[season.season_id]}
              advanceResult={advanceResult?.seasonId === season.season_id ? advanceResult.data : null}
              onDismissResult={() => setAdvanceResult(null)}
              onAdvance={() => handleAdvance(season.season_id)}
              onAutoAdvance={(enabled) => handleAutoAdvance(season.season_id, enabled)}
              onCorpsClick={(corpsId) => navigate(`/corps/${corpsId}`)}
              onSeasonClick={() => navigate(`/seasons/${season.season_id}`)}
              onCompetitionClick={(compId) => navigate(`/tour/${compId}`)}
              onShowClick={(showSlug) => navigate(`/shows/${showSlug}`)}
              corpsNames={corpsNames}
              defaultCollapsed={false}
            />
          ))}
        </div>
      )}

      {/* Other Seasons (planning, etc.) */}
      {otherSeasons.length > 0 && (
        <div className="dash-section">
          <h2>Other Seasons</h2>
          {otherSeasons.map((season) => (
            <TourSeasonCard
              key={season.season_id}
              season={season}
              advancing={advancing === season.season_id}
              executionPhase={executionPhase[season.season_id]}
              advanceResult={null}
              onDismissResult={() => {}}
              onAdvance={() => handleAdvance(season.season_id)}
              onAutoAdvance={(enabled) => handleAutoAdvance(season.season_id, enabled)}
              onCorpsClick={(corpsId) => navigate(`/corps/${corpsId}`)}
              onSeasonClick={() => navigate(`/seasons/${season.season_id}`)}
              onCompetitionClick={(compId) => navigate(`/tour/${compId}`)}
              onShowClick={(showSlug) => navigate(`/shows/${showSlug}`)}
              corpsNames={corpsNames}
              defaultCollapsed={true}
            />
          ))}
        </div>
      )}

      {/* Completed / archived seasons — collapsible */}
      {completedSeasons.length > 0 && (
        <div className="dash-section">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <h2 style={{ margin: 0 }}>Completed Seasons ({completedSeasons.length})</h2>
            <button className="small" onClick={() => setHideCompleted(!hideCompleted)}>
              {hideCompleted ? "Show" : "Hide"}
            </button>
          </div>
          {!hideCompleted && completedSeasons.map((season) => (
            <TourSeasonCard
              key={season.season_id}
              season={season}
              advancing={false}
              advanceResult={null}
              onDismissResult={() => {}}
              onAdvance={() => {}}
              onAutoAdvance={() => {}}
              onCorpsClick={(corpsId) => navigate(`/corps/${corpsId}`)}
              onSeasonClick={() => navigate(`/seasons/${season.season_id}`)}
              onCompetitionClick={(compId) => navigate(`/tour/${compId}`)}
              onShowClick={(showSlug) => navigate(`/shows/${showSlug}`)}
              corpsNames={corpsNames}
              defaultCollapsed={true}
            />
          ))}
        </div>
      )}

      {allSeasons.length === 0 && active.length === 0 && completed.length === 0 && (
        <p className="empty">No tours or competitions yet. Start a tour from the Season Workshop.</p>
      )}

      {active.length > 0 && (
        <div className="dash-section">
          <h2>Active Competitions</h2>
          <div className="competition-grid">
            {active.map((c) => (
              <div
                key={c.competition_id}
                className="competition-card"
                onClick={() => navigate(`/tour/${c.competition_id}`)}
              >
                <h3 title={c.show_slug}>{slugToTitle(c.show_slug)}</h3>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
                  <Badge variant="success">{formatStatus(c.status)}</Badge>
                  <span className="text-muted" title={c.season_id}>
                    {slugToTitle(c.season_id)}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {c.corps_ids.length} corps competing
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {completed.length > 0 && (
        <CompletedSection competitions={completed} navigate={navigate} />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Completed competitions — grouped by season, collapsible             */
/* ------------------------------------------------------------------ */

function CompletedSection({
  competitions,
  navigate,
}: {
  competitions: Array<{ competition_id: string; show_slug: string; status: string; season_id: string }>;
  navigate: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const bySeason = new Map<string, typeof competitions>();
  for (const c of competitions) {
    const key = c.season_id || "unknown";
    if (!bySeason.has(key)) bySeason.set(key, []);
    bySeason.get(key)!.push(c);
  }
  const seasonEntries = [...bySeason.entries()].sort((a, b) => b[1].length - a[1].length);
  const PREVIEW_SEASONS = 2;
  const visible = expanded ? seasonEntries : seasonEntries.slice(0, PREVIEW_SEASONS);
  const hiddenCount = seasonEntries.length - PREVIEW_SEASONS;

  return (
    <div className="dash-section">
      <h2>Completed ({competitions.length})</h2>
      {visible.map(([seasonId, comps]) => (
        <div key={seasonId} style={{ marginBottom: 12 }}>
          <h3 style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>
            {slugToTitle(seasonId)} ({comps.length} rounds)
          </h3>
          <div className="competition-grid">
            {comps.slice(0, expanded ? comps.length : 5).map((c) => (
              <div
                key={c.competition_id}
                className="competition-card"
                onClick={() => navigate(`/tour/${c.competition_id}`)}
              >
                <h3 title={c.show_slug}>{slugToTitle(c.show_slug)}</h3>
                <Badge variant="info">{formatStatus(c.status)}</Badge>
              </div>
            ))}
            {!expanded && comps.length > 5 && (
              <div className="competition-card text-muted" onClick={() => setExpanded(true)} style={{ cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                +{comps.length - 5} more
              </div>
            )}
          </div>
        </div>
      ))}
      {!expanded && hiddenCount > 0 && (
        <button className="small" onClick={() => setExpanded(true)}>
          Show all ({hiddenCount} more seasons)
        </button>
      )}
      {expanded && seasonEntries.length > PREVIEW_SEASONS && (
        <button className="small" onClick={() => setExpanded(false)}>
          Collapse
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tour Season Card — collapsible, show links, execution phase display */
/* ------------------------------------------------------------------ */

function TourSeasonCard({
  season,
  advancing,
  executionPhase,
  advanceResult,
  onDismissResult,
  onAdvance,
  onAutoAdvance,
  onCorpsClick,
  onSeasonClick,
  onCompetitionClick,
  onShowClick,
  corpsNames = {},
  defaultCollapsed = false,
}: {
  season: TouringSeason;
  advancing: boolean;
  executionPhase?: string;
  advanceResult?: any;
  onDismissResult: () => void;
  onAdvance: () => void;
  onAutoAdvance: (enabled: boolean) => void;
  onCorpsClick: (corpsId: string) => void;
  onSeasonClick: () => void;
  onCompetitionClick: (competitionId: string) => void;
  onShowClick: (showSlug: string) => void;
  corpsNames?: Record<string, string>;
  defaultCollapsed?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const ts = season.tourStatus;
  const seasonStatus = (season.metadata?.status as string) || ts?.status || "unknown";

  if (!ts) {
    return (
      <Panel
        title={
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{ cursor: "pointer", userSelect: "none", fontSize: 12, opacity: 0.6 }}
              onClick={(e) => { e.stopPropagation(); setCollapsed(!collapsed); }}
            >
              {collapsed ? "\u25B6" : "\u25BC"}
            </span>
            <span style={{ cursor: "pointer" }} onClick={onSeasonClick}>
              {season.name}
            </span>
          </span>
        }
        actions={
          <Badge variant={seasonStatus === "completed" ? "info" : "warning"}>
            {formatStatus(seasonStatus)}
          </Badge>
        }
      >
        {!collapsed && (
          <p className="text-muted">
            {seasonStatus === "planning"
              ? "Season is being planned. Start a tour from the Season Workshop."
              : seasonStatus === "completed"
              ? "Season completed."
              : "Tour status unavailable."}
          </p>
        )}
      </Panel>
    );
  }

  const totalRounds = ts.schedule.length;
  const completedCount = ts.history.length;
  const progress = totalRounds > 0 ? Math.round((completedCount / totalRounds) * 100) : 0;
  const hasPending = ts.upcoming.length > 0 || ts.current_round !== null;
  const isTouringOrFinals = seasonStatus === "touring" || seasonStatus === "finals";

  const standingsData = (season.standings as any)?.results || [];

  const roundColumns = [
    { key: "round", label: "#", render: (_v: unknown, r: TourRound) => `${r.round ?? "?"}` },
    {
      key: "show_slug",
      label: "Show",
      render: (_v: unknown, r: TourRound) => (
        <span
          style={{ cursor: "pointer", textDecoration: "underline", color: "var(--accent)" }}
          onClick={(e: React.MouseEvent) => {
            e.stopPropagation();
            onShowClick(r.show_slug);
          }}
        >
          {slugToTitle(r.show_slug)}
        </span>
      ),
    },
    {
      key: "corps_ids",
      label: "Corps",
      render: (_v: unknown, r: TourRound) => `${r.corps_ids?.length ?? 0}`,
    },
    {
      key: "status",
      label: "Status",
      render: (_v: unknown, r: TourRound) => (
        <Badge
          variant={
            r.status === "completed" ? "success" : r.status === "pending" || !r.status ? "default" : "warning"
          }
        >
          {formatStatus(r.status || "pending")}
        </Badge>
      ),
    },
    {
      key: "standings",
      label: "Winner / Score",
      render: (_v: unknown, r: TourRound) => {
        if (r.status !== "completed" || !r.standings?.length) return <span className="text-muted">&mdash;</span>;
        const winner = r.standings[0];
        const name = corpsNames[winner.corps_id] || winner.corps_id?.slice(0, 8);
        return (
          <span style={{ fontSize: 12 }}>
            <strong>{name}</strong> {winner.final_score?.toFixed(1)}
          </span>
        );
      },
    },
    {
      key: "competition_id",
      label: "",
      render: (_v: unknown, r: TourRound) => {
        if (!r.competition_id) return null;
        return (
          <button
            className="small"
            style={{ fontSize: 11, padding: "2px 8px" }}
            onClick={(e) => {
              e.stopPropagation();
              onCompetitionClick(r.competition_id);
            }}
          >
            Details
          </button>
        );
      },
    },
  ];

  const standingsColumns = [
    { key: "rank", label: "Rank" },
    {
      key: "corps_id",
      label: "Corps",
      render: (_v: unknown, r: any) => (
        <span
          style={{ cursor: "pointer", textDecoration: "underline" }}
          onClick={(e: React.MouseEvent) => {
            e.stopPropagation();
            onCorpsClick(r.corps_id);
          }}
          title={r.corps_id}
        >
          {corpsNames[r.corps_id] || r.corps_id?.slice(0, 8)}
        </span>
      ),
    },
    {
      key: "final_score",
      label: "Score",
      render: (_v: unknown, r: any) => (typeof r.final_score === "number" ? r.final_score.toFixed(1) : "-"),
    },
  ];

  return (
    <Panel
      title={
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{ cursor: "pointer", userSelect: "none", fontSize: 12, opacity: 0.6 }}
            onClick={(e) => { e.stopPropagation(); setCollapsed(!collapsed); }}
          >
            {collapsed ? "\u25B6" : "\u25BC"}
          </span>
          <span style={{ cursor: "pointer" }} onClick={onSeasonClick}>
            {season.name}
          </span>
        </span>
      }
      actions={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge variant={isTouringOrFinals ? "success" : seasonStatus === "completed" ? "info" : "default"}>
            {formatStatus(seasonStatus)}
          </Badge>
          {totalRounds > 0 && (
            <span className="text-muted" style={{ fontSize: 12 }}>
              {completedCount}/{totalRounds} rounds
            </span>
          )}
        </div>
      }
    >
      {!collapsed && (
        <>
          {/* Progress bar */}
          {totalRounds > 0 && (
            <div
              style={{
                height: 6,
                borderRadius: 3,
                background: "var(--border)",
                marginBottom: 16,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${progress}%`,
                  background: "var(--accent)",
                  borderRadius: 3,
                  transition: "width 0.3s ease",
                }}
              />
            </div>
          )}

          {/* Inline round result card */}
          {advanceResult && (
            <div style={{
              marginBottom: 16,
              padding: 12,
              border: "1px solid var(--success)",
              borderRadius: 6,
              background: "rgba(0, 200, 100, 0.05)",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong>Round {advanceResult.round} — {formatStatus(advanceResult.status)}</strong>
                  {advanceResult.standings?.length > 0 && (
                    <div style={{ marginTop: 4, fontSize: 13 }}>
                      Winner: <strong>{corpsNames[advanceResult.standings[0]?.corps_id] || advanceResult.standings[0]?.corps_id?.slice(0, 8)}</strong>
                      {" "}({advanceResult.standings[0]?.final_score?.toFixed(1)})
                      {advanceResult.standings.length > 1 && (
                        <span className="text-muted">
                          {" "}+{(advanceResult.standings[0]?.final_score - advanceResult.standings[1]?.final_score)?.toFixed(1)} over 2nd
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  {advanceResult.competition_id && (
                    <button
                      className="small"
                      onClick={() => onCompetitionClick(advanceResult.competition_id)}
                    >
                      View Full Results
                    </button>
                  )}
                  <button
                    onClick={onDismissResult}
                    style={{ background: "none", border: "none", cursor: "pointer", opacity: 0.7, color: "inherit" }}
                  >
                    x
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Controls — only for touring/finals seasons */}
          {isTouringOrFinals && (
            <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
              <button
                className="primary"
                disabled={!hasPending || advancing}
                onClick={onAdvance}
                style={{ minWidth: 140 }}
              >
                {advancing ? (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span className="spinner" style={{
                      display: "inline-block", width: 12, height: 12,
                      border: "2px solid transparent", borderTopColor: "currentColor",
                      borderRadius: "50%", animation: "spin 0.8s linear infinite",
                    }} />
                    Scoring...
                  </span>
                ) : "Run Next Round"}
              </button>
              {executionPhase && (
                <span style={{ fontSize: 12, color: "var(--accent)", fontWeight: 600 }}>
                  {executionPhase}
                </span>
              )}
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={season.autoAdvance || false}
                  onChange={(e) => onAutoAdvance(e.target.checked)}
                />
                Auto-advance
              </label>
              {!hasPending && <Badge variant="info">All rounds complete</Badge>}
            </div>
          )}

          {/* Current round — show name is clickable */}
          {ts.current_round && (
            <div style={{ marginBottom: 16, padding: 12, border: "1px solid var(--border)", borderRadius: 6 }}>
              <h4 style={{ margin: "0 0 8px" }}>
                Next Up: Round {ts.current_round.round} &mdash;{" "}
                <span
                  style={{ cursor: "pointer", textDecoration: "underline", color: "var(--accent)" }}
                  onClick={() => onShowClick(ts.current_round!.show_slug)}
                >
                  {slugToTitle(ts.current_round.show_slug)}
                </span>
              </h4>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                Corps: {ts.current_round.corps_ids.map((id) => corpsNames[id] || id.slice(0, 8)).join(", ")}
              </div>
            </div>
          )}

          {/* Schedule table with inline scores */}
          {ts.schedule.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ margin: "0 0 8px" }}>Schedule</h4>
              <DataTable columns={roundColumns} data={ts.schedule} />
            </div>
          )}

          {/* Standings */}
          {standingsData.length > 0 && (
            <div>
              <h4 style={{ margin: "0 0 8px" }}>Cumulative Standings</h4>
              <DataTable columns={standingsColumns} data={standingsData} />
            </div>
          )}
        </>
      )}
    </Panel>
  );
}
