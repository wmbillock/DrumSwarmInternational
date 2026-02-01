import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import * as api from "../services/api";
import * as v1 from "../services/v1";
import type { JudgeTape, CritiqueDetail, CritiqueActionsResponse } from "../types";

function formatRole(role: string): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function ScoreBadge({ value }: { value: number }) {
  const cls = value >= 80 ? "success" : value >= 60 ? "review" : "failed";
  return <span className={`badge ${cls}`}>{value.toFixed(1)}</span>;
}

function RiskBadge({ rework, escalation }: { rework: boolean; escalation: boolean }) {
  if (escalation) return <span className="badge failed">ESCALATION</span>;
  if (rework) return <span className="badge review">REWORK</span>;
  return <span className="badge completed">CLEAN</span>;
}

export function JudgingCritique() {
  const { corpsId } = useParams<{ corpsId: string }>();
  const [tapes, setTapes] = useState<JudgeTape[]>([]);
  const [selectedRep, setSelectedRep] = useState<string | null>(null);
  const [critique, setCritique] = useState<CritiqueDetail | null>(null);
  const [actions, setActions] = useState<CritiqueActionsResponse | null>(null);
  const [tab, setTab] = useState<"tapes" | "actions">("tapes");
  const [exportMd, setExportMd] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [inputCorps, setInputCorps] = useState(corpsId || "");

  const activeCorps = corpsId || inputCorps;

  const loadTapes = async (cid: string) => {
    setLoading(true);
    try {
      const [t, a] = await Promise.all([
        v1.listJudgingTapes(cid),
        api.getCritiqueActions(cid),
      ]);
      setTapes(t);
      setActions(a);
    } catch { setTapes([]); setActions(null); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (activeCorps) loadTapes(activeCorps);
    else setLoading(false);
  }, [activeCorps]);

  const handleSelectRep = async (repId: string) => {
    setSelectedRep(repId);
    setExportMd(null);
    if (!activeCorps) return;
    try {
      const c = await v1.getJudgingTape(repId);
      setCritique(c);
    } catch { setCritique(null); }
  };

  const handleExport = async () => {
    if (!activeCorps || !selectedRep) return;
    try {
      const result = await api.exportJudgeTape(activeCorps, selectedRep);
      setExportMd(result.markdown);
    } catch (e: any) { setExportMd(`Export failed: ${e.message}`); }
  };

  // No corps specified — show input
  if (!activeCorps) {
    return (
      <div className="dashboard">
        <h2 className="page-title">Judging & Critique</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 16 }}>
          Enter a corps ID to view judge tapes and critique actions.
        </p>
        <div className="create-form">
          <input
            value={inputCorps}
            onChange={e => setInputCorps(e.target.value)}
            onKeyDown={e => e.key === "Enter" && loadTapes(inputCorps)}
            placeholder="Corps ID..."
          />
          <button className="primary" onClick={() => loadTapes(inputCorps)}>Load</button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dash-header">
        <h2 className="page-title">Judging & Critique</h2>
        <span className="corps-badge">{activeCorps.slice(0, 12)}</span>
      </div>

      <div className="info-tabs" style={{ marginBottom: 16 }}>
        <button className={`tab ${tab === "tapes" ? "active" : ""}`} onClick={() => setTab("tapes")}>
          Judge Tapes ({tapes.length})
        </button>
        <button className={`tab ${tab === "actions" ? "active" : ""}`} onClick={() => setTab("actions")}>
          Critique to Actions {actions ? `(${actions.total_actions})` : ""}
        </button>
      </div>

      {loading && <div className="page-loading">Loading judge data...</div>}

      {!loading && tab === "tapes" && (
        <div style={{ display: "flex", gap: 16 }}>
          {/* Tape list */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {tapes.length === 0 && <p className="empty">No scored reps found for this corps.</p>}
            {tapes.map(t => (
              <div
                key={t.rep_id}
                className={`show-card ${selectedRep === t.rep_id ? "status-active" : ""}`}
                onClick={() => handleSelectRep(t.rep_id)}
                style={{ marginBottom: 8 }}
              >
                <div className="show-card-header">
                  <h3>{t.segment_title || t.rep_id.slice(0, 12)}</h3>
                  <ScoreBadge value={t.composite.final_score} />
                </div>
                <div className="show-stats">
                  <span>{t.score_count} scores</span>
                  <span>{t.rep_status}</span>
                  <RiskBadge rework={t.composite.needs_rework} escalation={t.composite.needs_escalation} />
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
                  {Object.entries(t.captions).map(([jt, scores]) => {
                    const avg = scores.reduce((s, c) => s + c.value, 0) / scores.length;
                    return (
                      <span key={jt} style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                        {jt.replace("_", " ")}: <strong>{avg.toFixed(0)}</strong>
                      </span>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Detail pane */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {critique && selectedRep ? (
              <div className="detail-panel">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <h3>Rep Critique</h3>
                  <button className="small" onClick={handleExport}>Export Tape</button>
                </div>
                <p style={{ marginBottom: 8 }}>
                  <strong>Assessment:</strong> {critique.overall_assessment || "N/A"}
                </p>
                {critique.needs_rework && (
                  <div className="info-msg" style={{ borderColor: "var(--warning)", color: "var(--warning)", marginBottom: 12 }}>
                    Rework required — score below threshold.
                  </div>
                )}

                {critique.feedbacks.map((fb, i) => (
                  <div key={i} style={{ marginBottom: 12, padding: "8px 12px", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <strong style={{ textTransform: "capitalize" }}>{fb.judge_type.replace("_", " ")}</strong>
                      <ScoreBadge value={fb.score_value} />
                    </div>
                    {fb.feedback && <p style={{ fontSize: 12, color: "var(--text-secondary)", fontStyle: "italic", marginBottom: 4 }}>{fb.feedback}</p>}
                    {fb.strengths.length > 0 && (
                      <div style={{ fontSize: 12, color: "var(--success)", marginBottom: 2 }}>
                        {fb.strengths.map((s, j) => <div key={j}>+ {s}</div>)}
                      </div>
                    )}
                    {fb.weaknesses.length > 0 && (
                      <div style={{ fontSize: 12, color: "var(--danger)", marginBottom: 2 }}>
                        {fb.weaknesses.map((w, j) => <div key={j}>- {w}</div>)}
                      </div>
                    )}
                    {fb.action_items.length > 0 && (
                      <div style={{ fontSize: 12, color: "var(--warning)" }}>
                        {fb.action_items.map((a, j) => <div key={j}>→ {a}</div>)}
                      </div>
                    )}
                  </div>
                ))}

                {exportMd && (
                  <div style={{ marginTop: 16 }}>
                    <h4 style={{ marginBottom: 8 }}>Exported Judge Tape</h4>
                    <div className="code-block" style={{ whiteSpace: "pre-wrap" }}>{exportMd}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty" style={{ padding: 32 }}>Select a rep to view its judge tape.</div>
            )}
          </div>
        </div>
      )}

      {!loading && tab === "actions" && actions && (
        <div>
          {actions.total_actions === 0 && <p className="empty">No actionable critiques found.</p>}
          {Object.entries(actions.by_role).map(([role, roleActions]) => (
            <div key={role} style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, marginBottom: 8 }}>
                <span className="badge active">{formatRole(role)}</span>
                <span style={{ marginLeft: 8, fontSize: 12, color: "var(--text-muted)" }}>
                  {roleActions.length} action{roleActions.length !== 1 ? "s" : ""}
                </span>
              </h3>
              {roleActions.map((action, i) => (
                <div key={i} style={{ padding: "8px 12px", marginBottom: 4, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 13 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                    <span style={{ textTransform: "capitalize", fontWeight: 500 }}>{action.judge_type.replace("_", " ")}</span>
                    <ScoreBadge value={action.score} />
                    <span className="mono" style={{ color: "var(--text-muted)" }}>{action.rep_id.slice(0, 8)}</span>
                  </div>
                  {action.weaknesses.map((w, j) => (
                    <div key={`w${j}`} style={{ fontSize: 12, color: "var(--danger)" }}>- {w}</div>
                  ))}
                  {action.action_items.map((a, j) => (
                    <div key={`a${j}`} style={{ fontSize: 12, color: "var(--warning)" }}>→ {a}</div>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
