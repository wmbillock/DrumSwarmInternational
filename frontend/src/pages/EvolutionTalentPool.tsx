import { useState, useEffect } from "react";
import * as api from "../services/api";
import * as v1 from "../services/v1";
import type { PerformerGenome, SelectionEvent, MutationLog, MutationSimulationResult } from "../types";

function formatRole(role: string): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function timeAgo(ts?: string | null): string {
  if (!ts) return "";
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

function TrustBar({ score }: { score: number }) {
  const color = score >= 70 ? "var(--success)" : score >= 40 ? "var(--warning)" : "var(--danger)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ width: 60, height: 6, background: "var(--bg-hover)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${score}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color }}>{score.toFixed(1)}</span>
    </div>
  );
}

function EventTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    trust_change: "var(--accent)",
    retirement: "var(--danger)",
    rep_completed: "var(--success)",
    rep_failed: "var(--danger)",
    session_completed: "var(--success)",
    session_failed: "var(--warning)",
    gupp_violation: "var(--danger)",
  };
  return (
    <span style={{
      fontSize: 10, padding: "1px 6px", borderRadius: 4, fontWeight: 600,
      background: "var(--bg-hover)", color: colors[type] || "var(--text-muted)",
      textTransform: "uppercase",
    }}>
      {type.replace(/_/g, " ")}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const color = level === "high" ? "var(--danger)" : level === "medium" ? "var(--warning)" : "var(--success)";
  return <span className="badge" style={{ color, borderColor: color }}>{level.toUpperCase()}</span>;
}

