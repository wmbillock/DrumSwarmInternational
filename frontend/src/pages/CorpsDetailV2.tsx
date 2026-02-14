import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Tabs, Panel, DataTable, Badge } from "../ui";
import { API_BASE } from "../config";
import { ShowDetail } from "../components/ShowDetail";
import { HiringProgress } from "../components/HiringProgress";
import { AwardsPanel } from "../components/AwardsPanel";
import { badgeForRunStatus, badgeForShowStatus, formatMode, formatStatus, formatTimestamp, slugToTitle } from "../utils/formatters";
import * as v1 from "../services/v1";
import { useWebSocket } from "../hooks/useWebSocket";
import { StrategyPanel } from "../components/StrategyPanel";

const TAB_ITEMS = [
  { key: "overview", label: "Overview" },
  { key: "roster", label: "Roster" },
  { key: "runs", label: "Runs" },
  { key: "shows", label: "Shows" },
  { key: "history", label: "History" },
  { key: "strategy", label: "Strategy" },
  { key: "seance", label: "Seance" },
];

export function CorpsDetailV2() {
  const { corpsId, tab } = useParams<{ corpsId: string; tab?: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(tab || "overview");
  const [corps, setCorps] = useState<v1.V1CorpsDetail | null>(null);
  const [runs, setRuns] = useState<v1.V1Run[]>([]);
  const [history, setHistory] = useState<v1.V1HistoryIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshToken, setRefreshToken] = useState(0);
  const [awardToast, setAwardToast] = useState<{ name: string; description: string; recipient: string } | null>(null);
  const { lastMessage } = useWebSocket(corpsId || null);

  useEffect(() => {
    if (!corpsId) return;
    const ac = new AbortController();

    setLoading(true);
    setError("");
    v1.getCorps(corpsId, ac.signal)
      .then(setCorps)
      .catch((e) => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => setLoading(false));

    v1.listRuns(corpsId, ac.signal)
      .then(setRuns)
      .catch(() => {});

    v1.getCorpsHistory(corpsId, ac.signal)
      .then(setHistory)
      .catch(() => {});

    return () => ac.abort();
  }, [corpsId, refreshToken]);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    navigate(`/corps/${corpsId}/${key}`, { replace: true });
  };

  const refreshCorps = useCallback(() => {
    if (!corpsId) return;
    v1.getCorps(corpsId).then(setCorps).catch(() => {});
  }, [corpsId]);

  useEffect(() => {
    if (!lastMessage || lastMessage.type !== "award.unlocked") return;
    const name = String(lastMessage.name || "Achievement unlocked");
    const description = String(lastMessage.description || "");
    const recipient = String(lastMessage.recipient_name || "");
    setAwardToast({ name, description, recipient });
    const timer = setTimeout(() => setAwardToast(null), 8000);
    return () => clearTimeout(timer);
  }, [lastMessage]);

  if (loading) return <div className="page-loading">Loading corps...</div>;
  if (error) {
    return (
      <div className="page-error">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
      </div>
    );
  }
  if (!corps) return <div className="page-error">Corps not found</div>;

  return (
    <div className="page-content">
      {awardToast && (
        <div className="award-toast">
          <div className="award-toast-title">{awardToast.name}</div>
          <div className="award-toast-body">{awardToast.description}</div>
          <div className="award-toast-meta">{awardToast.recipient}</div>
          <button className="award-toast-close" onClick={() => setAwardToast(null)}>Dismiss</button>
        </div>
      )}
      <div className="page-header" style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button className="back-btn" onClick={() => navigate("/corps")}>Back</button>
        {(corps as any).logo_path && (
          <img
            src={`${API_BASE}/generated_images/${(corps as any).logo_path.split("/").pop()}`}
            alt={`${corps.display_name} logo`}
            style={{ width: 40, height: 40, borderRadius: 6, objectFit: "cover" }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        )}
        <h2>{corps.display_name}</h2>
        <Badge variant={corps.state === "on_tour" ? "success" : "default"}>{formatStatus(corps.state)}</Badge>
      </div>

      <Tabs active={activeTab} onChange={handleTabChange} items={TAB_ITEMS} />

      <div style={{ marginTop: 16 }}>
        {activeTab === "overview" && (
          <OverviewTab corps={corps} onStateChange={refreshCorps} />
        )}
        {activeTab === "roster" && (
          <RosterTab corpsId={corpsId!} />
        )}
        {activeTab === "runs" && (
          <RunsTab corpsId={corpsId!} runs={runs} navigate={navigate} />
        )}
        {activeTab === "shows" && (
          <ShowsTab history={history} />
        )}
        {activeTab === "history" && (
          <HistoryTab corps={corps} history={history} corpsId={corpsId!} />
        )}
        {activeTab === "strategy" && (
          <StrategyPanel corpsId={corpsId!} />
        )}
        {activeTab === "seance" && (
          <SeanceTab corpsId={corpsId!} />
        )}
      </div>
    </div>
  );
}

