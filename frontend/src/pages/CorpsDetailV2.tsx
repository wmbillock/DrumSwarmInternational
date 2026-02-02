import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Tabs, Panel, DataTable, Badge } from "../ui";
import { ShowDetail } from "../components/ShowDetail";
import * as v1 from "../services/v1";

const TAB_ITEMS = [
  { key: "overview", label: "Overview" },
  { key: "roster", label: "Roster" },
  { key: "runs", label: "Runs" },
  { key: "shows", label: "Shows" },
  { key: "history", label: "History" },
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

  useEffect(() => {
    if (!corpsId) return;
    const ac = new AbortController();

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
  }, [corpsId]);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    navigate(`/corps/${corpsId}/${key}`, { replace: true });
  };

  const refreshCorps = useCallback(() => {
    if (!corpsId) return;
    v1.getCorps(corpsId).then(setCorps).catch(() => {});
  }, [corpsId]);

  if (loading) return <div className="page-loading">Loading corps...</div>;
  if (error) return <div className="page-error"><div className="error-banner">{error}</div></div>;
  if (!corps) return <div className="page-error">Corps not found</div>;

  return (
    <div className="page-content">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate("/corps")}>Back</button>
        <h2>{corps.display_name}</h2>
        <Badge variant={corps.state === "on_tour" ? "success" : "default"}>{corps.state}</Badge>
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
          <RunsTab runs={runs} navigate={navigate} />
        )}
        {activeTab === "shows" && (
          <ShowsTab history={history} />
        )}
        {activeTab === "history" && (
          <HistoryTab corps={corps} history={history} corpsId={corpsId!} />
        )}
      </div>
    </div>
  );
}

