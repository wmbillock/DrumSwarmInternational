import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
type ContextBinderItem = v1.V1Seance["context_binder"][number];

export function SeanceSession() {
  const { seanceId } = useParams<{ seanceId: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<v1.V1Seance | null>(null);
  const [transcript, setTranscript] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [mode, setMode] = useState<"strict" | "relaxed">("strict");
  const [preview, setPreview] = useState<{ path: string; content: string; truncated: boolean } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!seanceId) return;
    Promise.all([
      v1.getSeance(seanceId),
      v1.getTranscript(seanceId),
    ])
      .then(([s, t]) => {
        setSession(s);
        setTranscript(t.transcript);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [seanceId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const handleSend = async () => {
    if (!seanceId || !message.trim() || sending) return;
    setSending(true);
    try {
      await v1.postSeanceMessage(seanceId, message.trim(), mode);
      setMessage("");
      const t = await v1.getTranscript(seanceId);
      setTranscript(t.transcript);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  };

  const handlePreview = async (item: ContextBinderItem) => {
    if (!seanceId || !item.loaded) return;
    setPreviewLoading(true);
    try {
      const p = await v1.previewArtifact(seanceId, item.path);
      setPreview(p);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  if (loading) return <div className="page-loading">Loading seance...</div>;
  if (error && !session) return <div className="dashboard"><div className="error-banner">{error}</div></div>;
  if (!session) return <div className="dashboard"><div className="error-banner">Session not found</div></div>;

  return (
    <div className="design-room">
      <div className="design-room-header">
        <button className="back-btn small" onClick={() => navigate(`/corps/${session.corps_id}/history`)}>Back</button>
        <h2>Seance: {session.corps_id} / {session.season_id}</h2>
        <span className={`badge ${session.status}`}>{session.status}</span>
        {session.show_slug && <span className="corps-badge">{session.show_slug}</span>}
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="design-room-panes">
        {/* Left: Chat */}
        <div className="design-room-left">
          <div className="chat-panel">
            <div className="chat-messages">
              <TranscriptView transcript={transcript} />
              <div ref={chatEndRef} />
            </div>
            <div className="chat-input-row">
              <select
                value={mode}
                onChange={e => setMode(e.target.value as "strict" | "relaxed")}
                disabled={session.status === "closed"}
              >
                <option value="strict">Strict</option>
                <option value="relaxed">Relaxed</option>
              </select>
              <input
                value={message}
                onChange={e => setMessage(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSend()}
                placeholder={session.status === "closed" ? "Session closed" : "Ask the Executive Director..."}
                disabled={session.status === "closed" || sending}
              />
              <button
                className="primary"
                onClick={handleSend}
                disabled={session.status === "closed" || sending || !message.trim()}
              >
                {sending ? "..." : "Send"}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Context Binder */}
        <div className="design-room-right" style={{ overflow: "auto", padding: 16 }}>
          <h3 style={{ fontSize: 14, marginBottom: 12, color: "var(--text-secondary)" }}>Context Binder</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 16 }}>
            {session.context_binder.map(item => (
              <div
                key={item.path}
                className={`agent-row ${item.loaded ? "clickable" : ""}`}
                style={{ opacity: item.loaded ? 1 : 0.5 }}
                onClick={() => handlePreview(item)}
              >
                <span className="badge" style={{ fontSize: 10, minWidth: 70, textAlign: "center" }}>
                  {item.type}
                </span>
                <span className="agent-nickname" style={{ fontSize: 12 }}>{item.path}</span>
                <span style={{ fontSize: 11, color: item.loaded ? "var(--success)" : "var(--text-muted)" }}>
                  {item.loaded ? "loaded" : "empty"}
                </span>
              </div>
            ))}
          </div>

          {/* Session Metadata */}
          <h3 style={{ fontSize: 14, marginBottom: 8, color: "var(--text-secondary)" }}>Session</h3>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 4, marginBottom: 16 }}>
            <span>ID: <code>{session.seance_id}</code></span>
            <span>Participant: {session.participant}</span>
            <span>Created: {new Date(session.created_at).toLocaleString()}</span>
            <span>Entry: {session.entry_id}</span>
          </div>

          {/* Artifact Preview */}
          {previewLoading && <div className="tab-loading">Loading artifact...</div>}
          {preview && !previewLoading && (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <h3 style={{ fontSize: 14, color: "var(--text-secondary)" }}>Preview: {preview.path}</h3>
                <button className="small" onClick={() => setPreview(null)}>Close</button>
              </div>
              <div className="code-block">
                <pre style={{ whiteSpace: "pre-wrap", fontSize: 11 }}>{preview.content}</pre>
              </div>
              {preview.truncated && (
                <p style={{ fontSize: 11, color: "var(--warning)", marginTop: 4 }}>Content truncated.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TranscriptView({ transcript }: { transcript: string }) {
  // Parse transcript lines into chat messages
  const lines = transcript.split("\n");
  const messages: { role: string; text: string }[] = [];

  for (const line of lines) {
    const match = line.match(/^\*\*\[(\w+)\]\*\*\s*(.*)/);
    if (match) {
      messages.push({ role: match[1], text: match[2] });
    }
  }

  if (messages.length === 0) {
    return <div className="chat-empty"><p className="empty">No messages yet. Start the conversation.</p></div>;
  }

  return (
    <>
      {messages.map((msg, i) => (
        <div key={i} className={`chat-msg ${msg.role === "user" ? "user" : "agent"}`}>
          <div className="chat-msg-header">
            <span className="chat-sender">{msg.role}</span>
          </div>
          <div className="chat-msg-body">{msg.text}</div>
        </div>
      ))}
    </>
  );
}
