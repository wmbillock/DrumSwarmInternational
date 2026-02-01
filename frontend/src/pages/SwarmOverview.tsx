import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { Show, AgentSession, WorkLogEntry } from "../types";
import * as api from "../services/api";
import * as v1 from "../services/v1";

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
  full_ensemble: "Full Ensemble",
  run_through: "Run Through",
};

function StatusBadge({ status }: { status: string }) {
  const label = STATUS_LABELS[status] || status;
  return <span className={`badge ${status}`}>{label}</span>;
}

function TierBadge({ tier }: { tier?: string }) {
  if (!tier) return null;
  return <span className={`tier-badge tier-${tier}`}>{tier}</span>;
}

const CLASSIFICATION_LABELS: Record<string, string> = {
  performing_member: "Performer",
  instructional_staff: "Staff",
  administrative_staff: "Admin",
  logistics: "Logistics",
  dci_assigned: "Judge",
};

function ClassificationBadge({ classification }: { classification?: string }) {
  if (!classification) return null;
  const label = CLASSIFICATION_LABELS[classification] || classification;
  return <span className={`classification-badge ${classification}`}>{label}</span>;
}

function ShowCard({ show, onSelect, onDelete, onActivate }: {
  show: Show; onSelect: (s: Show) => void; onDelete: (id: string) => void; onActivate: (id: string) => void;
}) {
  const displayTitle = show.title.length > 40 ? show.title.slice(0, 40) + "..." : show.title;
  return (
    <div className={`show-card status-${show.status}`} onClick={() => onSelect(show)}>
      <div className="show-card-header">
        <h3 title={show.title}>{displayTitle}</h3>
        <StatusBadge status={show.status} />
      </div>
      {show.corps_name && <p className="show-corps-name">{show.corps_name}</p>}
      {show.description && <p className="show-desc">{show.description.length > 80 ? show.description.slice(0, 80) + "..." : show.description}</p>}
      <div className="show-stats">
        <span>{show.agents_active ?? 0} agents</span>
        <span>{(show.reps_completed ?? 0)}/{(show.reps_total ?? 0)} tasks done</span>
        {show.final_score != null && <span className="show-score">Score: {show.final_score}</span>}
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

export function SwarmOverview() {
  const navigate = useNavigate();
  const [shows, setShows] = useState<Show[]>([]);
  const [agents, setAgents] = useState<AgentSession[]>([]);
  const [workLog, setWorkLog] = useState<WorkLogEntry[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [corpsSlugMap, setCorpsSlugMap] = useState<Record<string, string>>({});

  const refreshDashboard = useCallback(async () => {
    const [s, a, l, c] = await Promise.allSettled([
      api.getShowsOverview(),
      v1.getAgentsOverview(),
      v1.getGlobalWorkLog(50),
      v1.listCorps(),
    ]);
    if (s.status === "fulfilled") setShows(s.value);
    if (a.status === "fulfilled") setAgents(a.value);
    if (l.status === "fulfilled") setWorkLog(l.value);
    if (c.status === "fulfilled") {
      const slugMap: Record<string, string> = {};
      for (const corps of c.value) {
        slugMap[corps.display_name] = corps.corps_id;
      }
      setCorpsSlugMap(slugMap);
    }
  }, []);

  useEffect(() => { refreshDashboard(); }, [refreshDashboard]);
  useEffect(() => {
    const iv = setInterval(refreshDashboard, 10000);
    return () => clearInterval(iv);
  }, [refreshDashboard]);

  const handleSelectShow = (show: Show) => {
    if (show.corps_id) {
      const slug = corpsSlugMap[show.corps_name || ""] || show.corps_id;
      navigate(`/corps/${slug}`);
    }
  };

  const handleCreateShow = async (title: string, desc?: string) => {
    await api.createShow(title, desc);
    refreshDashboard();
  };

  const handleDeleteShow = async (id: string) => {
    if (!confirm("Delete this show? This cannot be undone.")) return;
    await api.deleteShow(id);
    refreshDashboard();
  };

  const handleActivateShow = async (id: string) => {
    await api.activateShow(id);
    refreshDashboard();
  };

  const handleBulkCleanup = async () => {
    const toDelete = shows.filter((s, i) => {
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

  const activeShows = shows.filter(s => s.status === "active");
  const draftShows = shows.filter(s => s.status === "draft");
  const completedShows = shows.filter(s => s.status === "completed" || s.status === "archived");

  return (
    <div className="shows-overview">
      <h1 className="page-title">Shows</h1>
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

      <div className="dash-section">
        <div className="dash-header">
          <h2>Shows</h2>
          <div className="header-actions">
            {shows.length > 3 && (
              <button className="small danger" onClick={handleBulkCleanup}>Clean Up Old Shows</button>
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
              handleCreateShow(newTitle.trim(), newDesc.trim() || undefined);
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
                <ShowCard key={s.id} show={s} onSelect={handleSelectShow} onDelete={handleDeleteShow} onActivate={handleActivateShow} />
              ))}
            </div>
          </>
        )}

        {draftShows.length > 0 && (
          <>
            <h3 className="section-label">Drafts</h3>
            <div className="show-grid">
              {draftShows.map(s => (
                <ShowCard key={s.id} show={s} onSelect={handleSelectShow} onDelete={handleDeleteShow} onActivate={handleActivateShow} />
              ))}
            </div>
          </>
        )}

        {completedShows.length > 0 && (
          <>
            <h3 className="section-label">Completed / Archived</h3>
            <div className="show-grid">
              {completedShows.map(s => (
                <ShowCard key={s.id} show={s} onSelect={handleSelectShow} onDelete={handleDeleteShow} onActivate={handleActivateShow} />
              ))}
            </div>
          </>
        )}
      </div>

      <div className="dash-row">
        <div className="dash-section flex-1">
          <h2>Active Agents ({agents.length})</h2>
          {agents.length === 0 && <p className="empty">No active agents. Activate a show to spawn agents.</p>}
          {(() => {
            const byCorps: Record<string, AgentSession[]> = {};
            for (const a of agents) {
              const key = a.corps_id || "unknown";
              (byCorps[key] ??= []).push(a);
            }
            return Object.entries(byCorps).map(([corpsId, corpsAgents]) => {
              const show = shows.find(s => s.corps_id === corpsId);
              const corpsName = corpsAgents[0]?.corps_name || show?.corps_name || show?.title || "Unknown Corps";
              return (
                <div key={corpsId} className="agent-corps-group">
                  <div className="agent-corps-header clickable" onClick={() => show && handleSelectShow(show)}>
                    <span className="corps-name">{corpsName}</span>
                    <span className="agent-count">{corpsAgents.length} agents</span>
                  </div>
                  <div className="agent-list">
                    {corpsAgents.map(a => (
                      <div key={a.id} className="agent-row clickable" onClick={() => show && handleSelectShow(show)}>
                        <span className="agent-nickname">{a.nickname || formatRole(a.role)}</span>
                        <span className="agent-role-small">{formatRole(a.role)}</span>
                        <TierBadge tier={a.model_tier} />
                        <ClassificationBadge classification={a.classification} />
                      </div>
                    ))}
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
                <span className="activity-role">{w.nickname || formatRole(w.role)}</span>
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
