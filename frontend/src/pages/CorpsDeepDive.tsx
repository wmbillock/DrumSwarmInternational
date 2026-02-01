import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type { Show, AgentSession, ChatMessage, Scoresheet, CorpsMode } from "../types";
import * as api from "../services/api";
import * as v1 from "../services/v1";
import { useWebSocket } from "../hooks/useWebSocket";
import { ModeIndicator } from "../components/ModeIndicator";
import { useMode } from "../contexts/ModeContext";
import { TheRoster } from "../components/TheRoster";
import { TheSheets } from "../components/TheSheets";
import { TheField } from "../components/TheField";
import { TheReps } from "../components/TheReps";
import { TheTape } from "../components/TheTape";
import { TheBanquet } from "../components/TheBanquet";
import { TheStand } from "../components/TheStand";
import { TheChart } from "../components/TheChart";
import { TheBooks } from "../components/TheBooks";
import { TheSeason } from "../components/TheSeason";
import { TheHistory } from "../components/TheHistory";

function formatRole(role: string): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function timeAgo(ts?: string): string {
  if (!ts) return "";
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 0) return "just now";
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

const STATUS_LABELS: Record<string, string> = {
  winter_camps: "Winter Camps",
  on_tour: "On Tour",
  in_progress: "In Progress",
};

function StatusBadge({ status }: { status: string }) {
  const label = STATUS_LABELS[status] || status;
  return <span className={`badge ${status}`}>{label}</span>;
}

function TierBadge({ tier }: { tier?: string }) {
  if (!tier) return null;
  return <span className={`tier-badge tier-${tier}`}>{tier}</span>;
}

const COMMAND_GROUPS: Record<string, { label: string; commands: { cmd: string; label: string; desc: string; style?: string }[] }> = {
  control: {
    label: "Field Commands",
    commands: [
      { cmd: "resume_hut", label: "Resume, Hut!", desc: "Wake all agents, begin work", style: "primary" },
      { cmd: "attention", label: "Attention!", desc: "All agents report status" },
      { cmd: "at_ease", label: "At Ease", desc: "Finish tasks then idle" },
      { cmd: "dismissed", label: "Dismissed", desc: "Disband the corps", style: "danger" },
    ],
  },
  rehearsal: {
    label: "Rehearsal Mode",
    commands: [
      { cmd: "basics", label: "Basics", desc: "Manual override: basics mode" },
      { cmd: "sectionals", label: "Sectionals", desc: "Manual override: sectionals" },
      { cmd: "full_ensemble", label: "Full Ensemble", desc: "Manual override: full ensemble" },
      { cmd: "run_through", label: "Run Through", desc: "Manual override: run through" },
    ],
  },
  execution: {
    label: "Execution",
    commands: [
      { cmd: "go_on_tour", label: "Go On Tour", desc: "Autonomous execution", style: "primary" },
      { cmd: "return_to_camps", label: "Return to Camps", desc: "Back to planning" },
    ],
  },
  system: {
    label: "System",
    commands: [
      { cmd: "metronome_tick", label: "Tick", desc: "Reclaim stale work" },
      { cmd: "merge_check", label: "Merge", desc: "Check completed work" },
    ],
  },
};