function OverviewTab({ corps, onStateChange }: { corps: v1.V1CorpsDetail; onStateChange?: () => void }) {
  const [cmdLoading, setCmdLoading] = useState("");
  const [cmdResult, setCmdResult] = useState("");

  const exec = async (command: string) => {
    setCmdLoading(command);
    setCmdResult("");
    try {
      const res = await v1.executeCorpsCommand(corps.corps_id, command);
      setCmdResult(res.detail || "OK");
      onStateChange?.();
    } catch (e: unknown) {
      setCmdResult(e instanceof Error ? e.message : "Command failed");
    } finally {
      setCmdLoading("");
    }
  };

  const isWinterCamps = corps.state === "winter_camps";
  const isOnTour = corps.state === "on_tour";
  const isReadyForContest = corps.state === "ready_for_contest";

  return (
    <div>
      <Panel title="Corps Info">
        <table className="styled-table">
          <tbody>
            <tr><td className="cell-primary">ID</td><td className="mono">{corps.corps_id}</td></tr>
            <tr><td className="cell-primary">State</td><td>{corps.state}</td></tr>
            {corps.mode && <tr><td className="cell-primary">Mode</td><td>{corps.mode.replace("_", " ")}</td></tr>}
            {corps.rehearsal_mode && <tr><td className="cell-primary">Rehearsal</td><td>{corps.rehearsal_mode.replace("_", " ")}</td></tr>}
            <tr><td className="cell-primary">Roster Size</td><td>{corps.roster_size}</td></tr>
            {corps.mascot && <tr><td className="cell-primary">Mascot</td><td>{corps.mascot}</td></tr>}
            <tr><td className="cell-primary">History Entries</td><td>{corps.history_count}</td></tr>
          </tbody>
        </table>
      </Panel>

      {corps.current_show && (
        <Panel title="Current Show" className="mt-16">
          <table className="styled-table">
            <tbody>
              <tr><td className="cell-primary">Title</td><td><strong>{corps.current_show.title}</strong></td></tr>
              <tr><td className="cell-primary">Status</td><td>
                <Badge variant={corps.current_show.status === "active" ? "success" : corps.current_show.status === "completed" ? "info" : "default"}>
                  {corps.current_show.status}
                </Badge>
              </td></tr>
              {corps.current_show.description && (
                <tr><td className="cell-primary">Description</td><td style={{ fontSize: 13, color: "var(--text-secondary)" }}>{corps.current_show.description}</td></tr>
              )}
            </tbody>
          </table>
        </Panel>
      )}

      <Panel title="Lifecycle Controls" className="mt-16">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          {isWinterCamps && (
            <button className="primary" onClick={() => exec("go_on_tour")} disabled={!!cmdLoading}>
              {cmdLoading === "go_on_tour" ? "Starting..." : "Go On Tour"}
            </button>
          )}
          {isOnTour && (
            <>
              <button className="success" onClick={() => exec("ready_for_contest")} disabled={!!cmdLoading}>
                {cmdLoading === "ready_for_contest" ? "Preparing..." : "Ready for Contest"}
              </button>
              <button onClick={() => exec("return_to_camps")} disabled={!!cmdLoading}>
                {cmdLoading === "return_to_camps" ? "Returning..." : "Return to Camps"}
              </button>
            </>
          )}
          {isReadyForContest && (
            <>
              <button className="success" onClick={() => exec("complete_corps")} disabled={!!cmdLoading}>
                {cmdLoading === "complete_corps" ? "Completing..." : "Complete Corps"}
              </button>
              <button onClick={() => exec("return_to_tour")} disabled={!!cmdLoading}>
                {cmdLoading === "return_to_tour" ? "Resuming..." : "Back to Tour"}
              </button>
            </>
          )}
          <button onClick={() => exec("resume_hut")} disabled={!!cmdLoading}>
            {cmdLoading === "resume_hut" ? "Waking..." : "Resume, Hut!"}
          </button>
          <button onClick={() => exec("attention")} disabled={!!cmdLoading}>
            {cmdLoading === "attention" ? "Requesting..." : "Attention!"}
          </button>
          <button onClick={() => exec("metronome_tick")} disabled={!!cmdLoading}>
            Metronome Tick
          </button>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Rehearsal:</span>
          {["basics", "sectionals", "full_ensemble", "run_through"].map((mode) => (
            <button key={mode} className="small" onClick={() => exec(mode)} disabled={!!cmdLoading}>
              {mode.replace("_", " ")}
            </button>
          ))}
        </div>
        {cmdResult && (
          <div style={{ marginTop: 8, fontSize: 13, color: "var(--text-secondary)" }}>{cmdResult}</div>
        )}
      </Panel>

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

function RunsTab({ runs, navigate }: { runs: v1.V1Run[]; navigate: ReturnType<typeof useNavigate> }) {
  return (
    <Panel title="Run History">
      <DataTable<v1.V1Run & Record<string, unknown>>
        columns={[
          { key: "run_id", label: "Run", render: (v) => <span className="mono">{String(v).slice(0, 30)}</span> },
          { key: "show_slug", label: "Show" },
          {
            key: "status",
            label: "Status",
            render: (v) => (
              <Badge variant={v === "completed" ? "success" : v === "failed" ? "danger" : "warning"}>
                {String(v)}
              </Badge>
            ),
          },
          { key: "started_at", label: "Started", render: (v) => v ? new Date(String(v)).toLocaleString() : "" },
        ]}
        data={runs as (v1.V1Run & Record<string, unknown>)[]}
        onRowClick={(row) => navigate(`/runs/${row.run_id}`)}
        emptyMessage="No runs found for this corps"
      />
    </Panel>
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
          { key: "show_slug", label: "Show", render: (v) => String(v || "N/A") },
          { key: "season_id", label: "Season" },
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
              { key: "show_slug", label: "Show", render: (v) => String(v || "N/A") },
              { key: "season_id", label: "Season" },
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

function RosterTab({ corpsId }: { corpsId: string }) {
  const [roster, setRoster] = useState<RosterMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");

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
                { key: "performer_name", label: "Performer" },
                { key: "performer_trust_score", label: "Trust", render: (v) => v != null ? Number(v).toFixed(1) : "-" },
                { key: "status", label: "Status", render: (v) => <Badge variant={v === "active" ? "success" : "default"}>{String(v)}</Badge> },
                { key: "tenure_days", label: "Tenure", render: (v) => v != null ? `${v}d` : "-" },
                { key: "session_id", label: "Actions", render: (_v, row) => (
                  <span style={{ display: "flex", gap: 4 }}>
                    {(row as RosterMember).performer_id && (
                      <>
                        <button className="btn-sm" onClick={() => handleAction("dismiss", (row as RosterMember).session_id)}>Dismiss</button>
                        <button className="btn-sm btn-danger" onClick={() => handleAction("fire", (row as RosterMember).session_id)}>Fire</button>
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
    </div>
  );
}
