import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Panel, Badge, DataTable, Tabs } from "../ui";
import type { TabItem } from "../ui";
import * as v1 from "../services/v1";
import { formatStatus, slugToTitle } from "../utils/formatters";
import { TourSchedule } from "../components/TourSchedule";

export function SeasonWorkshop() {
  const navigate = useNavigate();
  const { seasonId } = useParams<{ seasonId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [seasons, setSeasons] = useState<v1.V1Season[]>([]);
  const [detail, setDetail] = useState<(v1.V1Season & { registered_corps?: string[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "setup");
  const [corps, setCorps] = useState<v1.V1Corps[]>([]);
  const [showThreads, setShowThreads] = useState<v1.V1Thread[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newSeasonName, setNewSeasonId] = useState("");
  const [creating, setCreating] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);
  const [config, setConfig] = useState({ corps_per_contest: 12, required_scores: 1 });
  const [assignments, setAssignments] = useState<Record<string, string[]>>({});
  const [savingConfig, setSavingConfig] = useState(false);
  const [locking, setLocking] = useState(false);
  const [startingTour, setStartingTour] = useState(false);
  const [competitions, setCompetitions] = useState<v1.V1Competition[]>([]);
  const [selectedCompetitionId, setSelectedCompetitionId] = useState<string | null>(null);
  const [standings, setStandings] = useState<v1.V1Standings | null>(null);
  const [recap, setRecap] = useState<v1.V1RecapRow[]>([]);
  const [standingsView, setStandingsView] = useState<"standings" | "recap">("standings");
  const [breakdowns, setBreakdowns] = useState<Record<string, v1.V1CorpsBreakdown | null>>({});
  const [standingsLoading, setStandingsLoading] = useState(false);
  const [tourSchedule, setTourSchedule] = useState<{ competition_id: string; show_slug: string; corps_ids: string[] }[]>([]);
  const [tourStandings, setTourStandings] = useState<any>(null);
  const [tourCompetitions, setTourCompetitions] = useState<v1.V1Competition[]>([]);
  const [tourLoading, setTourLoading] = useState(false);
  const [enteringFinals, setEnteringFinals] = useState(false);
  const [finalizing, setFinalizing] = useState(false);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError("");
    Promise.allSettled([
      v1.listSeasons(ac.signal),
      v1.listCorps(ac.signal),
      v1.listThreads(ac.signal),
    ]).then(([seasonsRes, corpsRes, threadsRes]) => {
      if (seasonsRes.status === "fulfilled") setSeasons(seasonsRes.value);
      if (corpsRes.status === "fulfilled") setCorps(corpsRes.value);
      if (threadsRes.status === "fulfilled") setShowThreads(threadsRes.value);
      setLoading(false);
    });
    return () => ac.abort();
  }, [refreshToken]);

  useEffect(() => {
    if (!seasonId) { setDetail(null); return; }
    const ac = new AbortController();
    setDetailLoading(true);
    v1.getSeason(seasonId, ac.signal)
      .then((data) => {
        setDetail(data);
        setConfig({
          corps_per_contest: data.config?.corps_per_contest ?? 12,
          required_scores: data.config?.required_scores ?? 1,
        });
        setAssignments(data.divisions || {});
      })
      .catch(e => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => setDetailLoading(false));
    return () => ac.abort();
  }, [seasonId]);

  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab && tab !== activeTab) {
      setActiveTab(tab);
    }
  }, [searchParams, activeTab]);

  useEffect(() => {
    if (!seasonId || activeTab !== "standings") return;
    const ac = new AbortController();
    setStandingsLoading(true);
    setStandings(null);
    setRecap([]);
    v1.listCompetitions(ac.signal)
      .then((comps) => {
        const filtered = comps.filter(c => c.season_id === seasonId);
        setCompetitions(filtered);
        const nextId = filtered.find(c => c.competition_id === selectedCompetitionId)?.competition_id
          || filtered[0]?.competition_id
          || null;
        setSelectedCompetitionId(nextId);
        return nextId;
      })
      .then((id) => {
        if (!id) return;
        return Promise.all([
          v1.getScores(id, ac.signal),
          v1.getRecap(id, "json", ac.signal),
        ]);
      })
      .then((data) => {
        if (!data) return;
        setStandings(data[0]);
        setRecap(data[1]);
      })
      .catch(() => {})
      .finally(() => setStandingsLoading(false));
    return () => ac.abort();
  }, [activeTab, seasonId, selectedCompetitionId]);

  useEffect(() => {
    if (!seasonId || activeTab !== "tour") return;
    const ac = new AbortController();
    setTourLoading(true);
    Promise.allSettled([
      v1.getSeasonSchedule(seasonId, ac.signal),
      v1.getSeasonStandings(seasonId, ac.signal),
      v1.listCompetitions(ac.signal),
    ]).then(([scheduleRes, standingsRes, competitionsRes]) => {
      if (scheduleRes.status === "fulfilled") setTourSchedule(scheduleRes.value);
      if (standingsRes.status === "fulfilled") setTourStandings(standingsRes.value);
      if (competitionsRes.status === "fulfilled") {
        setTourCompetitions(competitionsRes.value.filter(c => c.season_id === seasonId));
      }
    }).finally(() => setTourLoading(false));
    return () => ac.abort();
  }, [activeTab, seasonId]);

  const corpsById = useMemo(() => Object.fromEntries(corps.map(c => [c.corps_id, c])), [corps]);
  const isTouring = Boolean(
    detail && (
      detail.metadata?.status === "touring"
      || detail.metadata?.status === "on_tour"
      || (detail as any).status === "touring"
      || (detail as any).status === "on_tour"
    )
  );
  const seasonStatus = detail?.metadata?.status || (detail as any)?.status || "";
  const canFinals = Boolean(detail && ["finals", "completed", "review", "locked", "touring", "on_tour"].includes(seasonStatus));

  const competitionStatus = useMemo(
    () => Object.fromEntries(tourCompetitions.map(c => [c.competition_id, c.status])),
    [tourCompetitions],
  );

  const currentCompetitionId = useMemo(() => {
    const current = tourCompetitions.find(c => ["in_progress", "running", "live", "active"].includes(c.status));
    if (current) return current.competition_id;
    const upcoming = tourSchedule.find(s => !["completed", "final", "scored", "closed"].includes(competitionStatus[s.competition_id] || ""));
    return upcoming?.competition_id || tourSchedule[0]?.competition_id || null;
  }, [competitionStatus, tourCompetitions, tourSchedule]);

  const overallRows = useMemo(() => {
    const source = Array.isArray(tourStandings)
      ? tourStandings
      : tourStandings?.overall || tourStandings?.overall_rankings || tourStandings?.standings || [];
    if (!Array.isArray(source)) return [];
    return source.map((row: any, idx: number) => ({
      rank: row.rank ?? idx + 1,
      corps: row.corps_name
        || row.display_name
        || (row.corps_id ? (corpsById[row.corps_id]?.display_name || `Corps • ${row.corps_id.slice(0, 8)}`) : "Unknown"),
      score: row.final_score ?? row.score ?? row.total ?? row.points ?? row.raw_score ?? row.aggregate ?? null,
    }));
  }, [tourStandings, corpsById]);

  const divisionRows = useMemo(() => {
    const divisions = tourStandings?.divisions || tourStandings?.division_standings || {};
    if (!divisions || typeof divisions !== "object" || Array.isArray(divisions)) return [];
    return Object.entries(divisions).map(([division, rows]) => ({
      division,
      rows: Array.isArray(rows)
        ? rows.map((row: any, idx: number) => ({
          rank: row.rank ?? idx + 1,
          corps: row.corps_name
            || row.display_name
            || (row.corps_id ? (corpsById[row.corps_id]?.display_name || `Corps • ${row.corps_id.slice(0, 8)}`) : "Unknown"),
          score: row.final_score ?? row.score ?? row.total ?? row.points ?? row.raw_score ?? row.aggregate ?? null,
        }))
        : [],
    }));
  }, [tourStandings, corpsById]);

  const handleCreateSeason = async () => {
    if (!newSeasonName.trim()) return;
    setCreating(true);
    try {
      const s = await v1.createSeason(newSeasonName.trim());
      setSeasons(prev => [...prev, s]);
      setNewSeasonId("");
      setShowCreate(false);
      navigate(`/seasons/${s.season_id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleRegisterCorps = async (corpsId: string) => {
    if (!seasonId) return;
    try {
      await v1.registerSeasonCorps(seasonId, corpsId);
      const updated = await v1.getSeason(seasonId);
      setDetail(updated);
      setAssignments(updated.divisions || {});
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleAddShow = async (showSlug: string) => {
    if (!seasonId) return;
    try {
      const updated = await v1.addSeasonShow(seasonId, showSlug);
      setDetail(updated);
      setAssignments(updated.divisions || {});
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRemoveShow = async (showSlug: string) => {
    if (!seasonId) return;
    try {
      const updated = await v1.removeSeasonShow(seasonId, showSlug);
      setDetail(updated);
      setAssignments(updated.divisions || {});
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleFinalize = async () => {
    if (!seasonId) return;
    setFinalizing(true);
    try {
      const result = await v1.runShowDraft(seasonId);
      await v1.applyDraft(seasonId, result.assignments);
      const updated = await v1.getSeason(seasonId);
      setDetail(updated);
      setAssignments(updated.divisions || {});
    } catch (e: any) {
      setError(e.message);
    } finally {
      setFinalizing(false);
    }
  };

  const handleSaveConfig = async () => {
    if (!seasonId) return;
    setSavingConfig(true);
    try {
      const updated = await v1.updateSeasonConfig(seasonId, config);
      setDetail(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSavingConfig(false);
    }
  };

  const handleLockSeason = async () => {
    if (!seasonId) return;
    setLocking(true);
    try {
      const updated = await v1.lockSeason(seasonId);
      setDetail(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLocking(false);
    }
  };

  const handleStartTour = async () => {
    if (!seasonId) return;
    setStartingTour(true);
    try {
      const updated = await v1.startSeasonTour(seasonId);
      setDetail(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setStartingTour(false);
    }
  };

  const handleEnterFinals = async () => {
    if (!seasonId) return;
    setEnteringFinals(true);
    try {
      await v1.enterSeasonFinals(seasonId);
      const updated = await v1.getSeason(seasonId);
      setDetail(updated);
      setActiveTab("finals");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setEnteringFinals(false);
    }
  };

  const handleDeleteSeason = async (sid: string) => {
    if (!confirm(`Delete season "${sid}"? This cannot be undone.`)) return;
    try {
      await v1.deleteSeason(sid);
      setSeasons(prev => prev.filter(s => s.season_id !== sid));
      if (seasonId === sid) navigate("/seasons");
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading) return <div className="page-loading">Loading seasons...</div>;

  const errorBanner = error ? (
    <div className="error-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
      <span>{error}</span>
      <div>
        <button className="small" onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
        <button className="small" onClick={() => setError("")} style={{ marginLeft: 8 }}>Dismiss</button>
      </div>
    </div>
  ) : null;

  // Detail view
  if (seasonId && detail) {
    const tabs: TabItem[] = [
      { key: "setup", label: "Setup" },
      { key: "camps", label: "Winter Camps" },
      { key: "ready", label: "Ready Check" },
    ];
    if (isTouring) {
      tabs.push({ key: "tour", label: "Tour Status" });
    }
    if (canFinals) {
      tabs.push({ key: "finals", label: "Finals" });
    }
    tabs.push({ key: "standings", label: "Standings" });

    const registeredCorps = detail.registered_corps || [];
    const unregisteredCorps = corps.filter(c => c.corps_type !== "system" && !registeredCorps.includes(c.corps_id));
    const selectedShows = detail.shows || [];
    const availableShows = showThreads.filter(t => t.status === "published" || t.status === "approved" || t.status === "needs_review");
    const hasDraftAssignments = Object.values(assignments).some(a => a.length > 0);
    const canStartTour = registeredCorps.length > 0
      && selectedShows.length > 0
      && hasDraftAssignments
      && Boolean(detail.locked);
    const checklist = [
      { key: "corps", label: "Add Corps", done: registeredCorps.length > 0 },
      { key: "shows", label: "Add Shows", done: selectedShows.length > 0 },
      { key: "draft", label: "Finalize Draft", done: hasDraftAssignments },
      { key: "config", label: "Competition Settings", done: !!config.corps_per_contest && !!config.required_scores },
      { key: "lock", label: "Lock & Prepare", done: Boolean(detail.locked) },
      { key: "tour", label: "Start Tour", done: detail.metadata?.status === "touring" },
    ];

    return (
      <div className="page-content season-workshop">
        {errorBanner}
        <div className="page-header">
          <button className="back-btn" onClick={() => navigate("/seasons")}>Back</button>
          <h1 className="page-title" style={{ marginBottom: 0 }}>
            {detail.name || slugToTitle(detail.season_id)}
          </h1>
          <button className="small danger" style={{ marginLeft: "auto" }} onClick={() => handleDeleteSeason(detail.season_id)}>
            Delete Season
          </button>
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

        {activeTab === "setup" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Setup Checklist">
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {checklist.map(step => (
                  <div key={step.key} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <Badge variant={step.done ? "success" : "warning"}>
                      {step.done ? "Done" : "Pending"}
                    </Badge>
                    <span style={{ fontWeight: 600 }}>{step.label}</span>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel title="Season Details">
              <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
                <Badge variant={(detail as any).status === "active" ? "success" : "default"}>
                  {formatStatus((detail as any).status || "planning")}
                </Badge>
                <span>{registeredCorps.length} corps registered</span>
              </div>

              {detail.metadata && Object.keys(detail.metadata).filter(k => k !== "name").length > 0 && (
                <pre style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap", marginBottom: 16 }}>
                  {JSON.stringify(Object.fromEntries(Object.entries(detail.metadata).filter(([k]) => k !== "name")), null, 2)}
                </pre>
              )}
            </Panel>

            <Panel title="Corps" style={{ marginTop: 16 }}>
              {registeredCorps.length === 0 && <p className="empty">No corps registered yet. Add corps below to get started.</p>}
              {registeredCorps.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
                  {registeredCorps.map(id => {
                    const c = corpsById[id];
                    const colors = c?.color_scheme || { primary: "#334155", secondary: "#475569", accent: "#94a3b8" };
                    const name = c?.display_name || `Corps ${id.slice(0, 8)}`;
                    const monogram = name.charAt(0).toUpperCase();
                    return (
                      <div
                        key={id}
                        onClick={() => navigate(`/corps/${id}`)}
                        style={{
                          width: 160,
                          padding: "16px 12px",
                          borderRadius: 8,
                          background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
                          borderLeft: `4px solid ${colors.accent}`,
                          cursor: "pointer",
                          transition: "transform 0.15s, box-shadow 0.15s",
                          color: "#fff",
                          textShadow: "0 1px 2px rgba(0,0,0,0.4)",
                        }}
                        onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.3)"; }}
                        onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = ""; }}
                      >
                        <div style={{
                          fontSize: 48,
                          fontWeight: 800,
                          lineHeight: 1,
                          marginBottom: 8,
                          fontFamily: "var(--font-display, inherit)",
                          opacity: 0.9,
                        }}>
                          {monogram}
                        </div>
                        <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.2 }}>{name}</div>
                        {c?.mascot && (
                          <div style={{ fontSize: 11, opacity: 0.75, marginTop: 4 }}>{c.mascot}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
              {unregisteredCorps.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {unregisteredCorps.map(c => {
                    const colors = c.color_scheme || { primary: "#334155", secondary: "#475569", accent: "#94a3b8" };
                    return (
                      <button
                        key={c.corps_id}
                        className="small"
                        onClick={() => handleRegisterCorps(c.corps_id)}
                        style={{
                          borderColor: colors.accent,
                          color: colors.accent,
                        }}
                      >
                        + {c.display_name}
                      </button>
                    );
                  })}
                </div>
              )}
              {unregisteredCorps.length === 0 && registeredCorps.length > 0 && (
                <p className="text-muted" style={{ fontSize: 12 }}>All available corps are registered.</p>
              )}
            </Panel>

            <Panel title="Assign Shows" style={{ marginTop: 16 }}>
              {availableShows.length === 0 && <p className="empty">No shows available. Publish a show first.</p>}
              {availableShows.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
                  {availableShows.map(show => (
                    <button
                      key={show.slug}
                      className="small"
                      onClick={() => handleAddShow(show.slug)}
                      disabled={selectedShows.includes(show.slug)}
                    >
                      + {slugToTitle(show.slug)}
                    </button>
                  ))}
                </div>
              )}
              {selectedShows.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
                  {selectedShows.map(showSlug => (
                    <span key={showSlug} style={{
                      display: "inline-flex", alignItems: "center", gap: 6,
                      padding: "4px 10px", borderRadius: 4,
                      background: "var(--bg-secondary, #1e293b)",
                      border: "1px solid var(--border)",
                      fontSize: 12,
                    }}>
                      {slugToTitle(showSlug)}
                      <button
                        onClick={() => handleRemoveShow(showSlug)}
                        style={{
                          background: "none", border: "none", cursor: "pointer",
                          color: "var(--text-muted)", fontSize: 14, padding: 0, lineHeight: 1,
                        }}
                        title="Remove show"
                      >
                        x
                      </button>
                    </span>
                  ))}
                </div>
              )}
              {selectedShows.length === 0 && <p className="empty">No shows assigned yet.</p>}

              {registeredCorps.length > 0 && selectedShows.length > 0 && (
                <>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginBottom: 16 }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid var(--border)" }}>
                        <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 600 }}>Corps</th>
                        <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 600 }}>Assigned Show</th>
                      </tr>
                    </thead>
                    <tbody>
                      {registeredCorps.map(cid => {
                        const c = corpsById[cid];
                        const assignedShow = Object.entries(assignments).find(
                          ([, corpsIds]) => corpsIds.includes(cid)
                        );
                        return (
                          <tr key={cid} style={{ borderBottom: "1px solid var(--border)" }}>
                            <td style={{ padding: "8px 12px" }}>
                              {c?.display_name || `Corps ${cid.slice(0, 8)}`}
                            </td>
                            <td style={{ padding: "8px 12px", color: assignedShow ? "var(--text)" : "var(--text-muted)" }}>
                              {assignedShow ? slugToTitle(assignedShow[0]) : "\u2014"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  <button
                    className="primary"
                    onClick={handleFinalize}
                    disabled={finalizing || registeredCorps.length === 0 || selectedShows.length === 0}
                    style={{ padding: "10px 24px" }}
                  >
                    {finalizing ? "Finalizing..." : "Finalize Corps and Shows"}
                  </button>
                </>
              )}
            </Panel>

            <Panel title="Competition Settings" style={{ marginTop: 16 }}>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <label style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }}>
                  Corps per Contest
                  <input
                    type="number"
                    min={2}
                    value={config.corps_per_contest}
                    onChange={(e) => setConfig(prev => ({ ...prev, corps_per_contest: Number(e.target.value) }))}
                  />
                </label>
                <label style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }}>
                  Required Scores
                  <input
                    type="number"
                    min={1}
                    value={config.required_scores}
                    onChange={(e) => setConfig(prev => ({ ...prev, required_scores: Number(e.target.value) }))}
                  />
                </label>
                <button className="small" onClick={handleSaveConfig} disabled={savingConfig}>
                  {savingConfig ? "Saving..." : "Save Settings"}
                </button>
              </div>
            </Panel>

            <Panel title="Lock & Prepare" style={{ marginTop: 16 }}>
              <p className="text-muted">Locking freezes configuration and prepares schedule generation.</p>
              <button className="small primary" onClick={handleLockSeason} disabled={locking || detail.locked}>
                {detail.locked ? "Locked" : locking ? "Locking..." : "Lock Season"}
              </button>
            </Panel>

            <Panel title="Start Tour" style={{ marginTop: 16 }}>
              {!canStartTour && (
                <p className="text-muted" style={{ marginBottom: 8 }}>Complete all setup steps before starting the tour.</p>
              )}
              <button
                className="primary"
                onClick={handleStartTour}
                disabled={!canStartTour || startingTour || detail.metadata?.status === "touring"}
                style={{ opacity: canStartTour ? 1 : 0.5 }}
              >
                {detail.metadata?.status === "touring" ? "Tour Active" : startingTour ? "Starting..." : "Start Tour"}
              </button>
              {detail.schedule && detail.schedule.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <h4 style={{ marginBottom: 8 }}>Schedule</h4>
                  <DataTable<Record<string, unknown>>
                    columns={[
                      { key: "competition_id", label: "Competition" },
                      { key: "show_slug", label: "Show", render: (v) => slugToTitle(String(v || "")) },
                      { key: "corps_ids", label: "Corps", render: (v) => Array.isArray(v) ? `${v.length} corps` : "0 corps" },
                    ]}
                    data={detail.schedule as Record<string, unknown>[]}
                    emptyMessage="No schedule generated."
                  />
                </div>
              )}
            </Panel>
          </div>
        )}

        {activeTab === "camps" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Winter Camps — Corps Readiness">
              {registeredCorps.length === 0 && <p className="empty">Register corps first.</p>}
              {registeredCorps.map(id => {
                const c = corps.find(x => x.corps_id === id);
                return (
                  <div key={id} style={{ padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 600 }} title={id}>{c?.display_name || `Corps • ${id.slice(0, 8)}`}</span>
                      <Badge variant={c?.state === "winter_camps" ? "warning" : c?.state === "on_tour" ? "success" : "default"}>
                        {formatStatus(c?.state || "unknown")}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </Panel>
          </div>
        )}

        {activeTab === "ready" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Ready Check">
              <p className="hint" style={{ marginBottom: 16 }}>
                All corps must be in RUN_THROUGH mode before starting the tour.
              </p>
              <div className="ready-check-list">
                {registeredCorps.map(id => {
                  const c = corps.find(x => x.corps_id === id);
                  const isReady = c?.state === "on_tour" || c?.state === "winter_camps";
                  return (
                    <div key={id} className={`ready-check-item ${isReady ? "ready" : "not-ready"}`}>
                      <span className={`ready-check-dot ${isReady ? "ready" : "not-ready"}`} />
                      <span style={{ flex: 1, fontWeight: 500 }} title={id}>{c?.display_name || `Corps • ${id.slice(0, 8)}`}</span>
                      <Badge variant={isReady ? "success" : "warning"}>
                        {isReady ? "Ready" : "Not Ready"}
                      </Badge>
                    </div>
                  );
                })}
              </div>
              {registeredCorps.length > 0 && (
                <button
                  className="primary"
                  style={{ marginTop: 16, fontFamily: "var(--font-display)", fontSize: 14, padding: "12px 24px" }}
                  disabled={registeredCorps.length === 0}
                >
                  Start Tour
                </button>
              )}
            </Panel>
          </div>
        )}

        {activeTab === "tour" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Tour Timeline">
              {tourLoading && <p className="empty">Loading tour data...</p>}
              {!tourLoading && tourSchedule.length === 0 && <p className="empty">No schedule available yet.</p>}
              {!tourLoading && tourSchedule.length > 0 && (
                <TourSchedule
                  schedule={tourSchedule}
                  statusByCompetition={competitionStatus}
                  currentCompetitionId={currentCompetitionId}
                  renderTitle={(slug) => slugToTitle(slug)}
                />
              )}
            </Panel>

            <Panel title="Overall Rankings" style={{ marginTop: 16 }}>
              {overallRows.length === 0 ? (
                <p className="empty">No standings available yet.</p>
              ) : (
                <DataTable<Record<string, unknown>>
                  columns={[
                    { key: "rank", label: "Rank", sortable: true, render: (v) => <strong>#{String(v)}</strong> },
                    { key: "corps", label: "Corps", sortable: true },
                    { key: "score", label: "Score", sortable: true, render: (v) => v == null ? "—" : Number(v).toFixed(2) },
                  ]}
                  data={overallRows as Record<string, unknown>[]}
                  defaultSortKey="rank"
                  emptyMessage="No standings available yet."
                />
              )}
            </Panel>

            <Panel title="Division Standings" style={{ marginTop: 16 }}>
              {divisionRows.length === 0 && <p className="empty">No division standings available yet.</p>}
              {divisionRows.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  {divisionRows.map((division) => (
                    <div key={division.division}>
                      <h4 style={{ marginBottom: 8 }}>{slugToTitle(String(division.division))}</h4>
                      <DataTable<Record<string, unknown>>
                        columns={[
                          { key: "rank", label: "Rank", sortable: true, render: (v) => <strong>#{String(v)}</strong> },
                          { key: "corps", label: "Corps", sortable: true },
                          { key: "score", label: "Score", sortable: true, render: (v) => v == null ? "—" : Number(v).toFixed(2) },
                        ]}
                        data={division.rows as Record<string, unknown>[]}
                        defaultSortKey="rank"
                        emptyMessage="No standings available yet."
                      />
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>
        )}

        {activeTab === "finals" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Finals Control">
              <p className="text-muted" style={{ marginBottom: 12 }}>
                Finals require corps to meet the required score threshold before winner declaration.
              </p>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button className="primary" onClick={handleEnterFinals} disabled={enteringFinals}>
                  {enteringFinals ? "Entering Finals..." : "Enter Finals"}
                </button>
                <button className="secondary" onClick={() => navigate(`/finals/${detail.season_id}`)}>
                  View Finals
                </button>
              </div>
              <div style={{ marginTop: 12, fontSize: 12 }}>
                Required scores per corps: <strong>{config.required_scores}</strong>
              </div>
            </Panel>
          </div>
        )}

        {activeTab === "standings" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Competitions">
              {competitions.length === 0 && <p className="empty">No competitions for this season.</p>}
              {competitions.length > 0 && (
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                  {competitions.map(c => (
                    <button
                      key={c.competition_id}
                      className={selectedCompetitionId === c.competition_id ? "primary" : "small"}
                      onClick={() => {
                        setSelectedCompetitionId(c.competition_id);
                        setBreakdowns({});
                      }}
                    >
                      {slugToTitle(c.show_slug)}
                    </button>
                  ))}
                </div>
              )}
              {selectedCompetitionId && (
                <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                  <button className={standingsView === "standings" ? "small primary" : "small"} onClick={() => setStandingsView("standings")}>Standings</button>
                  <button className={standingsView === "recap" ? "small primary" : "small"} onClick={() => setStandingsView("recap")}>Recap</button>
                </div>
              )}

              {standingsLoading && <p className="empty">Loading standings...</p>}

              {!standingsLoading && standingsView === "standings" && standings && (
                <>
                  <DataTable<v1.V1StandingEntry & Record<string, unknown>>
                    columns={[
                      { key: "rank", label: "Rank", sortable: true, render: (v) => <strong>#{String(v)}</strong> },
                      { key: "display_name", label: "Corps", sortable: true, render: (_v, row) => row.display_name || `Corps • ${row.corps_id.slice(0, 8)}` },
                      { key: "final_score", label: "Final", sortable: true, render: (v) => Number(v).toFixed(2) },
                      { key: "raw_score", label: "Raw", sortable: true, render: (v) => Number(v).toFixed(2) },
                      { key: "penalties_total", label: "Pen", sortable: true, render: (_v, row) => Number(row.penalties_total || 0).toFixed(1) },
                      { key: "caption_scores", label: "Captions", render: (v) => (
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          {Object.entries((v as Record<string, number>) || {}).map(([cap, score]) => (
                            <span key={cap} className={`standings-caption caption-${cap}`}>{cap}: {Number(score).toFixed(1)}</span>
                          ))}
                        </div>
                      ) },
                    ]}
                    data={standings.results as (v1.V1StandingEntry & Record<string, unknown>)[]}
                    onRowClick={async (row) => {
                      if (!selectedCompetitionId) return;
                      if (breakdowns[row.corps_id] !== undefined) return;
                      const bd = await v1.getCorpsBreakdown(selectedCompetitionId, row.corps_id);
                      setBreakdowns(prev => ({ ...prev, [row.corps_id]: bd }));
                    }}
                    emptyMessage="No standings data."
                  />
                  {Object.entries(breakdowns).map(([corpsId, breakdown]) => (
                    breakdown ? (
                      <Panel key={corpsId} title={`Breakdown — ${corpsById[corpsId]?.display_name || corpsId.slice(0, 8)}`} style={{ marginTop: 12 }}>
                        <DataTable<Record<string, unknown>>
                          columns={[
                            { key: "caption", label: "Caption" },
                            { key: "score", label: "Score" },
                            { key: "weight", label: "Weight" },
                            { key: "weighted", label: "Weighted" },
                            { key: "commentary", label: "Commentary" },
                          ]}
                          data={Object.entries(breakdown.caption_scores).map(([cap, data]) => ({
                            caption: cap,
                            score: Number(data.score).toFixed(1),
                            weight: `${(Number(data.weight) * 100).toFixed(0)}%`,
                            weighted: Number(data.weighted).toFixed(2),
                            commentary: breakdown.commentary?.[cap] || "",
                          }))}
                          emptyMessage="No breakdown data."
                        />
                      </Panel>
                    ) : null
                  ))}
                </>
              )}

              {!standingsLoading && standingsView === "recap" && recap && (
                <DataTable<Record<string, unknown>>
                  columns={[
                    { key: "rank", label: "Rank", sortable: true, render: (v) => <strong>#{String(v)}</strong> },
                    { key: "corps_name", label: "Corps", sortable: true },
                    { key: "raw_total", label: "Raw", sortable: true, render: (v) => Number(v).toFixed(1) },
                    { key: "penalties_total", label: "Pen", sortable: true, render: (v) => Number(v).toFixed(1) },
                    { key: "final_score", label: "Final", sortable: true, render: (v) => Number(v).toFixed(1) },
                  ]}
                  data={recap as Record<string, unknown>[]}
                  emptyMessage="No recap data."
                />
              )}
            </Panel>
          </div>
        )}
      </div>
    );
  }

  if (seasonId && detailLoading) {
    return <div className="page-loading">Loading season details...</div>;
  }

  if (seasonId && !detail && !detailLoading) {
    return (
      <div className="page-content season-workshop">
        {errorBanner}
        <div className="page-header">
          <button className="back-btn" onClick={() => navigate("/seasons")}>Back</button>
          <h1 className="page-title">{slugToTitle(seasonId)}</h1>
        </div>
        <p className="empty">Season not found or failed to load.</p>
      </div>
    );
  }

  // List view
  return (
    <div className="page-content season-workshop">
      {errorBanner}
      <div className="page-header">
        <h1 className="page-title">Season Workshop</h1>
      </div>

      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{seasons.length}</span>
          <span className="summary-label">Seasons</span>
        </div>
      </div>

      <div style={{ marginBottom: 16, display: "flex", gap: 8 }}>
        {!showCreate ? (
          <button className="primary" onClick={() => setShowCreate(true)}>+ New Season</button>
        ) : (
          <form onSubmit={e => { e.preventDefault(); handleCreateSeason(); }} style={{ display: "flex", gap: 8 }}>
            <input
              className="library-search"
              style={{ width: 240 }}
              placeholder="Season name (e.g. Summer Tour 2026)..."
              value={newSeasonName}
              onChange={e => setNewSeasonId(e.target.value)}
              autoFocus
            />
            <button type="submit" className="primary" disabled={creating || !newSeasonName.trim()}>Create</button>
            <button type="button" onClick={() => setShowCreate(false)}>Cancel</button>
          </form>
        )}
      </div>

      <Panel title="All Seasons">
        <DataTable<v1.V1Season & Record<string, unknown>>
          columns={[
            {
              key: "name",
              label: "Season",
              render: (v, row) => <span>{String(v || slugToTitle((row as v1.V1Season).season_id))}</span>,
            },
            {
              key: "status",
              label: "Status",
              render: v => (
                <Badge variant={v === "active" ? "success" : v === "completed" ? "info" : "default"}>
                  {formatStatus(String(v || "planning"))}
                </Badge>
              ),
            },
            {
              key: "registered_corps_count",
              label: "Corps",
              render: v => <span>{v != null ? String(v) : "—"}</span>,
            },
          ]}
          data={seasons as (v1.V1Season & Record<string, unknown>)[]}
          onRowClick={row => navigate(`/seasons/${row.season_id}`)}
          emptyMessage="No seasons found"
        />
      </Panel>
    </div>
  );
}
