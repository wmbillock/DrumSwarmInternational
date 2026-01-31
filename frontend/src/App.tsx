import { useState, useEffect, useCallback, useRef } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import type { Show, AgentSession, WorkLogEntry, CoordinateNode, ChatMessage, WebSocketEvent } from "./types";
import * as api from "./services/api";
import "./App.css";

// --- Utility ---
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

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${status}`}>{status}</span>;
}

function TierBadge({ tier }: { tier?: string }) {
  if (!tier) return null;
  return <span className={`tier-badge tier-${tier}`}>{tier}</span>;
}

// --- Dashboard View ---
function Dashboard({
  shows, agents, workLog, onSelectShow, onCreateShow, onDeleteShow, onActivateShow, onBulkCleanup,
}: {
  shows: Show[];
  agents: AgentSession[];
  workLog: WorkLogEntry[];
  onSelectShow: (s: Show) => void;
  onCreateShow: (title: string, desc?: string) => void;
  onDeleteShow: (id: string) => void;
  onActivateShow: (id: string) => void;
  onBulkCleanup: () => void;
}) {
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);

  const activeShows = shows.filter(s => s.status === "active");
  const draftShows = shows.filter(s => s.status === "draft");
  const completedShows = shows.filter(s => s.status === "completed" || s.status === "archived");

  return (
    <div className="dashboard">
      {/* Summary bar */}
      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{shows.length}</span>
          <span className="summary-label">Shows</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{activeShows.length}</span>
          <span className="summary-label">Active</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{agents.length}</span>
          <span className="summary-label">Agents Online</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{workLog.length}</span>
          <span className="summary-label">Recent Events</span>
        </div>
      </div>

      {/* Shows section */}
      <div className="dash-section">
        <div className="dash-header">
          <h2>Shows</h2>
          <div className="header-actions">
            {shows.length > 3 && (
              <button className="small danger" onClick={onBulkCleanup}>Clean Up Old Shows</button>
            )}
            <button className="small primary" onClick={() => setShowCreateForm(!showCreateForm)}>
              {showCreateForm ? "Cancel" : "+ New Show"}
            </button>
          </div>
        </div>

        {showCreateForm && (
          <form className="create-form" onSubmit={e => {
            e.preventDefault();
            if (newTitle.trim()) {
              onCreateShow(newTitle.trim(), newDesc.trim() || undefined);
              setNewTitle(""); setNewDesc(""); setShowCreateForm(false);
            }
          }}>
            <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Show title..." autoFocus />
            <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Description (optional)" />
            <button type="submit" className="primary" disabled={!newTitle.trim()}>Create</button>
          </form>
        )}

        {shows.length === 0 && <p className="empty">No shows yet. Create one to get started.</p>}

        {activeShows.length > 0 && (
          <>
            <h3 className="section-label">Active</h3>
            <div className="show-grid">
              {activeShows.map(s => (
                <ShowCard key={s.id} show={s} onSelect={onSelectShow} onDelete={onDeleteShow} onActivate={onActivateShow} />
              ))}
            </div>
          </>
        )}

        {draftShows.length > 0 && (
          <>
            <h3 className="section-label">Drafts</h3>
            <div className="show-grid">
              {draftShows.map(s => (
                <ShowCard key={s.id} show={s} onSelect={onSelectShow} onDelete={onDeleteShow} onActivate={onActivateShow} />
              ))}
            </div>
          </>
        )}

        {completedShows.length > 0 && (
          <>
            <h3 className="section-label">Completed / Archived</h3>
            <div className="show-grid">
              {completedShows.map(s => (
                <ShowCard key={s.id} show={s} onSelect={onSelectShow} onDelete={onDeleteShow} onActivate={onActivateShow} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Two-column: Agents + Activity */}
      <div className="dash-row">
        <div className="dash-section flex-1">
          <h2>Active Agents ({agents.length})</h2>
          {agents.length === 0 && <p className="empty">No active agents. Activate a show to spawn agents.</p>}
          <div className="agent-list">
            {agents.slice(0, 30).map(a => (
              <div key={a.id} className="agent-row">
                <span className="agent-nickname">{a.nickname || formatRole(a.role)}</span>
                <span className="agent-role-small">{formatRole(a.role)}</span>
                <TierBadge tier={a.model_tier} />
                <span className="agent-time">{timeAgo(a.started_at)}</span>
              </div>
            ))}
            {agents.length > 30 && <p className="empty">...and {agents.length - 30} more</p>}
          </div>
        </div>

        <div className="dash-section flex-1">
          <h2>Recent Activity</h2>
          {workLog.length === 0 && <p className="empty">No activity yet.</p>}
          <div className="activity-list">
            {workLog.slice(0, 30).map(w => (
              <div key={w.id} className="activity-row">
                <span className="activity-type">{w.event_type}</span>
                <span className="activity-role">{formatRole(w.role)}</span>
                <span className="activity-detail">{w.details?.slice(0, 100)}</span>
                <span className="activity-time">{timeAgo(w.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ShowCard({ show, onSelect, onDelete, onActivate }: {
  show: Show; onSelect: (s: Show) => void; onDelete: (id: string) => void; onActivate: (id: string) => void;
}) {
  return (
    <div className={`show-card status-${show.status}`} onClick={() => onSelect(show)}>
      <div className="show-card-header">
        <h3 title={show.title}>{show.title.length > 60 ? show.title.slice(0, 60) + "..." : show.title}</h3>
        <StatusBadge status={show.status} />
      </div>
      {show.description && <p className="show-desc">{show.description.slice(0, 120)}</p>}
      <div className="show-stats">
        <span>{show.agents_active ?? 0} agents</span>
        <span>{(show.reps_completed ?? 0)}/{(show.reps_total ?? 0)} tasks done</span>
        {show.created_at && <span>{timeAgo(show.created_at)}</span>}
      </div>
      <div className="show-actions" onClick={e => e.stopPropagation()}>
        {show.status === "draft" && (
          <button className="small primary" onClick={() => onActivate(show.id)}>Activate</button>
        )}
        <button className="small danger" onClick={() => onDelete(show.id)}>Delete</button>
      </div>
    </div>
  );
}

// --- Show Detail View ---
function ShowDetail({
  show, roster, tree, workLog, chatHistory, wsEvents, connected,
  onSendChat, onBack, onToggleTour, onRefresh,
}: {
  show: Show;
  roster: AgentSession[];
  tree: CoordinateNode | null;
  workLog: WorkLogEntry[];
  chatHistory: ChatMessage[];
  wsEvents: WebSocketEvent[];
  connected: boolean;
  onSendChat: (msg: string, toRole: string) => void;
  onBack: () => void;
  onToggleTour: (enable: boolean) => void;
  onRefresh: () => void;
}) {
  const [chatInput, setChatInput] = useState("");
  const [chatTarget, setChatTarget] = useState("executive_director");
  const [activeTab, setActiveTab] = useState<"chat" | "agents" | "work" | "activity" | "health">("chat");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Build unified chat from history + live ws events, deduped
  const seenIds = new Set<string>();
  const allChat: { id?: string; from: string; content: string; time?: string }[] = [];
  for (const m of chatHistory) {
    if (!seenIds.has(m.id)) {
      seenIds.add(m.id);
      allChat.push({ id: m.id, from: m.from_role, content: m.body || m.subject, time: m.created_at });
    }
  }
  for (const e of wsEvents) {
    if (e.type === "chat" || e.type === "agent_response") {
      const id = (e as Record<string, unknown>).message_id as string | undefined;
      if (id && seenIds.has(id)) continue;
      if (id) seenIds.add(id);
      allChat.push({ from: e.from_role || e.role || "agent", content: e.content || "", time: undefined });
    }
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allChat.length]);

  const handleSend = () => {
    if (!chatInput.trim()) return;
    onSendChat(chatInput.trim(), chatTarget);
    setChatInput("");
  };

  const uniqueRoles = [...new Set(roster.map(r => r.role))].sort();
  const activeAgents = roster.filter(r => r.status === "active");
  const deadAgents = roster.filter(r => r.status !== "active");

  // Health data from ws events
  const healthEvents = wsEvents.filter(e => e.type === "metronome_tick" || e.type === "merge_check" || e.type === "agent_status");

  return (
    <div className="show-detail">
      <div className="show-detail-header">
        <button className="back-btn" onClick={onBack}>&larr;</button>
        <div className="show-detail-title">
          <h2>{show.title.length > 50 ? show.title.slice(0, 50) + "..." : show.title}</h2>
          <StatusBadge status={show.status} />
          <span className={`ws-dot ${connected ? "connected" : "disconnected"}`}
                title={connected ? "WebSocket connected" : "WebSocket disconnected"} />
        </div>
        <div className="show-detail-actions">
          <button className="small" onClick={onRefresh}>Refresh</button>
          {show.status === "active" && (
            <button className="small primary" onClick={() => onToggleTour(true)}>Start Tour</button>
          )}
        </div>
      </div>

      <div className="show-detail-tabs">
        {(["chat", "agents", "work", "activity", "health"] as const).map(tab => (
          <button key={tab} className={activeTab === tab ? "tab active" : "tab"} onClick={() => setActiveTab(tab)}>
            {tab === "chat" ? "Chat" :
             tab === "agents" ? `Agents (${activeAgents.length}/${roster.length})` :
             tab === "work" ? "Work Tree" :
             tab === "activity" ? `Activity (${workLog.length})` :
             "Health"}
          </button>
        ))}
      </div>

      <div className="show-detail-content">
        {/* ===== CHAT TAB ===== */}
        {activeTab === "chat" && (
          <div className="chat-panel">
            <div className="chat-messages">
              {allChat.length === 0 && (
                <div className="chat-empty">
                  <p>Send a message to start talking to the swarm.</p>
                  <p className="hint">Choose a role to message, or talk to the Executive Director to coordinate the whole team.</p>
                  {deadAgents.length > 0 && activeAgents.length === 0 && (
                    <p className="hint warning">All agents are currently stopped. Sending a message will revive the target agent.</p>
                  )}
                </div>
              )}
              {allChat.map((m, i) => (
                <div key={m.id || i} className={`chat-msg ${m.from === "user" ? "user" : "agent"}`}>
                  <div className="chat-msg-header">
                    <span className="chat-sender">{m.from === "user" ? "You" : formatRole(m.from)}</span>
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
                  <option key={r} value={r}>{formatRole(r)}</option>
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
        )}

        {/* ===== AGENTS TAB ===== */}
        {activeTab === "agents" && (
          <div className="agents-panel">
            {activeAgents.length > 0 && (
              <>
                <h3 className="section-label">Active ({activeAgents.length})</h3>
                <div className="agent-grid">
                  {activeAgents.map(a => <AgentCard key={a.id} agent={a} />)}
                </div>
              </>
            )}
            {deadAgents.length > 0 && (
              <>
                <h3 className="section-label">Stopped ({deadAgents.length})</h3>
                <p className="hint">Stopped agents will be revived when you send them a message via Chat.</p>
                <div className="agent-grid">
                  {deadAgents.map(a => <AgentCard key={a.id} agent={a} />)}
                </div>
              </>
            )}
            {roster.length === 0 && <p className="empty">No agents spawned. Activate the show first.</p>}
          </div>
        )}

        {/* ===== WORK TREE TAB ===== */}
        {activeTab === "work" && (
          <div className="work-panel">
            {!tree && <p className="empty">No work tree available. Activate the show to create the coordinate structure.</p>}
            {tree && <CoordTree node={tree} depth={0} />}
          </div>
        )}

        {/* ===== ACTIVITY TAB ===== */}
        {activeTab === "activity" && (
          <div className="activity-panel">
            {workLog.length === 0 && wsEvents.length === 0 && <p className="empty">No activity recorded yet.</p>}

            {/* Live events first */}
            {wsEvents.filter(e => e.type !== "chat" && e.type !== "pong" && e.type !== "ack").length > 0 && (
              <>
                <h3 className="section-label">Live Events</h3>
                <div className="activity-list">
                  {wsEvents.filter(e => e.type !== "chat" && e.type !== "pong" && e.type !== "ack").slice(-30).reverse().map((e, i) => (
                    <div key={i} className="activity-row">
                      <span className="activity-type">{e.type}</span>
                      <span className="activity-role">{e.role ? formatRole(e.role) : "-"}</span>
                      <span className="activity-detail">
                        {e.content?.slice(0, 100) || e.status || (e.tool ? `tool: ${e.tool}` : "")}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {workLog.length > 0 && (
              <>
                <h3 className="section-label">Work Log</h3>
                <div className="activity-list">
                  {workLog.map(w => (
                    <div key={w.id} className="activity-row">
                      <span className="activity-type">{w.event_type}</span>
                      <span className="activity-role">{formatRole(w.role)}</span>
                      <span className="activity-detail">{w.details?.slice(0, 120)}</span>
                      <span className="activity-time">{timeAgo(w.timestamp)}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* ===== HEALTH TAB ===== */}
        {activeTab === "health" && (
          <div className="health-panel">
            <div className="health-grid">
              <div className="health-card">
                <h3>WebSocket</h3>
                <div className={`health-indicator ${connected ? "ok" : "error"}`}>
                  {connected ? "Connected" : "Disconnected"}
                </div>
              </div>
              <div className="health-card">
                <h3>Agents</h3>
                <div className="health-stats">
                  <span className="health-ok">{activeAgents.length} active</span>
                  <span className="health-warn">{deadAgents.length} stopped</span>
                </div>
              </div>
              <div className="health-card">
                <h3>Work Items</h3>
                <div className="health-stats">
                  <span>{show.reps_completed ?? 0} completed</span>
                  <span>{show.reps_failed ?? 0} failed</span>
                  <span>{(show.reps_total ?? 0) - (show.reps_completed ?? 0) - (show.reps_failed ?? 0)} pending</span>
                </div>
              </div>
            </div>

            <h3 className="section-label">System Events</h3>
            {healthEvents.length === 0 && <p className="empty">No health events received yet. Events appear as the metronome ticks.</p>}
            <div className="activity-list">
              {healthEvents.slice(-20).reverse().map((e, i) => (
                <div key={i} className="activity-row">
                  <span className="activity-type">{e.type}</span>
                  <span className="activity-detail">
                    {e.type === "agent_status" && `${e.role || e.session_id?.slice(0, 8)} → ${e.status}`}
                    {e.type === "metronome_tick" && `checked: ${(e as Record<string,unknown>).checked}, reclaimed: ${(e as Record<string,unknown>).reclaimed}`}
                    {e.type === "merge_check" && `merged: ${(e as Record<string,unknown>).merged}, conflicts: ${(e as Record<string,unknown>).conflicts}`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentSession }) {
  return (
    <div className={`agent-card-detail status-${agent.status}`}>
      <div className="agent-card-top">
        <span className="agent-nickname-lg">{agent.nickname || formatRole(agent.role)}</span>
        <TierBadge tier={agent.model_tier} />
        <StatusBadge status={agent.status} />
      </div>
      <div className="agent-card-meta">
        <span>Role: {formatRole(agent.role)}</span>
        {agent.parent_session_id && <span>Reports to: {agent.parent_session_id.slice(0, 8)}</span>}
        <span>Since: {timeAgo(agent.started_at)}</span>
        {agent.ended_at && <span>Ended: {timeAgo(agent.ended_at)}</span>}
      </div>
    </div>
  );
}

// --- Coordinate Tree ---
function CoordTree({ node, depth }: { node: CoordinateNode; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;
  const completedReps = node.reps?.filter(r => r.status === "completed").length ?? 0;
  const totalReps = node.reps?.length ?? 0;

  return (
    <div className="coord-node">
      <div className={`coord-row status-${node.status}`} onClick={() => setExpanded(!expanded)}>
        <span className="coord-expand">{hasChildren ? (expanded ? "\u25BC" : "\u25B6") : "\u2022"}</span>
        <span className="coord-type-tag">{node.type}</span>
        <span className="coord-title">{node.title}</span>
        <StatusBadge status={node.status} />
        {totalReps > 0 && <span className="coord-reps-count">{completedReps}/{totalReps} tasks</span>}
      </div>
      {expanded && node.reps && node.reps.length > 0 && (
        <div className="coord-reps">
          {node.reps.map(r => (
            <div key={r.id} className={`rep-chip status-${r.status}`}>
              <StatusBadge status={r.status} />
              {r.assigned_to && <span className="rep-assignee">{r.assigned_to.slice(0, 8)}</span>}
              {r.result && <span className="rep-result">{r.result.slice(0, 80)}</span>}
              {r.error && <span className="rep-error">{r.error.slice(0, 80)}</span>}
            </div>
          ))}
        </div>
      )}
      {expanded && hasChildren && (
        <div className="coord-children">
          {node.children.map(c => <CoordTree key={c.id} node={c} depth={depth + 1} />)}
        </div>
      )}
    </div>
  );
}

// --- Main App ---
export default function App() {
  const [view, setView] = useState<"dashboard" | "show">("dashboard");
  const [selectedShow, setSelectedShow] = useState<Show | null>(null);
  const [shows, setShows] = useState<Show[]>([]);
  const [agents, setAgents] = useState<AgentSession[]>([]);
  const [globalLog, setGlobalLog] = useState<WorkLogEntry[]>([]);
  const [roster, setRoster] = useState<AgentSession[]>([]);
  const [tree, setTree] = useState<CoordinateNode | null>(null);
  const [showLog, setShowLog] = useState<WorkLogEntry[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [theme, setTheme] = useState<"dark" | "light">(() =>
    (localStorage.getItem("dci-theme") as "dark" | "light") || "dark"
  );

  const corpsId = selectedShow?.corps_id ?? null;
  const { connected, events, clearEvents } = useWebSocket(corpsId);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("dci-theme", theme);
  }, [theme]);

  // Load dashboard data — each call independent so one failure doesn't kill all
  const refreshDashboard = useCallback(async () => {
    const [s, a, l] = await Promise.allSettled([
      api.getShowsOverview(),
      api.getAgentsOverview(),
      api.getGlobalWorkLog(50),
    ]);
    if (s.status === "fulfilled") setShows(s.value);
    if (a.status === "fulfilled") setAgents(a.value);
    if (l.status === "fulfilled") setGlobalLog(l.value);
  }, []);

  useEffect(() => { refreshDashboard(); }, [refreshDashboard]);
  useEffect(() => {
    if (view !== "dashboard") return;
    const iv = setInterval(refreshDashboard, 10000);
    return () => clearInterval(iv);
  }, [view, refreshDashboard]);

  // Load show detail
  const loadShowDetail = useCallback(async (show: Show) => {
    setRoster([]); setTree(null); setShowLog([]); setChatHistory([]);
    clearEvents();

    if (show.corps_id) {
      const [r, l, c] = await Promise.allSettled([
        api.getRoster(show.corps_id),
        api.getWorkLog(show.corps_id, 100),
        api.getChatHistory(show.corps_id),
      ]);
      if (r.status === "fulfilled") setRoster(r.value);
      if (l.status === "fulfilled") setShowLog(l.value);
      if (c.status === "fulfilled") setChatHistory(c.value);
    }
    if (show.coordinate_root_id) {
      try { setTree(await api.getCoordinateTree(show.coordinate_root_id)); } catch {}
    }
  }, [clearEvents]);

  const handleSelectShow = (show: Show) => {
    setSelectedShow(show);
    setView("show");
    loadShowDetail(show);
  };

  const handleCreateShow = async (title: string, desc?: string) => {
    await api.createShow(title, desc);
    refreshDashboard();
  };

  const handleDeleteShow = async (id: string) => {
    if (!confirm("Delete this show? This cannot be undone.")) return;
    await api.deleteShow(id);
    if (selectedShow?.id === id) { setView("dashboard"); setSelectedShow(null); }
    refreshDashboard();
  };

  const handleActivateShow = async (id: string) => {
    await api.activateShow(id);
    refreshDashboard();
  };

  const handleBulkCleanup = async () => {
    // Find duplicate/completed shows and delete them
    const toDelete = shows.filter((s, i) => {
      // Delete duplicates (same title, keep the newest)
      const isDuplicate = shows.findIndex(x => x.title === s.title) !== i;
      const isCompleted = s.status === "completed" || s.status === "archived";
      return isDuplicate || isCompleted;
    });
    if (toDelete.length === 0) { alert("Nothing to clean up."); return; }
    if (!confirm(`Delete ${toDelete.length} old/duplicate shows?`)) return;
    for (const s of toDelete) {
      try { await api.deleteShow(s.id); } catch {}
    }
    refreshDashboard();
  };

  const handleSendChat = async (content: string, toRole: string) => {
    if (!corpsId) return;
    await api.sendChat(corpsId, content, toRole);
  };

  const handleBack = () => {
    setView("dashboard");
    setSelectedShow(null);
    clearEvents();
    refreshDashboard();
  };

  const handleToggleTour = async (enable: boolean) => {
    if (!selectedShow) return;
    await api.toggleTour(selectedShow.id, enable);
  };

  const handleRefreshDetail = () => {
    if (selectedShow) loadShowDetail(selectedShow);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title" onClick={handleBack} style={{ cursor: "pointer" }}>DCI Swarm</h1>
        <div className="header-controls">
          <button className="theme-toggle" onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}>
            {theme === "dark" ? "\u2600 Light" : "\u263D Dark"}
          </button>
        </div>
      </header>

      <main className="app-main">
        {view === "dashboard" && (
          <Dashboard
            shows={shows} agents={agents} workLog={globalLog}
            onSelectShow={handleSelectShow} onCreateShow={handleCreateShow}
            onDeleteShow={handleDeleteShow} onActivateShow={handleActivateShow}
            onBulkCleanup={handleBulkCleanup}
          />
        )}
        {view === "show" && selectedShow && (
          <ShowDetail
            show={selectedShow} roster={roster} tree={tree} workLog={showLog}
            chatHistory={chatHistory} wsEvents={events} connected={connected}
            onSendChat={handleSendChat} onBack={handleBack}
            onToggleTour={handleToggleTour} onRefresh={handleRefreshDetail}
          />
        )}
      </main>
    </div>
  );
}