function OverviewTab({ corps, onStateChange }: { corps: v1.V1CorpsDetail; onStateChange?: () => void }) {
  const [logoGenerating, setLogoGenerating] = useState(false);
  const [staffing, setStaffing] = useState<v1.StaffingStatus | null>(null);
  const [awards, setAwards] = useState<v1.V1Award[]>([]);

  const lifecycle = ["initializing", "winter_camps", "on_tour", "ready_for_contest", "completed"];

  useEffect(() => {
    v1.getStaffingStatus(corps.corps_id)
      .then(setStaffing)
      .catch(() => {});
  }, [corps.corps_id]);

  useEffect(() => {
    v1.listAwards({ corps_id: corps.corps_id, recipient_type: "corps" })
      .then(setAwards)
      .catch(() => setAwards([]));
  }, [corps.corps_id]);

  return (
    <div>
      <Panel title="Corps Info">
        <table className="styled-table">
          <tbody>
            <tr>
              <td className="cell-primary">ID</td>
              <td className="mono" title={corps.corps_id}>Corps • {corps.corps_id.slice(0, 8)}</td>
            </tr>
            <tr><td className="cell-primary">State</td><td>{formatStatus(corps.state)}</td></tr>
            {corps.mode && <tr><td className="cell-primary">Mode</td><td>{formatMode(corps.mode)}</td></tr>}
            {corps.rehearsal_mode && <tr><td className="cell-primary">Rehearsal</td><td>{formatMode(corps.rehearsal_mode)}</td></tr>}
            <tr><td className="cell-primary">Roster Size</td><td>{corps.roster_size}</td></tr>
            {corps.mascot && <tr><td className="cell-primary">Mascot</td><td>{corps.mascot}</td></tr>}
            <tr><td className="cell-primary">History Entries</td><td>{corps.history_count}</td></tr>
            {(corps as any).logo_path && (
              <tr><td className="cell-primary">Logo</td><td>
                <img
                  src={`${API_BASE}/generated_images/${(corps as any).logo_path.split("/").pop()}`}
                  alt="Logo"
                  style={{ width: 64, height: 64, borderRadius: 8, objectFit: "cover" }}
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              </td></tr>
            )}
          </tbody>
        </table>
        <button
          style={{ marginTop: 8, fontSize: 12 }}
          disabled={logoGenerating}
          onClick={async () => {
            setLogoGenerating(true);
            try {
              await v1.generateCorpsLogo(corps.corps_id);
              onStateChange?.();
            } catch { /* ignore */ }
            setLogoGenerating(false);
          }}
        >
          {logoGenerating
            ? "Generating..."
            : (corps as any).logo_path
              ? "Regenerate Logo (SDXL)"
              : "Generate Logo"}
        </button>
      </Panel>

      {corps.current_show && (
        <Panel title="Current Show" className="mt-16">
          <table className="styled-table">
            <tbody>
              <tr><td className="cell-primary">Title</td><td><strong>{corps.current_show.title}</strong></td></tr>
              <tr><td className="cell-primary">Status</td><td>
                <Badge variant={badgeForShowStatus(corps.current_show.status)}>
                  {formatStatus(corps.current_show.status)}
                </Badge>
              </td></tr>
              {corps.current_show.description && (
                <tr><td className="cell-primary">Description</td><td style={{ fontSize: 13, color: "var(--text-secondary)" }}>{corps.current_show.description}</td></tr>
              )}
            </tbody>
          </table>
        </Panel>
      )}

      <Panel title="Lifecycle Status" className="mt-16">
        <div className="lifecycle-bar">
          {(() => {
            // Map non-lifecycle states to the nearest lifecycle step
            const stateMap: Record<string, string> = {
              active: "on_tour",
              commissioned: "initializing",
              contending: "on_tour",
              touring: "on_tour",
              disbanded: "completed",
            };
            const mapped = stateMap[corps.state] || corps.state;
            const currentIdx = lifecycle.indexOf(mapped);
            return lifecycle.map((state, idx) => (
              <div
                key={state}
                className={`lifecycle-step${mapped === state ? " active" : idx < currentIdx ? " done" : ""}`}
              >
                {formatStatus(state)}
              </div>
            ));
          })()}
        </div>
      </Panel>

      <CorpsStatusPanel corps={corps} staffing={staffing} />

      <Panel title="Rehearsal Progression" className="mt-16">
        {(() => {
          const stages = [
            { key: "basics", label: "Basics", desc: "Fundamentals and warm-ups" },
            { key: "sectionals", label: "Sectionals", desc: "Section-specific practice" },
            { key: "full_ensemble", label: "Full Ensemble", desc: "Full corps integration" },
            { key: "run_through", label: "Run Through", desc: "Complete performance runs" },
          ];
          const currentIdx = stages.findIndex((s) => s.key === corps.rehearsal_mode);
          return (
            <div>
              <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
                {stages.map((s, i) => (
                  <div
                    key={s.key}
                    style={{
                      flex: 1,
                      padding: "8px 10px",
                      borderRadius: 6,
                      background: i === currentIdx
                        ? "var(--accent-bg, rgba(100,180,255,0.15))"
                        : i < currentIdx
                          ? "rgba(100,200,100,0.1)"
                          : "var(--bg-elevated, rgba(255,255,255,0.03))",
                      border: i === currentIdx
                        ? "1px solid var(--accent)"
                        : "1px solid var(--border)",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: i === currentIdx ? 700 : 400 }}>
                      {i < currentIdx ? "\u2713 " : ""}{s.label}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>{s.desc}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {currentIdx >= 0
                  ? `Currently in ${stages[currentIdx].label} phase. Progression happens automatically during competition.`
                  : "No active rehearsal phase. Rehearsal begins when the corps starts preparing for a show."}
              </div>
            </div>
          );
        })()}
      </Panel>

      <AwardsPanel title="Corps Achievements" awards={awards} emptyText="No corps achievements yet." />

      <FeedbackPanel corpsId={corps.corps_id} />

      {corps.philosophy && (
        <Panel title="Philosophy" className="mt-16">
          <p style={{ fontSize: 13, color: "var(--text-secondary)", fontStyle: "italic" }}>
            {corps.philosophy}
          </p>
        </Panel>
      )}
    </div>
  );
}

function FeedbackPanel({ corpsId }: { corpsId: string }) {
  const navigate = useNavigate();
  const [feedback, setFeedback] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState("");

  const handleSend = async () => {
    if (!feedback.trim()) return;
    setSending(true);
    setResult("");
    try {
      await v1.sendCorpsFeedback(corpsId, feedback.trim());
      setResult("Feedback delivered to ED");
      setFeedback("");
    } catch (e: unknown) {
      setResult(e instanceof Error ? e.message : "Failed to send");
    } finally {
      setSending(false);
    }
  };

  const handleChat = async () => {
    try {
      const session = await v1.startEDChat(corpsId);
      navigate(`/critique/ed-chat-${corpsId}/${corpsId}`);
    } catch (e: unknown) {
      setResult(e instanceof Error ? e.message : "Failed to start chat");
    }
  };

  return (
    <Panel title="Feedback" className="mt-16">
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <textarea
          value={feedback}
          onChange={e => setFeedback(e.target.value)}
          placeholder="Send feedback to the Executive Director..."
          rows={3}
          style={{ flex: 1, fontFamily: "var(--font-body)", fontSize: 13, padding: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)", color: "var(--text-primary)", borderRadius: 4 }}
        />
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button className="primary" onClick={handleSend} disabled={sending || !feedback.trim()}>
          {sending ? "Sending..." : "Send to ED"}
        </button>
        <button onClick={handleChat}>Chat with ED</button>
      </div>
      {result && <div style={{ marginTop: 8, fontSize: 13, color: "var(--text-secondary)" }}>{result}</div>}
    </Panel>
  );
}

function CorpsStatusPanel({ corps, staffing }: { corps: v1.V1CorpsDetail; staffing: v1.StaffingStatus | null }) {
  const [workStats, setWorkStats] = useState<{ total_logs: number; recent_logs: number; active_agents: number } | null>(null);

  useEffect(() => {
    // Fetch work log stats for this corps
    v1.fetchV1<{ total_logs: number; recent_logs: number; active_agents: number }>(`/corps/${corps.corps_id}/work-stats`)
      .then(setWorkStats)
      .catch(() => {});
  }, [corps.corps_id]);

  const isWinterCamps = corps.state === "winter_camps";
  const staffComplete = staffing ? staffing.hired >= staffing.total_roles : false;

  return (
    <Panel title="Corps Status" className="mt-16">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
        {/* Lifecycle */}
        <div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 2 }}>Lifecycle</div>
          <Badge variant={corps.state === "on_tour" ? "success" : "default"}>
            {formatStatus(corps.state)}
          </Badge>
        </div>

        {/* Mode */}
        <div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 2 }}>Mode</div>
          <span>{corps.mode ? formatMode(corps.mode) : "Idle"}</span>
        </div>

        {/* Rehearsal Phase */}
        {corps.rehearsal_mode && (
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 2 }}>Rehearsal</div>
            <span>{formatMode(corps.rehearsal_mode)}</span>
          </div>
        )}

        {/* Current Show */}
        {corps.current_show && (
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 2 }}>Current Show</div>
            <span>{corps.current_show.title}</span>
            <Badge variant={badgeForShowStatus(corps.current_show.status)} style={{ marginLeft: 6 }}>
              {corps.current_show.status}
            </Badge>
          </div>
        )}

        {/* Staffing */}
        {staffing && (
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 2 }}>Staffing</div>
            <span>
              {staffing.hired}/{staffing.total_roles} roles filled
              {staffComplete && <Badge variant="success" style={{ marginLeft: 6 }}>Complete</Badge>}
            </span>
          </div>
        )}

        {/* Work Activity */}
        {workStats && (
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 2 }}>Activity</div>
            <span>
              {workStats.active_agents} active agents, {workStats.recent_logs} recent actions
            </span>
          </div>
        )}
      </div>

      {/* Staffing progress bar during winter camps */}
      {isWinterCamps && (
        <div style={{ marginTop: 12 }}>
          <HiringProgress corpsId={corps.corps_id} />
        </div>
      )}
    </Panel>
  );
}

