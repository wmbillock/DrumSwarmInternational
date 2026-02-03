import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Panel, Badge } from "../ui";
import * as v1 from "../services/v1";
import { formatCaption, formatRole, formatStatus, slugToTitle } from "../utils/formatters";

const JUDGE_TYPES = ["brass", "percussion", "guard", "visual", "general_effect", "ensemble_technique"];

export function CritiquePage() {
  const { competitionId, corpsId } = useParams<{ competitionId: string; corpsId: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<v1.V1CritiqueSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [selectedJudge, setSelectedJudge] = useState("brass");
  const [error, setError] = useState("");
  const handleRetry = () => {
    setError("");
    if (!session) {
      handleStart();
    }
  };

  const handleStart = async () => {
    if (!competitionId || !corpsId) return;
    setLoading(true);
    setError("");
    try {
      const s = await v1.startCritique(competitionId, corpsId, selectedJudge);
      setSession(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start critique");
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!session || !message.trim()) return;
    setSending(true);
    try {
      const updated = await v1.sendCritiqueMessage(session.id, message.trim());
      setSession(updated);
      setMessage("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const handleComplete = async () => {
    if (!session) return;
    setSending(true);
    try {
      const updated = await v1.completeCritique(session.id);
      setSession(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to complete critique");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>Back</button>
        <h2>Critique Session</h2>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={handleRetry}>Retry</button>
        </div>
      )}

      {!session && (
        <Panel title="Start Critique">
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
            <label>
              Judge Type:
              <select value={selectedJudge} onChange={(e) => setSelectedJudge(e.target.value)} style={{ marginLeft: "0.5rem" }}>
                {JUDGE_TYPES.map((jt) => (
                  <option key={jt} value={jt}>{formatCaption(jt)}</option>
                ))}
              </select>
            </label>
            <button className="primary" onClick={handleStart} disabled={loading}>
              {loading ? "Starting..." : "Start Critique"}
            </button>
          </div>
          <p className="text-muted" style={{ marginTop: "0.5rem" }}>
            Competition: {competitionId ? slugToTitle(competitionId) : "--"} | Corps: {corpsId ? `Corps • ${corpsId.slice(0, 8)}` : "--"}
          </p>
        </Panel>
      )}

      {session && (
        <>
          <Panel title={`${formatCaption(session.judge_type)} Judge → ${formatRole(session.staff_role)}`}>
            <div className="critique-meta">
              <Badge>{formatStatus(session.status)}</Badge>
            </div>

            <div className="critique-conversation">
              {session.conversation.map((turn, i) => (
                <div key={i} className={`critique-message ${turn.role}`}>
                  <div className="critique-role">{turn.role === "judge" ? "Judge" : "Staff"}</div>
                  <div className="critique-content">{turn.content}</div>
                </div>
              ))}
            </div>

            {session.status === "active" && (
              <div className="critique-input">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Ask the judge a question or request clarification..."
                  rows={3}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                />
                <div className="critique-actions">
                  <button className="primary" onClick={handleSend} disabled={sending || !message.trim()}>
                    {sending ? "Sending..." : "Send"}
                  </button>
                  <button className="secondary" onClick={handleComplete} disabled={sending}>
                    Complete & Extract Actions
                  </button>
                </div>
              </div>
            )}
          </Panel>

          {session.action_items && (
            <Panel title="Action Items">
              <pre className="action-items-text">{session.action_items}</pre>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}