function SwarmControlPanel({ corpsId, onCommand }: { corpsId: string; onCommand: (corpsId: string, cmd: string) => void }) {
  const [lastResult, setLastResult] = useState<string | null>(null);
  const handleCommand = async (cmd: string) => {
    try {
      const result = await v1.executeCorpsCommand(corpsId, cmd);
      setLastResult(`${result.command}: ${result.detail}`);
      onCommand(corpsId, cmd);
    } catch (e) {
      setLastResult(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    }
    setTimeout(() => setLastResult(null), 4000);
  };

  return (
    <div className="control-panel">
      {Object.entries(COMMAND_GROUPS).map(([, group]) => (
        <div key={group.label} className="control-group">
          <span className="control-group-label">{group.label}</span>
          <div className="control-buttons">
            {group.commands.map(c => (
              <button key={c.cmd} className={`control-btn ${c.style || ""}`} title={c.desc} onClick={() => handleCommand(c.cmd)}>
                {c.label}
              </button>
            ))}
          </div>
        </div>
      ))}
      {lastResult && <div className="control-result">{lastResult}</div>}
    </div>
  );
}

type TabKey = "command" | "roster" | "sheets" | "field" | "reps" | "tape" | "banquet" | "stand" | "chart" | "books" | "season" | "history";

const TAB_LABELS: Record<TabKey, string> = {
  command: "Command Room",
  roster: "Roster",
  sheets: "Sheets",
  field: "Field",
  reps: "Reps",
  tape: "Tape",
  banquet: "Banquet",
  stand: "Stand",
  chart: "Chart",
  books: "Books",
  season: "Season",
  history: "History",
};

export function CorpsDeepDive() {
  const { corpsId, tab } = useParams<{ corpsId: string; tab?: string }>();
  const navigate = useNavigate();
  const activeTab = (tab as TabKey) || "command";

  const [show, setShow] = useState<Show | null>(null);
  const [corpsMode, setCorpsMode] = useState<CorpsMode | undefined>();
  const [roster, setRoster] = useState<AgentSession[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [scoresheet, setScoresheet] = useState<Scoresheet | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [chatTarget, setChatTarget] = useState("executive_director");
  const [showSwarmChatter, setShowSwarmChatter] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const { connected, events, clearEvents } = useWebSocket(corpsId || null);
  const { config: modeConfig, refreshMode } = useMode();

  const loadData = useCallback(async (isRefresh = false) => {
    if (!corpsId) return;
    if (!isRefresh) {
      setRoster([]); setChatHistory([]); setScoresheet(null);
      clearEvents();
    }

    // Load corps info
    try {
      const corps = await v1.getCorps(corpsId);
      setCorpsMode(corps.mode as CorpsMode | undefined);
      if (corpsId) refreshMode(corpsId);
    } catch {}

    // Load roster, chat, and scoresheet (independent of show)
    const [r, c, sc] = await Promise.allSettled([
      v1.getCorpsRoster(corpsId),
      v1.getCorpsChatHistory(corpsId),
      v1.getCorpsScoresheet(corpsId),
    ]);
    if (r.status === "fulfilled") setRoster(r.value);
    if (c.status === "fulfilled") setChatHistory(c.value);
    if (sc.status === "fulfilled") setScoresheet(sc.value);

    // Find show for this corps
    try {
      const shows = await api.listShows();
      const s = shows.find((s: any) => s.corps_id === corpsId);
      if (s) {
        const fullShow = await api.getShow(s.id);
        setShow({ ...s, ...fullShow } as Show);
      }
    } catch {}
  }, [corpsId, clearEvents, refreshMode]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSendChat = async (content: string, toRole: string) => {
    if (!corpsId) return;
    await api.sendChat(corpsId, content, toRole);
    // Re-fetch chat history to pick up the sent message and any agent responses
    try {
      const history = await v1.getCorpsChatHistory(corpsId);
      setChatHistory(history);
    } catch {}
  };

  const handleSend = () => {
    if (!chatInput.trim()) return;
    handleSendChat(chatInput.trim(), chatTarget);
    setChatInput("");
  };

  // Build unified chat
  const nicknameByRole: Record<string, string> = {};
  for (const a of roster) { if (a.nickname) nicknameByRole[a.role] = a.nickname; }
  const seenIds = new Set<string>();
  const allChat: { id?: string; from: string; nickname?: string; content: string; time?: string; internal?: boolean }[] = [];
  for (const m of chatHistory) {
    if (!seenIds.has(m.id)) {
      seenIds.add(m.id);
      const isInternal = m.from_role !== "user" && !m.to_role?.includes("user");
      allChat.push({ id: m.id, from: m.from_role, nickname: nicknameByRole[m.from_role], content: m.body || m.subject, time: m.created_at, internal: isInternal });
    }
  }
  for (const e of events) {
    if (e.type === "chat" || e.type === "agent_response") {
      const id = (e as Record<string, unknown>).message_id as string | undefined;
      const contentKey = id || `ws:${e.from_role || e.role}:${(e.content || "").slice(0, 100)}`;
      if (seenIds.has(contentKey)) continue;
      seenIds.add(contentKey);
      const isInternal = e.type === "agent_response" && !id;
      allChat.push({ from: e.from_role || e.role || "agent", nickname: e.nickname, content: e.content || "", time: undefined, internal: isInternal });
    }
  }
  const visibleChat = showSwarmChatter ? allChat : allChat.filter(m => !m.internal);
  const hiddenCount = allChat.length - allChat.filter(m => !m.internal).length;

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [allChat.length]);

  const uniqueRoles = [...new Set(roster.map(r => r.role))].sort();
  const activeAgents = roster.filter(r => r.status === "active");
  const deadAgents = roster.filter(r => r.status !== "active");

  const setTab = (t: TabKey) => {
    if (t === "command") {
      navigate(`/corps/${corpsId}`);
    } else {
      navigate(`/corps/${corpsId}/${t}`);
    }
  };

  return (
    <div className="show-detail">
      <div className="show-detail-header">
        <button className="back-btn" onClick={() => navigate("/")}>&larr;</button>
        <div className="show-detail-title">
          <h2>{show?.title ? (show.title.length > 60 ? show.title.slice(0, 60) + "..." : show.title) : corpsId?.slice(0, 8)}</h2>
          {show?.corps_name && <span className="corps-badge">{show.corps_name}</span>}
          {show && <StatusBadge status={show.status} />}
          <ModeIndicator mode={corpsMode} />
          <span className={`ws-dot ${connected ? "connected" : "disconnected"}`}
                title={connected ? "WebSocket connected" : "WebSocket disconnected"} />
        </div>
        <div className="show-detail-actions">
          <button className="small" onClick={() => loadData(true)}>Refresh</button>
          {show?.status === "active" && (
            <button className="small primary" onClick={() => show && api.toggleTour(show.id, true)}>Go On Tour</button>
          )}
        </div>
      </div>

      {corpsId && <SwarmControlPanel corpsId={corpsId} onCommand={() => loadData(true)} />}

      {/* Tab bar */}
      <div className="corps-tabs">
        {(Object.keys(TAB_LABELS) as TabKey[]).map(t => (
          <button key={t} className={`tab ${activeTab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="corps-tab-content">
        {activeTab === "command" && (
          <div className="two-pane">
            {/* Chat pane */}
            <div className="pane-left">
              <div className="chat-panel">
                <div className="chat-toolbar">
                  <label className="chatter-toggle" title="Show internal agent-to-agent messages">
                    <input type="checkbox" checked={showSwarmChatter} onChange={e => setShowSwarmChatter(e.target.checked)} />
                    <span>Swarm chatter{hiddenCount > 0 ? ` (${hiddenCount})` : ""}</span>
                  </label>
                </div>
                <div className="chat-messages">
                  {visibleChat.length === 0 && (
                    <div className="chat-empty">
                      <p>Send a message to start talking to the swarm.</p>
                      <p className="hint">Choose a role, or talk to the ED to direct the whole team.</p>
                      {deadAgents.length > 0 && activeAgents.length === 0 && (
                        <p className="hint warning">All agents stopped. Sending a message will revive the target.</p>
                      )}
                    </div>
                  )}
                  {visibleChat.map((m, i) => (
                    <div key={m.id || i} className={`chat-msg ${m.from === "user" ? "user" : "agent"} ${m.internal ? "internal" : ""}`}>
                      <div className="chat-msg-header">
                        <span className="chat-sender">{m.from === "user" ? "You" : (m.nickname || formatRole(m.from))}</span>
                        {m.internal && <span className="chat-badge-internal">internal</span>}
                        {m.time && <span className="chat-time">{timeAgo(m.time)}</span>}
                      </div>
                      <div className="chat-msg-body">{m.content}</div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>
                <div className="chat-input-row">
                  <select value={chatTarget} onChange={e => setChatTarget(e.target.value)} title="Target agent role">
                    {uniqueRoles.length > 0 ? uniqueRoles.map(r => (
                      <option key={r} value={r}>{nicknameByRole[r] ? `${nicknameByRole[r]} (${formatRole(r)})` : formatRole(r)}</option>
                    )) : (
                      <option value="executive_director">Executive Director</option>
                    )}
                  </select>
                  <input
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleSend()}
                    placeholder="Message the swarm..."
                  />
                  <button className="primary" onClick={handleSend} disabled={!chatInput.trim()}>Send</button>
                </div>
              </div>
            </div>

            {/* Sidebar: agents + status */}
            <div className="pane-right">
              <div className="agents-panel-compact" style={{ padding: 8 }}>
                <h4 className="section-label">Agents ({activeAgents.length}/{roster.length})</h4>
                {activeAgents.map(a => (
                  <div key={a.id} className="agent-row-compact">
                    <TierBadge tier={a.model_tier} />
                    <span className="agent-nickname">{a.nickname || formatRole(a.role)}</span>
                    <span className="agent-role-small">{formatRole(a.role)}</span>
                  </div>
                ))}
                {deadAgents.length > 0 && (
                  <>
                    <h4 className="section-label">Stopped ({deadAgents.length})</h4>
                    {deadAgents.map(a => (
                      <div key={a.id} className="agent-row-compact stopped">
                        <TierBadge tier={a.model_tier} />
                        <span className="agent-nickname">{a.nickname || formatRole(a.role)}</span>
                      </div>
                    ))}
                  </>
                )}
                {roster.length === 0 && <p className="empty">No agents spawned.</p>}

                {/* Mode quick actions */}
                {modeConfig && (
                  <div style={{ marginTop: 12 }}>
                    <h4 className="section-label">{modeConfig.label} Actions</h4>
                    <div className="mode-quick-actions">
                      {modeConfig.quickActions.map(action => (
                        <button
                          key={action.command}
                          className={`control-btn small ${action.style || ""}`}
                          title={action.description}
                          onClick={async () => {
                            if (!corpsId) return;
                            if (action.command.startsWith("mode:")) {
                              const newMode = action.command.slice(5) as CorpsMode;
                              try {
                                await v1.switchCorpsMode(corpsId, newMode);
                                setCorpsMode(newMode);
                                refreshMode(corpsId);
                              } catch {}
                            } else {
                              try {
                                await v1.executeCorpsCommand(corpsId, action.command);
                                loadData(true);
                              } catch {}
                            }
                          }}
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggested prompts */}
                {modeConfig && visibleChat.length === 0 && (
                  <div style={{ marginTop: 12 }}>
                    <h4 className="section-label">Suggested</h4>
                    <div className="suggested-prompts">
                      {modeConfig.suggestedPrompts.map(prompt => (
                        <button
                          key={prompt}
                          className="suggested-prompt-btn"
                          onClick={() => { setChatInput(prompt); }}
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Scores summary */}
                {scoresheet && (
                  <div style={{ marginTop: 12 }}>
                    <h4 className="section-label">Score</h4>
                    <div className={`composite-score ${scoresheet.composite.needs_escalation ? "escalation" : scoresheet.composite.needs_rework ? "rework" : "healthy"}`}>
                      <div className="composite-main">
                        <span className="composite-value">{scoresheet.composite.final_score.toFixed(1)}</span>
                        <span className="composite-label">Final</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "roster" && corpsId && <TheRoster corpsId={corpsId} />}
        {activeTab === "sheets" && corpsId && <TheSheets corpsId={corpsId} />}
        {activeTab === "field" && <TheField rootSegmentId={show?.segment_root_id || null} />}
        {activeTab === "reps" && corpsId && <TheReps corpsId={corpsId} />}
        {activeTab === "tape" && corpsId && <TheTape corpsId={corpsId} />}
        {activeTab === "banquet" && corpsId && <TheBanquet corpsId={corpsId} />}
        {activeTab === "stand" && corpsId && <TheStand corpsId={corpsId} />}
        {activeTab === "chart" && corpsId && <TheChart corpsId={corpsId} />}
        {activeTab === "books" && corpsId && <TheBooks corpsId={corpsId} />}
        {activeTab === "season" && <TheSeason />}
        {activeTab === "history" && corpsId && <TheHistory corpsId={corpsId} />}
      </div>
    </div>
  );
}
