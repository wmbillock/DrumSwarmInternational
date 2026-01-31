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
          {(() => {
            // Group agents by corps, link to their show
            const byCorps: Record<string, AgentSession[]> = {};
            for (const a of agents) {
              const key = a.corps_id || "unknown";
              (byCorps[key] ??= []).push(a);
            }
            return Object.entries(byCorps).map(([corpsId, corpsAgents]) => {
              const show = shows.find(s => s.corps_id === corpsId);
              return (
                <div key={corpsId} className="agent-corps-group">
                  <div className="agent-corps-header clickable" onClick={() => show && onSelectShow(show)}>
                    <span className="corps-name">{show?.title || corpsId.slice(0, 8)}</span>
                    <span className="agent-count">{corpsAgents.length} agents</span>
                  </div>
                  <div className="agent-list">
                    {corpsAgents.slice(0, 10).map(a => (
                      <div key={a.id} className="agent-row clickable" onClick={() => show && onSelectShow(show)}>
                        <span className="agent-nickname">{a.nickname || formatRole(a.role)}</span>
                        <span className="agent-role-small">{formatRole(a.role)}</span>
                        <TierBadge tier={a.model_tier} />
                      </div>
                    ))}
                    {corpsAgents.length > 10 && <p className="empty">...and {corpsAgents.length - 10} more</p>}
                  </div>
                </div>
              );
            });
          })()}
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
      {show.corps_name && <p className="show-corps-name">{show.corps_name}</p>}
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
  const [activeTab, setActiveTab] = useState<"agents" | "work" | "activity" | "health">("agents");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Build unified chat from history + live ws events, deduped
  const seenIds = new Set<string>();
  // Build role→nickname lookup from roster
  const nicknameByRole: Record<string, string> = {};
  for (const a of roster) {
    if (a.nickname) nicknameByRole[a.role] = a.nickname;
  }

  const allChat: { id?: string; from: string; nickname?: string; content: string; time?: string }[] = [];
  for (const m of chatHistory) {
    if (!seenIds.has(m.id)) {
      seenIds.add(m.id);
      allChat.push({ id: m.id, from: m.from_role, nickname: nicknameByRole[m.from_role], content: m.body || m.subject, time: m.created_at });
    }
  }
  for (const e of wsEvents) {
    if (e.type === "chat" || e.type === "agent_response") {
      const id = (e as Record<string, unknown>).message_id as string | undefined;
      // Deduplicate by message_id or by content fingerprint
      const contentKey = id || `ws:${e.from_role || e.role}:${(e.content || "").slice(0, 100)}`;
      if (seenIds.has(contentKey)) continue;
      seenIds.add(contentKey);
      allChat.push({ from: e.from_role || e.role || "agent", nickname: e.nickname, content: e.content || "", time: undefined });
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
          <h2>{show.title.length > 60 ? show.title.slice(0, 60) + "..." : show.title}</h2>
          {show.corps_name && <span className="corps-badge">{show.corps_name}</span>}
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

      <div className="two-pane">
        {/* ===== LEFT PANE: CHAT ===== */}
        <div className="pane-left">
          <div className="chat-panel">
            <div className="chat-messages">
              {allChat.length === 0 && (
                <div className="chat-empty">
                  <p>Send a message to start talking to the swarm.</p>
                  <p className="hint">Choose a role, or talk to the ED to coordinate the whole team.</p>
                  {deadAgents.length > 0 && activeAgents.length === 0 && (
                    <p className="hint warning">All agents stopped. Sending a message will revive the target.</p>
                  )}
                </div>
              )}
              {allChat.map((m, i) => (
                <div key={m.id || i} className={`chat-msg ${m.from === "user" ? "user" : "agent"}`}>
                  <div className="chat-msg-header">
                    <span className="chat-sender">{m.from === "user" ? "You" : (m.nickname || formatRole(m.from))}</span>
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

        {/* ===== RIGHT PANE: INFO TABS ===== */}
        <div className="pane-right">
          <div className="info-tabs">
            {(["agents", "work", "activity", "health"] as const).map(tab => (
              <button key={tab} className={activeTab === tab ? "tab active" : "tab"} onClick={() => setActiveTab(tab)}>
                {tab === "agents" ? `Agents (${activeAgents.length}/${roster.length})` :
                 tab === "work" ? "Work Tree" :
                 tab === "activity" ? `Activity (${workLog.length})` :
                 "Health"}
              </button>
            ))}
          </div>

          <div className="info-content">
            {activeTab === "agents" && (
              <div className="agents-panel-compact">
                {activeAgents.length > 0 && (
                  <>
                    <h4 className="section-label">Active ({activeAgents.length})</h4>
                    {activeAgents.map(a => (
                      <div key={a.id} className="agent-row-compact">
                        <TierBadge tier={a.model_tier} />
                        <span className="agent-nickname">{a.nickname || formatRole(a.role)}</span>
                        <span className="agent-role-small">{formatRole(a.role)}</span>
                      </div>
                    ))}
                  </>
                )}
                {deadAgents.length > 0 && (
                  <>
                    <h4 className="section-label">Stopped ({deadAgents.length})</h4>
                    {deadAgents.map(a => (
                      <div key={a.id} className="agent-row-compact stopped">
                        <TierBadge tier={a.model_tier} />
                        <span className="agent-nickname">{a.nickname || formatRole(a.role)}</span>
                        <span className="agent-role-small">{formatRole(a.role)}</span>
                      </div>
                    ))}
                  </>
                )}
                {roster.length === 0 && <p className="empty">No agents spawned.</p>}
              </div>
            )}

            {activeTab === "work" && (
              <div className="work-panel">
                {!tree && <p className="empty">No work tree available.</p>}
                {tree && <CoordTree node={tree} depth={0} />}
              </div>
            )}

            {activeTab === "activity" && (
              <div className="activity-panel-compact">
                {wsEvents.filter(e => e.type !== "chat" && e.type !== "pong" && e.type !== "ack").length > 0 && (
                  <>
                    <h4 className="section-label">Live</h4>
                    <div className="activity-list">
                      {wsEvents.filter(e => e.type !== "chat" && e.type !== "pong" && e.type !== "ack").slice(-20).reverse().map((e, i) => (
                        <div key={i} className="activity-row">
                          <span className="activity-type">{e.type}</span>
                          <span className="activity-role">{e.nickname || (e.role ? formatRole(e.role) : "-")}</span>
                          <span className="activity-detail">
                            {e.content?.slice(0, 80) || e.status || (e.tool ? `tool: ${e.tool}` : "")}
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
                {workLog.length > 0 && (
                  <>
                    <h4 className="section-label">Log</h4>
                    <div className="activity-list">
                      {workLog.slice(0, 30).map(w => (
                        <div key={w.id} className="activity-row">
                          <span className="activity-type">{w.event_type}</span>
                          <span className="activity-role">{formatRole(w.role)}</span>
                          <span className="activity-detail">{w.details?.slice(0, 80)}</span>
                          <span className="activity-time">{timeAgo(w.timestamp)}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
                {workLog.length === 0 && wsEvents.length === 0 && <p className="empty">No activity yet.</p>}
              </div>
            )}

            {activeTab === "health" && (
              <div className="health-panel-compact">
                <div className="health-row">
                  <span>WS: <span className={connected ? "health-ok" : "health-error"}>{connected ? "Connected" : "Down"}</span></span>
                  <span>Agents: <span className="health-ok">{activeAgents.length}</span>/<span className="health-warn">{deadAgents.length}</span></span>
                  <span>Tasks: {show.reps_completed ?? 0}/{show.reps_total ?? 0}</span>
                </div>
                {healthEvents.length > 0 && (
                  <div className="activity-list">
                    {healthEvents.slice(-15).reverse().map((e, i) => (
                      <div key={i} className="activity-row">
                        <span className="activity-type">{e.type}</span>
                        <span className="activity-detail">
                          {e.type === "agent_status" && `${e.nickname || e.role || e.session_id?.slice(0, 8)} → ${e.status}`}
                          {e.type === "metronome_tick" && `checked: ${(e as Record<string,unknown>).checked}, reclaimed: ${(e as Record<string,unknown>).reclaimed}`}
                          {e.type === "merge_check" && `merged: ${(e as Record<string,unknown>).merged}, conflicts: ${(e as Record<string,unknown>).conflicts}`}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {healthEvents.length === 0 && <p className="empty">No health events yet.</p>}
              </div>
            )}
          </div>
        </div>
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
// --- Admin Chat ("The Bar") ---
function AdminChat({
  corpsId, roster, chatHistory, wsEvents, connected, onSendChat, onBack,
}: {
  corpsId: string;
  roster: AgentSession[];
  chatHistory: ChatMessage[];
  wsEvents: WebSocketEvent[];
  connected: boolean;
  onSendChat: (msg: string, toRole: string) => void;
  onBack: () => void;
}) {
  const [chatInput, setChatInput] = useState("");
  const [chatTarget, setChatTarget] = useState("executive_director");
  const chatEndRef = useRef<HTMLDivElement>(null);

  const nicknameByRole: Record<string, string> = {};
  for (const a of roster) { if (a.nickname) nicknameByRole[a.role] = a.nickname; }

  const seenIds = new Set<string>();
  const allChat: { id?: string; from: string; nickname?: string; content: string; time?: string }[] = [];
  for (const m of chatHistory) {
    if (!seenIds.has(m.id)) {
      seenIds.add(m.id);
      allChat.push({ id: m.id, from: m.from_role, nickname: nicknameByRole[m.from_role], content: m.body || m.subject, time: m.created_at });
    }
  }
  for (const e of wsEvents) {
    if (e.type === "chat" || e.type === "agent_response") {
      const id = (e as Record<string, unknown>).message_id as string | undefined;
      const contentKey = id || `ws:${e.from_role || e.role}:${(e.content || "").slice(0, 100)}`;
      if (seenIds.has(contentKey)) continue;
      seenIds.add(contentKey);
      allChat.push({ from: e.from_role || e.role || "agent", nickname: e.nickname, content: e.content || "", time: undefined });
    }
  }

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [allChat.length]);

  const handleSend = () => {
    if (!chatInput.trim()) return;
    onSendChat(chatInput.trim(), chatTarget);
    setChatInput("");
  };

  const uniqueRoles = [...new Set(roster.map(r => r.role))].sort();

  return (
    <div className="admin-chat-view">
      <div className="admin-chat-header">
        <button className="back-btn" onClick={onBack}>&larr;</button>
        <h2>Critique</h2>
        <span className="corps-badge">Post-Run Review</span>
        <span className={`ws-dot ${connected ? "connected" : "disconnected"}`}
              title={connected ? "Connected" : "Disconnected"} />
        <div style={{ flex: 1 }} />
        <div className="admin-roster">
          {roster.map(a => (
            <span key={a.id} className={`admin-agent-chip ${a.status}`} title={`${a.nickname || formatRole(a.role)} (${a.status})`}>
              <TierBadge tier={a.model_tier} />
              <span>{a.nickname || formatRole(a.role)}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="chat-panel">
        <div className="chat-messages">
          {allChat.length === 0 && (
            <div className="chat-empty">
              <p>Welcome to Critique.</p>
              <p className="hint">This is where the staff gathers after the run to review, discuss, and plan. Give feedback, get status updates, or coordinate across shows.</p>
            </div>
          )}
          {allChat.map((m, i) => (
            <div key={m.id || i} className={`chat-msg ${m.from === "user" ? "user" : "agent"}`}>
              <div className="chat-msg-header">
                <span className="chat-sender">{m.from === "user" ? "You" : (m.nickname || formatRole(m.from))}</span>
                {m.time && <span className="chat-time">{timeAgo(m.time)}</span>}
              </div>
              <div className="chat-msg-body">{m.content}</div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
        <div className="chat-input-row">
          <select value={chatTarget} onChange={e => setChatTarget(e.target.value)}>
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
            placeholder="Give your critique..."
          />
          <button className="primary" onClick={handleSend} disabled={!chatInput.trim()}>Send</button>
        </div>
      </div>
    </div>
  );
}


export default function App() {
  const [view, setView] = useState<"dashboard" | "show" | "admin">("dashboard");
  const [selectedShow, setSelectedShow] = useState<Show | null>(null);
  const [shows, setShows] = useState<Show[]>([]);
  const [agents, setAgents] = useState<AgentSession[]>([]);
  const [globalLog, setGlobalLog] = useState<WorkLogEntry[]>([]);
  const [roster, setRoster] = useState<AgentSession[]>([]);
  const [tree, setTree] = useState<CoordinateNode | null>(null);
  const [showLog, setShowLog] = useState<WorkLogEntry[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [adminCorpsId, setAdminCorpsId] = useState<string | null>(null);
  const [adminRoster, setAdminRoster] = useState<AgentSession[]>([]);
  const [adminChatHistory, setAdminChatHistory] = useState<ChatMessage[]>([]);
  const [theme, setTheme] = useState<"dark" | "light">(() =>
    (localStorage.getItem("dci-theme") as "dark" | "light") || "dark"
  );

  // WebSocket connects to whichever corps is active
  const activeCorpsId = view === "admin" ? adminCorpsId : (selectedShow?.corps_id ?? null);
  const { connected, events, clearEvents } = useWebSocket(activeCorpsId);

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
  const loadShowDetail = useCallback(async (show: Show, isRefresh = false) => {
    if (!isRefresh) {
      setRoster([]); setTree(null); setShowLog([]); setChatHistory([]);
      clearEvents();
    }

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
    const cid = view === "admin" ? adminCorpsId : selectedShow?.corps_id;
    if (!cid) return;
    await api.sendChat(cid, content, toRole);
  };

  const handleOpenAdmin = async () => {
    try {
      const data = await api.getAdminCorps();
      setAdminCorpsId(data.id);
      setAdminRoster(data.roster);
      clearEvents();
      // Load chat history
      try {
        const history = await api.getChatHistory(data.id);
        setAdminChatHistory(history);
      } catch { setAdminChatHistory([]); }
      setView("admin");
    } catch (e) {
      alert("Failed to load admin corps: " + (e instanceof Error ? e.message : "unknown error"));
    }
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
    if (selectedShow) loadShowDetail(selectedShow, true);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title" onClick={handleBack} style={{ cursor: "pointer" }}>DCI Swarm</h1>
        <div className="header-controls">
          <button className={view === "admin" ? "primary small" : "small"} onClick={handleOpenAdmin}>Critique</button>
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
        {view === "admin" && adminCorpsId && (
          <AdminChat
            corpsId={adminCorpsId} roster={adminRoster}
            chatHistory={adminChatHistory} wsEvents={events} connected={connected}
            onSendChat={handleSendChat} onBack={handleBack}
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