export function EvolutionTalentPool() {
  const [tab, setTab] = useState<"pool" | "events" | "mutations" | "simulate">("pool");
  const [performers, setPerformers] = useState<any[]>([]);
  const [selectedGenome, setSelectedGenome] = useState<PerformerGenome | null>(null);
  const [events, setEvents] = useState<SelectionEvent[]>([]);
  const [eventFilter, setEventFilter] = useState("");
  const [mutations, setMutations] = useState<MutationLog[]>([]);

  // Simulation state
  const [simDefId, setSimDefId] = useState("");
  const [simChanges, setSimChanges] = useState("{}");
  const [simReason, setSimReason] = useState("");
  const [simResult, setSimResult] = useState<MutationSimulationResult | null>(null);
  const [simulating, setSimulating] = useState(false);

  useEffect(() => {
    v1.listPerformers().then(setPerformers).catch(() => setPerformers([]));
  }, []);

  const loadEvents = async () => {
    try {
      const e = await v1.getSelectionEvents(eventFilter || undefined);
      setEvents(e);
    } catch { setEvents([]); }
  };

  const loadMutations = async () => {
    try {
      const m = await v1.getMutations();
      setMutations(m);
    } catch { setMutations([]); }
  };

  useEffect(() => {
    if (tab === "events") loadEvents();
    if (tab === "mutations") loadMutations();
  }, [tab, eventFilter]);

  const handleSelectPerformer = async (id: string) => {
    try {
      const genome = await v1.getPerformerGenome(id);
      setSelectedGenome(genome);
    } catch { setSelectedGenome(null); }
  };

  const handleSimulate = async () => {
    if (!simDefId || !simReason) return;
    setSimulating(true);
    try {
      const changes = JSON.parse(simChanges);
      const result = await api.simulateMutation(simDefId, changes, simReason);
      setSimResult(result);
    } catch (e: any) {
      setSimResult(null);
      alert(e.message);
    } finally { setSimulating(false); }
  };

  return (
    <div className="dashboard">
      <h2 className="page-title">Evolution & Talent Pool</h2>

      <div className="info-tabs" style={{ marginBottom: 16 }}>
        <button className={`tab ${tab === "pool" ? "active" : ""}`} onClick={() => setTab("pool")}>
          Talent Pool ({performers.length})
        </button>
        <button className={`tab ${tab === "events" ? "active" : ""}`} onClick={() => setTab("events")}>
          Selection Events
        </button>
        <button className={`tab ${tab === "mutations" ? "active" : ""}`} onClick={() => setTab("mutations")}>
          Mutations
        </button>
        <button className={`tab ${tab === "simulate" ? "active" : ""}`} onClick={() => setTab("simulate")}>
          Simulate Mutation
        </button>
      </div>

      {/* Talent Pool + Genome */}
      {tab === "pool" && (
        <div style={{ display: "flex", gap: 16 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="table-wrapper">
              <table className="styled-table">
                <thead>
                  <tr><th>Name</th><th>Role</th><th>Trust</th><th>Age</th><th>Status</th><th>Sessions</th></tr>
                </thead>
                <tbody>
                  {performers.map((p: any) => (
                    <tr key={p.id} onClick={() => handleSelectPerformer(p.id)} className="clickable">
                      <td className="cell-primary">{p.name || p.id.slice(0, 8)}</td>
                      <td>{formatRole(p.role_type || "")}</td>
                      <td><TrustBar score={p.trust_score ?? 0} /></td>
                      <td>{p.age ?? "-"}</td>
                      <td><span className={`badge ${p.status}`}>{p.status}</span></td>
                      <td>{p.total_sessions ?? 0}</td>
                    </tr>
                  ))}
                  {performers.length === 0 && <tr><td colSpan={6} className="dim">No performers in the talent pool.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>

          {/* Genome detail */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {selectedGenome ? (
              <div className="detail-panel">
                <h3>{selectedGenome.name}</h3>
                <p className="dim" style={{ marginBottom: 12 }}>{formatRole(selectedGenome.role_type)} — Age {selectedGenome.age}, {selectedGenome.experience_seasons} seasons</p>

                <div className="section-label">Identity</div>
                <div className="stats-grid">
                  <div><strong>Trust</strong><TrustBar score={selectedGenome.trust_score} /></div>
                  <div><strong>Status</strong><span className={`badge ${selectedGenome.status}`}>{selectedGenome.status}</span></div>
                  <div><strong>Specialties</strong><span>{selectedGenome.specialties || "None"}</span></div>
                </div>

                <div className="section-label">Performance Summary</div>
                <div className="stats-grid">
                  <div><strong>Sessions</strong><span>{selectedGenome.performance.total_sessions}</span></div>
                  <div><strong>Success Rate</strong><span>{(selectedGenome.performance.success_rate * 100).toFixed(0)}%</span></div>
                  <div><strong>Avg Score</strong><span>{selectedGenome.performance.avg_score?.toFixed(1) ?? "-"}</span></div>
                  <div><strong>Reps Done</strong><span>{selectedGenome.performance.reps_completed}</span></div>
                  <div><strong>Reps Failed</strong><span style={{ color: "var(--danger)" }}>{selectedGenome.performance.reps_failed}</span></div>
                  <div><strong>GUPP Violations</strong><span style={{ color: selectedGenome.performance.gupp_violations > 0 ? "var(--danger)" : undefined }}>{selectedGenome.performance.gupp_violations}</span></div>
                </div>

                {selectedGenome.definition && (
                  <>
                    <div className="section-label">Agent Definition (Genome)</div>
                    <div style={{ padding: 12, background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)", fontSize: 12 }}>
                      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
                        <span><strong>Role:</strong> {selectedGenome.definition.role}</span>
                        <span><strong>Version:</strong> v{selectedGenome.definition.version}</span>
                        <span className={`tier-badge tier-${selectedGenome.definition.model_tier}`}>{selectedGenome.definition.model_tier}</span>
                        {selectedGenome.definition.classification && (
                          <span className={`classification-badge ${selectedGenome.definition.classification}`}>{selectedGenome.definition.classification.replace("_", " ")}</span>
                        )}
                      </div>
                      {selectedGenome.definition.nickname && (
                        <div style={{ marginBottom: 4 }}><strong>Nickname:</strong> {selectedGenome.definition.nickname}</div>
                      )}
                      <div style={{ marginBottom: 4 }}>
                        <strong>Tools:</strong>{" "}
                        {selectedGenome.definition.tools_allowed.length > 0
                          ? selectedGenome.definition.tools_allowed.map(t => (
                              <span key={t} style={{ display: "inline-block", padding: "1px 6px", background: "var(--bg-hover)", borderRadius: 3, marginRight: 4, fontSize: 11 }}>{t}</span>
                            ))
                          : <span className="dim">None</span>
                        }
                      </div>
                      <div><strong>Prompt Length:</strong> {selectedGenome.definition.system_prompt_length} chars</div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="empty" style={{ padding: 32 }}>Select a performer to view their genome.</div>
            )}
          </div>
        </div>
      )}

      {/* Selection Events */}
      {tab === "events" && (
        <div>
          <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
            <select
              value={eventFilter}
              onChange={e => setEventFilter(e.target.value)}
              style={{ padding: "6px 10px", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)", fontSize: 12 }}
            >
              <option value="">All Events</option>
              <option value="trust_change">Trust Changes</option>
              <option value="retirement">Retirements</option>
              <option value="rep_completed">Rep Completed</option>
              <option value="rep_failed">Rep Failed</option>
              <option value="session_completed">Session Completed</option>
              <option value="session_failed">Session Failed</option>
              <option value="gupp_violation">GUPP Violations</option>
            </select>
          </div>

          {events.length === 0 && <p className="empty">No selection events recorded.</p>}

          <div className="activity-list">
            {events.map(e => (
              <div key={e.id} className="activity-row">
                <EventTypeBadge type={e.entry_type} />
                <span className="activity-role">{e.performer_name || e.role_type}</span>
                {e.trust_before != null && e.trust_after != null && (
                  <span style={{ fontSize: 11 }}>
                    <span style={{ color: "var(--text-muted)" }}>{e.trust_before.toFixed(1)}</span>
                    {" → "}
                    <span style={{ color: e.trust_after > e.trust_before ? "var(--success)" : "var(--danger)", fontWeight: 600 }}>
                      {e.trust_after.toFixed(1)}
                    </span>
                  </span>
                )}
                {e.score != null && <span style={{ fontSize: 11, color: "var(--accent)" }}>score: {e.score.toFixed(1)}</span>}
                <span className="activity-detail">{e.details}</span>
                <span className="activity-time">{timeAgo(e.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mutations */}
      {tab === "mutations" && (
        <div>
          {mutations.length === 0 && <p className="empty">No mutation proposals recorded.</p>}
          {mutations.map(m => (
            <div key={m.id} style={{ padding: 12, marginBottom: 8, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <div>
                  <strong>{m.nickname || formatRole(m.role)}</strong>
                  <span style={{ marginLeft: 8, fontSize: 12, color: "var(--text-muted)" }}>v{m.old_version} → v{m.new_version}</span>
                </div>
                <span className={`badge ${m.status === "approved" ? "completed" : m.status === "rejected" ? "failed" : "pending"}`}>
                  {m.status}
                </span>
              </div>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>{m.reason}</p>
              <div className="code-block" style={{ fontSize: 11, maxHeight: 100, padding: 8 }}>
                {JSON.stringify(m.changes, null, 2)}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                {m.approved_by && <span>Approved by: {m.approved_by.slice(0, 8)} </span>}
                {timeAgo(m.created_at)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Simulate Mutation */}
      {tab === "simulate" && (
        <div>
          <p style={{ color: "var(--text-secondary)", marginBottom: 16, fontSize: 13 }}>
            Simulate a definition mutation in sandbox mode. No changes are applied.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 600, marginBottom: 16 }}>
            <input
              value={simDefId}
              onChange={e => setSimDefId(e.target.value)}
              placeholder="Agent Definition ID"
              style={{ padding: "8px 12px", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)", fontSize: 13 }}
            />
            <textarea
              value={simChanges}
              onChange={e => setSimChanges(e.target.value)}
              placeholder='{"model_tier": "opus"}'
              rows={4}
              style={{ padding: "8px 12px", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)", fontSize: 12, fontFamily: "monospace" }}
            />
            <input
              value={simReason}
              onChange={e => setSimReason(e.target.value)}
              placeholder="Reason for mutation..."
              style={{ padding: "8px 12px", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)", fontSize: 13 }}
            />
            <button className="primary" onClick={handleSimulate} disabled={simulating || !simDefId || !simReason}>
              {simulating ? "Simulating..." : "Run Simulation"}
            </button>
          </div>

          {simResult && (
            <div className="detail-panel">
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                <h3>Simulation Results</h3>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <RiskBadge level={simResult.risk_level} />
                  {simResult.requires_approval && <span className="badge review">NEEDS APPROVAL</span>}
                  <span className="badge completed">SANDBOX</span>
                </div>
              </div>
              <p style={{ fontSize: 13, marginBottom: 12 }}>
                <strong>{formatRole(simResult.role)}</strong> v{simResult.current_version} → v{simResult.proposed_version}
              </p>

              {simResult.impacts.map((impact, i) => (
                <div key={i} style={{ padding: 8, marginBottom: 6, background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)", fontSize: 12 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                    <strong>{impact.field}</strong>
                    <RiskBadge level={impact.risk} />
                  </div>
                  <p style={{ color: "var(--text-secondary)" }}>{impact.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
