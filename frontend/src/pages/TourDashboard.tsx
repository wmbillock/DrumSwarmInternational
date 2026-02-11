import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge, Panel, DataTable } from "../ui";
import { formatStatus, slugToTitle } from "../utils/formatters";

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
  const [tourSeasons, setTourSeasons] = useState<TouringSeason[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const [advancing, setAdvancing] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    setError(null);

    const loadData = async () => {
      try {
        // Load competitions and seasons in parallel
        const [comps, seasons] = await Promise.all([
          v1.listCompetitions(ac.signal).catch(() => []),
          v1.listSeasons(ac.signal),
        ]);

        setCompetitions(comps);

        // Find touring seasons and load their tour status
        const touring = seasons.filter(
          (s: any) => s.metadata?.status === "touring" || s.metadata?.status === "finals"
        );

        const enriched = await Promise.all(
          touring.map(async (s: any) => {
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

        setTourSeasons(enriched);
      } catch (e: any) {
        if (e.name !== "AbortError") setError(e.message || "Failed to load tour data");
      } finally {
        setLoading(false);
      }
    };

    loadData();
    return () => ac.abort();
  }, [refreshToken]);

  const handleAdvance = useCallback(async (seasonId: string) => {
    setAdvancing(seasonId);
    try {
      await v1.advanceSeasonTour(seasonId);
      setRefreshToken((t) => t + 1);
    } catch (e: any) {
      setError(e.message || "Failed to advance round");
    } finally {
      setAdvancing(null);
    }
  }, []);

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

  const totalRounds = tourSeasons.reduce(
    (sum, s) => sum + (s.tourStatus?.schedule?.length || 0),
    0
  );
  const completedRounds = tourSeasons.reduce(
    (sum, s) => sum + (s.tourStatus?.history?.length || 0),
    0
  );

  return (
    <div className="page-content tour-dashboard">
      <div className="page-header">
        <h1 className="page-title">On Tour</h1>
        <button className="secondary" onClick={() => setRefreshToken((t) => t + 1)}>
          Refresh
        </button>
      </div>

      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{tourSeasons.length}</span>
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

      {/* Touring Seasons */}
      {tourSeasons.length > 0 && (
        <div className="dash-section">
          <h2>Tours in Progress</h2>
          {tourSeasons.map((season) => (
            <TourSeasonCard
              key={season.season_id}
              season={season}
              advancing={advancing === season.season_id}
              onAdvance={() => handleAdvance(season.season_id)}
              onAutoAdvance={(enabled) => handleAutoAdvance(season.season_id, enabled)}
              onCorpsClick={(corpsId) => navigate(`/corps/${corpsId}`)}
              onSeasonClick={() => navigate(`/seasons/${season.season_id}`)}
            />
          ))}
        </div>
      )}

      {tourSeasons.length === 0 && active.length === 0 && completed.length === 0 && (
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
        <div className="dash-section">
          <h2>Completed</h2>
          <div className="competition-grid">
            {completed.map((c) => (
              <div
                key={c.competition_id}
                className="competition-card"
                onClick={() => navigate(`/tour/${c.competition_id}`)}
              >
                <h3 title={c.show_slug}>{slugToTitle(c.show_slug)}</h3>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <Badge variant="info">{formatStatus(c.status)}</Badge>
                  <span className="text-muted" title={c.season_id}>
                    {slugToTitle(c.season_id)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tour Season Card — shows schedule progress, standings, controls     */
/* ------------------------------------------------------------------ */

function TourSeasonCard({
  season,
  advancing,
  onAdvance,
  onAutoAdvance,
  onCorpsClick,
  onSeasonClick,
}: {
  season: TouringSeason;
  advancing: boolean;
  onAdvance: () => void;
  onAutoAdvance: (enabled: boolean) => void;
  onCorpsClick: (corpsId: string) => void;
  onSeasonClick: () => void;
}) {
  const ts = season.tourStatus;
  if (!ts) {
    return (
      <Panel title={season.name} actions={<Badge variant="warning">No data</Badge>}>
        <p className="text-muted">Tour status unavailable</p>
      </Panel>
    );
  }

  const totalRounds = ts.schedule.length;
  const completedCount = ts.history.length;
  const progress = totalRounds > 0 ? Math.round((completedCount / totalRounds) * 100) : 0;
  const hasPending = ts.upcoming.length > 0 || ts.current_round !== null;

  // Build standings from completed rounds
  const standingsData = (season.standings as any)?.results || [];

  const roundColumns = [
    { key: "round", label: "Round", render: (_v: unknown, r: TourRound) => `#${r.round ?? "?"}` },
    { key: "show_slug", label: "Show", render: (_v: unknown, r: TourRound) => slugToTitle(r.show_slug) },
    {
      key: "corps_ids",
      label: "Corps",
      render: (_v: unknown, r: TourRound) => `${r.corps_ids?.length ?? 0} corps`,
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
          {r.corps_id?.slice(0, 8)}...
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
        <span style={{ cursor: "pointer" }} onClick={onSeasonClick}>
          {season.name}
        </span>
      }
      actions={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge variant={ts.status === "touring" ? "success" : "info"}>
            {formatStatus(ts.status)}
          </Badge>
          <span className="text-muted" style={{ fontSize: 12 }}>
            {completedCount}/{totalRounds} rounds
          </span>
        </div>
      }
    >
      {/* Progress bar */}
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

      {/* Controls */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <button
          className="primary"
          disabled={!hasPending || advancing}
          onClick={onAdvance}
        >
          {advancing ? "Advancing..." : "Advance Round"}
        </button>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
          <input
            type="checkbox"
            checked={season.autoAdvance || false}
            onChange={(e) => onAutoAdvance(e.target.checked)}
          />
          Auto-advance
        </label>
        {!hasPending && <Badge variant="info">All rounds complete</Badge>}
      </div>

      {/* Current round */}
      {ts.current_round && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ margin: "0 0 8px" }}>
            Current: Round {ts.current_round.round} — {slugToTitle(ts.current_round.show_slug)}
          </h4>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Corps: {ts.current_round.corps_ids.map((id) => id.slice(0, 8)).join(", ")}
          </div>
        </div>
      )}

      {/* Schedule table */}
      {ts.schedule.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ margin: "0 0 8px" }}>Schedule</h4>
          <DataTable columns={roundColumns} data={ts.schedule} />
        </div>
      )}

      {/* Standings */}
      {standingsData.length > 0 && (
        <div>
          <h4 style={{ margin: "0 0 8px" }}>Standings</h4>
          <DataTable columns={standingsColumns} data={standingsData} />
        </div>
      )}
    </Panel>
  );
}
