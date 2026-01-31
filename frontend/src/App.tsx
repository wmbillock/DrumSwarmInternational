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
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

function tierBadge(tier?: string): string {
  if (tier === "opus") return "opus";
  if (tier === "sonnet") return "snnt";
  if (tier === "haiku") return "hku";
  return "";
}

// --- Status Badge ---
function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${status}`}>{status}</span>;
}

// --- Dashboard View ---
function Dashboard({
  shows, agents, workLog, onSelectShow, onCreateShow, onDeleteShow, onActivateShow,
}: {
  shows: Show[];
  agents: AgentSession[];
  workLog: WorkLogEntry[];
  onSelectShow: (s: Show) => void;
  onCreateShow: (title: string) => void;
  onDeleteShow: (id: string) => void;
  onActivateShow: (id: string) => void;
}) {
  const [newTitle, setNewTitle] = useState("");

  return (
    <div className="dashboard">
      <div className="dash-section">
        <div className="dash-header">
          <h2>Shows</h2>
          <form className="inline-form" onSubmit={e => { e.preventDefault(); if (newTitle.trim()) { onCreateShow(newTitle.trim()); setNewTitle(""); } }}>
            <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="New show title..." />
            <button type="submit" className="primary" disabled={!newTitle.trim()}>Create</button>
          </form>
        </div>
        {shows.length === 0 && <p className="empty">No shows yet. Create one to get started.</p>}
        <div className="show-grid">
          {shows.map(s => (
            <div key={s.id} className={`show-card status-${s.status}`} onClick={() => onSelectShow(s)}>
              <div className="show-card-header">
                <h3>{s.title}</h3>
                <StatusBadge status={s.status} />
              </div>
              {s.description && <p className="show-desc">{s.description}</p>}
              <div className="show-stats">
                <span>{s.agents_active ?? 0} agents</span>
                <span>{s.reps_completed ?? 0}/{s.reps_total ?? 0} tasks</span>
              </div>
              <div className="show-actions">
                {s.status === "draft" && (
                  <button className="small primary" onClick={e => { e.stopPropagation(); onActivateShow(s.id); }}>Activate</button>
                )}
                <button className="small danger" onClick={e => { e.stopPropagation(); onDeleteShow(s.id); }}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="dash-row">
        <div className="dash-section flex-1">
          <h2>Active Agents ({agents.length})</h2>
          {agents.length === 0 && <p className="empty">No active agents.</p>}
          <div className="agent-list">
            {agents.slice(0, 20).map(a => (
              <div key={a.id} className="agent-row">
                <span className="agent-nickname">{a.nickname || formatRole(a.role)}</span>
                <span className="agent-role-small">{formatRole(a.role)}</span>
                <span className={`tier-badge tier-${a.model_tier}`}>{tierBadge(a.model_tier)}</span>
                <span className="agent-time">{timeAgo(a.started_at)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="dash-section flex-1">
          <h2>Recent Activity</h2>
          {workLog.length === 0 && <p className="empty">No activity yet.</p>}
          <div className="activity-list">
            {workLog.slice(0, 20).map(w => (
              <div key={w.id} className="activity-row">
                <span className="activity-type">{w.event_type}</span>
                <span className="activity-role">{formatRole(w.role)}</span>
                <span className="activity-detail">{w.details?.slice(0, 80)}</span>
                <span className="activity-time">{timeAgo(w.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Show Detail View ---
function ShowDetail({
  show, roster, tree, workLog, chatHistory, wsEvents, connected,
  onSendChat, onBack, onToggleTour,
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
}) {
  const [chatInput, setChatInput] = useState("");
  const [chatTarget, setChatTarget] = useState("executive_director");
  const [activeTab, setActiveTab] = useState<"chat" | "agents" | "work" | "activity">("chat");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Merge chat history with live ws chat events
  const allChat: { from: string; content: string; time?: string }[] = [
    ...chatHistory.map(m => ({ from: m.from_role, content: m.body || m.subject, time: m.created_at })),
    ...wsEvents
      .filter(e => e.type === "chat" || e.type === "agent_response")
      .map(e => ({
        from: e.from_role || e.role || "agent",
        content: e.content || "",
        time: undefined as string | undefined,
      })),
  ];

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allChat.length]);

  const handleSend = () => {
    if (!chatInput.trim()) return;
    onSendChat(chatInput.trim(), chatTarget);
    setChatInput("");
  };

  const uniqueRoles = [...new Set(roster.map(r => r.role))];

  return (
    <div className="show-detail">
      <div className="show-detail-header">
        <button className="back-btn" onClick={onBack}>&larr; Back</button>
        <div className="show-detail-title">
          <h2>{show.title}</h2>
          <StatusBadge status={show.status} />
          {connected && <span className="ws-dot connected" title="Connected" />}
          {!connected && <span className="ws-dot disconnected" title="Disconnected" />}
        </div>
        <div className="show-detail-actions">
          {show.status === "active" && (
            <button className="small" onClick={() => onToggleTour(true)}>Start Tour</button>
          )}
        </div>
      </div>

      <div className="show-detail-tabs">
        <button className={activeTab === "chat" ? "tab active" : "tab"} onClick={() => setActiveTab("chat")}>Chat</button>
        <button className={activeTab === "agents" ? "tab active" : "tab"} onClick={() => setActiveTab("agents")}>Agents ({roster.length})</button>
        <button className={activeTab === "work" ? "tab active" : "tab"} onClick={() => setActiveTab("work")}>Work Tree</button>
        <button className={activeTab === "activity" ? "tab active" : "tab"} onClick={() => setActiveTab("activity")}>Activity</button>
      </div>

      <div className="show-detail-content">
        {activeTab === "chat" && (
          <div className="chat-panel">
            <div className="chat-messages">
              {allChat.length === 0 && <p className="empty">Send a message to start a conversation with the swarm.</p>}
              {allChat.map((m, i) => (
                <div key={i} className={`chat-msg ${m.from === "user" ? "user" : "agent"}`}>
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
              <select value={chatTarget} onChange={e => setChatTarget(e.target.value)}>
                {uniqueRoles.map(r => <option key={r} value={r}>{formatRole(r)}</option>)}
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

        {activeTab === "agents" && (
          <div className="agents-panel">
            {roster.map(a => (
              <div key={a.id} className={`agent-card-detail status-${a.status}`}>
                <div className="agent-card-top">
                  <span className="agent-nickname-lg">{a.nickname || formatRole(a.role)}</span>
                  <span className={`tier-badge tier-${a.model_tier}`}>{a.model_tier}</span>
                  <StatusBadge status={a.status} />
                </div>
                <div className="agent-card-meta">
                  <span>Role: {formatRole(a.role)}</span>
                  <span>Started: {timeAgo(a.started_at)}</span>
                  {a.ended_at && <span>Ended: {timeAgo(a.ended_at)}</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "work" && (
          <div className="work-panel">
            {!tree && <p className="empty">No work tree available. Activate the show to start.</p>}
            {tree && <CoordTree node={tree} />}
          </div>
        )}

        {activeTab === "activity" && (
          <div className="activity-panel">
            {workLog.length === 0 && <p className="empty">No activity recorded yet.</p>}
            {workLog.map(w => (
              <div key={w.id} className="activity-row">
                <span className="activity-type">{w.event_type}</span>
                <span className="activity-role">{formatRole(w.role)}</span>
                <span className="activity-detail">{w.details}</span>
                <span className="activity-time">{timeAgo(w.timestamp)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- Coordinate Tree Renderer ---
function CoordTree({ node }: { node: CoordinateNode }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="coord-node">
      <div className={`coord-row status-${node.status}`} onClick={() => setExpanded(!expanded)}>
        <span className="coord-expand">{hasChildren ? (expanded ? "\u25BC" : "\u25B6") : "\u2022"}</span>
        <span className="coord-type-tag">{node.type}</span>
        <span className="coord-title">{node.title}</span>
        <StatusBadge status={node.status} />
        {node.reps && node.reps.length > 0 && (
          <span className="coord-reps-count">{node.reps.filter(r => r.status === "completed").length}/{node.reps.length} done</span>
        )}
      </div>
      {expanded && node.reps && node.reps.length > 0 && (
        <div className="coord-reps">
          {node.reps.map(r => (
            <div key={r.id} className={`rep-chip status-${r.status}`}>
              <StatusBadge status={r.status} />
              {r.result && <span className="rep-result">{r.result.slice(0, 60)}</span>}
              {r.error && <span className="rep-error">{r.error.slice(0, 60)}</span>}
            </div>
          ))}
        </div>
      )}
      {expanded && hasChildren && (
        <div className="coord-children">
          {node.children.map(c => <CoordTree key={c.id} node={c} />)}
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

  // Theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("dci-theme", theme);
  }, [theme]);

  // Load dashboard data
  const refreshDashboard = useCallback(async () => {
    try {
      const [s, a, l] = await Promise.all([
        api.getShowsOverview(),
        api.getAgentsOverview(),
        api.getGlobalWorkLog(30),
      ]);
      setShows(s);
      setAgents(a);
      setGlobalLog(l);
    } catch (e) {
      console.error("Dashboard refresh error:", e);
    }
  }, []);

  useEffect(() => { refreshDashboard(); }, [refreshDashboard]);

  // Auto-refresh dashboard every 15s
  useEffect(() => {
    if (view !== "dashboard") return;
    const iv = setInterval(refreshDashboard, 15000);
    return () => clearInterval(iv);
  }, [view, refreshDashboard]);

  // Load show detail data
  const loadShowDetail = useCallback(async (show: Show) => {
    setRoster([]);
    setTree(null);
    setShowLog([]);
    setChatHistory([]);
    clearEvents();

    if (show.corps_id) {
      try {
        const [r, l, c] = await Promise.all([
          api.getRoster(show.corps_id),
          api.getWorkLog(show.corps_id, 50),
          api.getChatHistory(show.corps_id),
        ]);
        setRoster(r);
        setShowLog(l);
        setChatHistory(c);
      } catch (e) {
        console.error("Show detail load error:", e);
      }
    }
    if (show.coordinate_root_id) {
      try {
        const t = await api.getCoordinateTree(show.coordinate_root_id);
        setTree(t);
      } catch {
        // tree might not exist yet
      }
    }
  }, [clearEvents]);

  const handleSelectShow = (show: Show) => {
    setSelectedShow(show);
    setView("show");
    loadShowDetail(show);
  };

  const handleCreateShow = async (title: string) => {
    await api.createShow(title);
    refreshDashboard();
  };

  const handleDeleteShow = async (id: string) => {
    await api.deleteShow(id);
    refreshDashboard();
  };

  const handleActivateShow = async (id: string) => {
    await api.activateShow(id);
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
    refreshDashboard();
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title" onClick={handleBack} style={{ cursor: "pointer" }}>DCI Swarm</h1>
        <div className="header-controls">
          <button className="theme-toggle" onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}>
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <main className="app-main">
        {view === "dashboard" && (
          <Dashboard
            shows={shows}
            agents={agents}
            workLog={globalLog}
            onSelectShow={handleSelectShow}
            onCreateShow={handleCreateShow}
            onDeleteShow={handleDeleteShow}
            onActivateShow={handleActivateShow}
          />
        )}
        {view === "show" && selectedShow && (
          <ShowDetail
            show={selectedShow}
            roster={roster}
            tree={tree}
            workLog={showLog}
            chatHistory={chatHistory}
            wsEvents={events}
            connected={connected}
            onSendChat={handleSendChat}
            onBack={handleBack}
            onToggleTour={handleToggleTour}
          />
        )}
      </main>
    </div>
  );
}