function RunsTab({ corpsId, runs, navigate }: { corpsId: string; runs: v1.V1Run[]; navigate: ReturnType<typeof useNavigate> }) {
  const [compHistory, setCompHistory] = useState<v1.V1CompetitionHistoryEntry[]>([]);
  const [postMortems, setPostMortems] = useState<v1.V1PostMortemSummary[]>([]);
  const [selectedPM, setSelectedPM] = useState<v1.V1PostMortemDetail | null>(null);
  const [pmLoading, setPmLoading] = useState(false);

  useEffect(() => {
    v1.getCorpsCompetitionHistory(corpsId)
      .then(setCompHistory)
      .catch(() => {});
    v1.getCorpsPostMortems(corpsId)
      .then(setPostMortems)
      .catch(() => {});
  }, [corpsId]);

  // Compute summary stats
  const completedComps = compHistory.filter((c) => c.status === "completed" && c.placement != null);
  const wins = completedComps.filter((c) => c.placement === 1).length;
  const totalCompleted = completedComps.length;
  const avgScore = totalCompleted > 0
    ? completedComps.reduce((sum, c) => sum + (c.final_score || 0), 0) / totalCompleted
    : 0;
  const bestPlacement = totalCompleted > 0
    ? Math.min(...completedComps.map((c) => c.placement!))
    : null;

  return (
    <div>
      {/* Summary stats */}
      {totalCompleted > 0 && (
        <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
          <div className="stat-card">
            <div className="stat-value">{totalCompleted}</div>
            <div className="stat-label">Competitions</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{wins}</div>
            <div className="stat-label">Wins</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{avgScore.toFixed(1)}</div>
            <div className="stat-label">Avg Score</div>
          </div>
          {bestPlacement != null && (
            <div className="stat-card">
              <div className="stat-value">#{bestPlacement}</div>
              <div className="stat-label">Best Place</div>
            </div>
          )}
        </div>
      )}

      {/* Competition History Table */}
      <Panel title="Competition History">
        <DataTable<v1.V1CompetitionHistoryEntry & Record<string, unknown>>
          columns={[
            { key: "round", label: "Round", render: (v) => `R${v}` },
            { key: "show_slug", label: "Show", render: (v) => slugToTitle(String(v || "")) },
            { key: "season_id", label: "Season", render: (v) => slugToTitle(String(v || "")) },
            { key: "placement", label: "Place", render: (v) => v != null ? <strong>#{String(v)}</strong> : "-" },
            { key: "final_score", label: "Score", render: (v) => v != null ? Number(v).toFixed(2) : "-" },
            {
              key: "status",
              label: "Status",
              render: (v) => (
                <Badge variant={v === "completed" ? "success" : "default"}>
                  {formatStatus(String(v))}
                </Badge>
              ),
            },
          ]}
          data={compHistory as (v1.V1CompetitionHistoryEntry & Record<string, unknown>)[]}
          onRowClick={(row) => {
            const comp = row as unknown as v1.V1CompetitionHistoryEntry;
            navigate(`/tour/${comp.competition_id}`);
          }}
          emptyMessage="No competitions found"
        />
      </Panel>

      {/* Post-Mortems */}
      {postMortems.length > 0 && (
        <Panel title="Season Post-Mortems" className="mt-16">
          {!selectedPM ? (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {postMortems.map((pm) => (
                <button
                  key={pm.season_id}
                  className="btn btn-secondary"
                  disabled={pmLoading}
                  onClick={() => {
                    setPmLoading(true);
                    v1.getPostMortem(pm.season_id, corpsId)
                      .then(setSelectedPM)
                      .catch(() => {})
                      .finally(() => setPmLoading(false));
                  }}
                >
                  {slugToTitle(pm.season_id)}
                </button>
              ))}
            </div>
          ) : (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <strong>{slugToTitle(selectedPM.season_id)}</strong>
                <button className="btn btn-ghost" onClick={() => setSelectedPM(null)}>Back</button>
              </div>
              <div className="post-mortem-content" style={{ whiteSpace: "pre-wrap", fontFamily: "var(--font-mono)", fontSize: "0.85rem", lineHeight: 1.6, padding: 16, background: "var(--bg-secondary)", borderRadius: 8, maxHeight: 600, overflow: "auto" }}>
                {selectedPM.content}
              </div>
            </div>
          )}
        </Panel>
      )}

      {/* Legacy Runs */}
      {runs.length > 0 && (
        <Panel title="Agent Runs" className="mt-16">
          <DataTable<v1.V1Run & Record<string, unknown>>
            columns={[
              { key: "run_id", label: "Run", render: (v) => <span className="mono" title={String(v)}>{String(v).slice(0, 8)}</span> },
              { key: "show_slug", label: "Show", render: (v) => slugToTitle(String(v || "")) },
              {
                key: "status",
                label: "Status",
                render: (v) => (
                  <Badge variant={badgeForRunStatus(String(v))}>
                    {formatStatus(String(v))}
                  </Badge>
                ),
              },
              { key: "started_at", label: "Started", render: (v) => {
                const ts = formatTimestamp(String(v || ""));
                return <span title={ts.title}>{ts.label}</span>;
              } },
            ]}
            data={runs as (v1.V1Run & Record<string, unknown>)[]}
            onRowClick={(row) => navigate(`/runs/${row.run_id}`)}
            emptyMessage="No runs"
          />
        </Panel>
      )}
    </div>
  );
}

function ShowsTab({ history }: { history: v1.V1HistoryIndex | null }) {
  if (!history || history.entries.length === 0) {
    return <p className="empty">No show participation recorded</p>;
  }

  const showEntries = history.entries.filter((e) => e.show_slug);
  return (
    <Panel title="Show Participation">
      <DataTable<v1.V1HistoryEntry & Record<string, unknown>>
        columns={[
          { key: "show_slug", label: "Show", render: (v) => slugToTitle(String(v || "")) },
          { key: "season_id", label: "Season", render: (v) => slugToTitle(String(v || "")) },
          { key: "placement", label: "Placement", render: (v) => <strong>#{String(v)}</strong> },
          { key: "final_score", label: "Score", render: (v) => Number(v).toFixed(2) },
        ]}
        data={showEntries as (v1.V1HistoryEntry & Record<string, unknown>)[]}
        emptyMessage="No shows found"
      />
    </Panel>
  );
}

function HistoryTab({ corps, history, corpsId }: { corps: v1.V1CorpsDetail; history: v1.V1HistoryIndex | null; corpsId: string }) {
  const [selectedEntry, setSelectedEntry] = useState<v1.V1HistoryEntry | null>(null);

  if (selectedEntry) {
    return (
      <ShowDetail
        corpsId={corpsId}
        entry={selectedEntry}
        onBack={() => setSelectedEntry(null)}
      />
    );
  }

  return (
    <div>
      {/* Show List */}
      {history && history.entries.length > 0 && (
        <Panel title="Past Shows">
          <DataTable<v1.V1HistoryEntry & Record<string, unknown>>
            columns={[
              { key: "show_slug", label: "Show", render: (v) => slugToTitle(String(v || "")) },
              { key: "season_id", label: "Season", render: (v) => slugToTitle(String(v || "")) },
              { key: "placement", label: "Place", render: (v) => <strong>#{String(v)}</strong> },
              { key: "final_score", label: "Score", render: (v) => Number(v).toFixed(2) },
              { key: "artifacts", label: "Artifacts", render: (v) => String(Object.keys(v as Record<string, string>).length) },
              { key: "runs", label: "Runs", render: (v) => String((v as string[]).length) },
            ]}
            data={history.entries as (v1.V1HistoryEntry & Record<string, unknown>)[]}
            onRowClick={(row) => setSelectedEntry(row as unknown as v1.V1HistoryEntry)}
            emptyMessage="No shows found"
          />
        </Panel>
      )}

      {/* Past Placements from corps.yaml */}
      {corps.history.length > 0 && (
        <Panel title="Placement History" className="mt-16">
          <DataTable<v1.V1Placement & Record<string, unknown>>
            columns={[
              { key: "season_id", label: "Season" },
              { key: "placement", label: "Place", render: (v) => <strong>#{String(v)}</strong> },
              { key: "final_score", label: "Score", render: (v) => Number(v).toFixed(2) },
              { key: "notes", label: "Notes" },
            ]}
            data={corps.history as (v1.V1Placement & Record<string, unknown>)[]}
            emptyMessage="No placement history"
          />
        </Panel>
      )}

      {corps.history.length === 0 && (!history || history.entries.length === 0) && (
        <p className="empty">No history available for {corpsId}</p>
      )}
    </div>
  );
}


interface RosterMember {
  session_id: string;
  role: string;
  nickname: string | null;
  model_tier: string;
  status: string;
  group: string;
  tenure_days: number | null;
  performer_id: string | null;
  performer_name: string | null;
  performer_trust_score: number | null;
  performer_status: string | null;
  performer_total_sessions: number | null;
  performer_successful_sessions: number | null;
}

interface AgentDetail {
  session_id: string;
  role: string;
  nickname: string | null;
  model_tier: string;
  status: string;
  group: string;
  tenure_days: number | null;
  started_at: string | null;
  ended_at: string | null;
  error: string | null;
  performer_name: string | null;
  performer_trust_score: number | null;
  performer_status: string | null;
  performer_total_sessions: number | null;
  performer_successful_sessions: number | null;
  message_count: number;
  rep_count: number;
  score_contributions: number;
  recent_logs: {
    id: string;
    event_type: string;
    phase: string | null;
    details: string | null;
    timestamp: string | null;
  }[];
  memories: {
    id: string;
    key: string;
    content: string;
    created_at: string | null;
  }[];
}

function RosterTab({ corpsId }: { corpsId: string }) {
  const [roster, setRoster] = useState<RosterMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<AgentDetail | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentError, setAgentError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  const loadRoster = useCallback(() => {
    v1.fetchV1<RosterMember[]>(`/corps/${corpsId}/roster`)
      .then(setRoster)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [corpsId]);

  useEffect(() => { loadRoster(); }, [loadRoster]);

  const handleAction = async (action: string, sessionId: string) => {
    setActionMsg("");
    try {
      await v1.fetchV1(`/corps/${corpsId}/roster/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setActionMsg(`${action} successful`);
      loadRoster();
    } catch (e: unknown) {
      setActionMsg(e instanceof Error ? e.message : "Action failed");
    }
  };

  const handleRowClick = async (member: RosterMember) => {
    setModalOpen(true);
    setAgentLoading(true);
    setAgentError("");
    setSelectedAgent(null);
    try {
      const detail = await v1.fetchV1<AgentDetail>(`/corps/${corpsId}/agents/${member.session_id}`);
      setSelectedAgent(detail);
    } catch (e: unknown) {
      setAgentError(e instanceof Error ? e.message : "Failed to load agent details");
    } finally {
      setAgentLoading(false);
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelectedAgent(null);
    setAgentError("");
  };

  if (loading) return <p>Loading roster...</p>;

  const groups = ["Administrative Staff", "Instructional Staff", "Performing Members", "Other"];

  return (
    <div>
      {actionMsg && <div className="info-banner" style={{ marginBottom: 12 }}>{actionMsg}</div>}
      {groups.map((group) => {
        const members = roster.filter((m) => m.group === group);
        if (members.length === 0) return null;
        return (
          <Panel key={group} title={group} className="mt-16">
            <DataTable<RosterMember & Record<string, unknown>>
              columns={[
                { key: "role", label: "Role", render: (v) => String(v).replace(/_/g, " ") },
                { key: "nickname", label: "Nickname" },
                { key: "model_tier", label: "Tier", render: (v) => <Badge variant="default">{String(v).toUpperCase()}</Badge> },
                { key: "performer_name", label: "Agent Identity" },
                { key: "performer_trust_score", label: "Trust", render: (v) => v != null ? Number(v).toFixed(1) : "-" },
                { key: "status", label: "Status", render: (v) => <Badge variant={v === "active" ? "success" : "default"}>{String(v)}</Badge> },
                { key: "tenure_days", label: "Tenure", render: (v) => v != null ? `${v}d` : "-" },
                { key: "session_id", label: "", render: (_v, row) => (
                  <span style={{ display: "flex", gap: 4 }}>
                    <button
                      className="btn-sm"
                      onClick={(e) => { e.stopPropagation(); handleRowClick(row as RosterMember); }}
                    >
                      Details
                    </button>
                    {(row as RosterMember).performer_id && (
                      <>
                        <button className="btn-sm" onClick={(e) => { e.stopPropagation(); handleAction("dismiss", (row as RosterMember).session_id); }}>Dismiss</button>
                        <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleAction("fire", (row as RosterMember).session_id); }}>Fire</button>
                      </>
                    )}
                  </span>
                )},
              ]}
              data={members as (RosterMember & Record<string, unknown>)[]}
              emptyMessage="No members"
            />
          </Panel>
        );
      })}
      {roster.length === 0 && <p className="empty">No roster data available</p>}

      {/* Agent Detail Modal */}
      {modalOpen && (
        <div
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
            display: "flex", justifyContent: "center", alignItems: "flex-start",
            paddingTop: 60, zIndex: 1000,
          }}
          onClick={closeModal}
        >
          <div
            style={{
              background: "var(--surface, #1a1a2e)", border: "1px solid var(--border)",
              borderRadius: 8, width: "90%", maxWidth: 700, maxHeight: "80vh",
              overflow: "auto", padding: 24,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {agentLoading ? (
              <p>Loading agent details...</p>
            ) : agentError ? (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <h2 style={{ margin: 0 }}>Error</h2>
                  <button className="secondary" onClick={closeModal} style={{ fontSize: 12 }}>Close</button>
                </div>
                <p className="text-muted">{agentError}</p>
              </div>
            ) : selectedAgent ? (
              <AgentDetailPanel agent={selectedAgent} onClose={closeModal} />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function AgentDetailPanel({ agent, onClose }: { agent: AgentDetail; onClose: () => void }) {
  const [activeSection, setActiveSection] = useState<"activity" | "memories">("activity");

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>
          {agent.nickname || agent.role.replace(/_/g, " ")}
        </h2>
        <button className="secondary" onClick={onClose} style={{ fontSize: 12 }}>Close</button>
      </div>

      {/* Identity */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase" }}>Role</div>
          <div>{agent.role.replace(/_/g, " ")}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase" }}>Model Tier</div>
          <Badge variant="default">{agent.model_tier.toUpperCase()}</Badge>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase" }}>Status</div>
          <Badge variant={agent.status === "active" ? "success" : "default"}>{agent.status}</Badge>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase" }}>Tenure</div>
          <div>{agent.tenure_days != null ? `${agent.tenure_days} days` : "-"}</div>
        </div>
        {agent.performer_name && (
          <>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase" }}>Agent Identity</div>
              <div>{agent.performer_name}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase" }}>Trust Score</div>
              <div>{agent.performer_trust_score?.toFixed(1) ?? "-"}</div>
            </div>
          </>
        )}
      </div>

      {/* Stats */}
      <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ textAlign: "center", padding: "8px 16px", border: "1px solid var(--border)", borderRadius: 6 }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{agent.message_count}</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Messages</div>
        </div>
        <div style={{ textAlign: "center", padding: "8px 16px", border: "1px solid var(--border)", borderRadius: 6 }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{agent.rep_count}</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Reps</div>
        </div>
        <div style={{ textAlign: "center", padding: "8px 16px", border: "1px solid var(--border)", borderRadius: 6 }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{agent.score_contributions}</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Scores</div>
        </div>
        {agent.performer_total_sessions != null && (
          <div style={{ textAlign: "center", padding: "8px 16px", border: "1px solid var(--border)", borderRadius: 6 }}>
            <div style={{ fontSize: 20, fontWeight: 700 }}>
              {agent.performer_successful_sessions}/{agent.performer_total_sessions}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Sessions Won</div>
          </div>
        )}
      </div>

      {agent.error && (
        <div className="error-banner" style={{ marginBottom: 16, fontSize: 12 }}>
          Last Error: {agent.error}
        </div>
      )}

      {/* Section tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button
          className={activeSection === "activity" ? "primary" : "secondary"}
          onClick={() => setActiveSection("activity")}
          style={{ fontSize: 12 }}
        >
          Activity ({agent.recent_logs.length})
        </button>
        <button
          className={activeSection === "memories" ? "primary" : "secondary"}
          onClick={() => setActiveSection("memories")}
          style={{ fontSize: 12 }}
        >
          Memories ({agent.memories.length})
        </button>
      </div>

      {/* Activity timeline */}
      {activeSection === "activity" && (
        <div style={{ maxHeight: 300, overflow: "auto" }}>
          {agent.recent_logs.length === 0 ? (
            <p className="text-muted">No activity recorded.</p>
          ) : (
            agent.recent_logs.map((log) => (
              <div key={log.id} style={{ padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <Badge variant="default">{log.event_type}</Badge>
                  <span className="text-muted">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : ""}
                  </span>
                </div>
                {log.details && (
                  <div style={{ marginTop: 4, color: "var(--text-secondary)", whiteSpace: "pre-wrap" }}>
                    {log.details.length > 200 ? log.details.slice(0, 200) + "..." : log.details}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Memories */}
      {activeSection === "memories" && (
        <div style={{ maxHeight: 300, overflow: "auto" }}>
          {agent.memories.length === 0 ? (
            <p className="text-muted">No memories stored.</p>
          ) : (
            agent.memories.map((mem) => (
              <div key={mem.id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{mem.key}</div>
                <div style={{ color: "var(--text-secondary)", whiteSpace: "pre-wrap" }}>
                  {mem.content.length > 300 ? mem.content.slice(0, 300) + "..." : mem.content}
                </div>
                <div className="text-muted" style={{ fontSize: 10, marginTop: 2 }}>
                  {mem.created_at ? new Date(mem.created_at).toLocaleString() : ""}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function SeanceTab({ corpsId }: { corpsId: string }) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const handleQuery = async () => {
    if (!query.trim() || loading) return;
    const q = query.trim();
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setQuery("");
    setLoading(true);
    try {
      const res = await v1.seanceQuery(corpsId, q);
      setMessages((prev) => [...prev, { role: "ed", text: res.message || res.error || "No response" }]);
    } catch (e: unknown) {
      setMessages((prev) => [...prev, { role: "error", text: e instanceof Error ? e.message : "Request failed" }]);
    }
    setLoading(false);
  };

  return (
    <Panel title="Ask the Executive Director">
      <p className="text-muted" style={{ marginBottom: 12, fontSize: 12 }}>
        Ask questions about this corps' history, state, and strategy. The ED responds in character using real corps data.
      </p>

      <div style={{ maxHeight: 400, overflow: "auto", marginBottom: 12 }}>
        {messages.length === 0 && !loading && (
          <p className="text-muted" style={{ textAlign: "center", padding: 20 }}>
            No messages yet. Ask a question to start.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              padding: "8px 12px",
              margin: "4px 0",
              borderRadius: 6,
              background: msg.role === "user"
                ? "var(--bg-hover, rgba(255,255,255,0.05))"
                : msg.role === "error"
                  ? "rgba(255,80,80,0.1)"
                  : "var(--bg-elevated, rgba(255,255,255,0.03))",
              borderLeft: msg.role === "user" ? "3px solid var(--accent)" : msg.role === "error" ? "3px solid var(--danger, #f44)" : "3px solid var(--success, #4a4)",
            }}
          >
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>
              {msg.role === "user" ? "You" : msg.role === "error" ? "Error" : "Executive Director"}
            </div>
            <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: 13 }}>
              {msg.text}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ padding: "8px 12px", color: "var(--text-muted)", fontStyle: "italic" }}>
            ED is thinking...
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleQuery()}
          placeholder="How is our brass section performing?"
          style={{ flex: 1 }}
          disabled={loading}
        />
        <button className="primary" onClick={handleQuery} disabled={loading || !query.trim()}>
          {loading ? "..." : "Ask"}
        </button>
      </div>
    </Panel>
  );
}
