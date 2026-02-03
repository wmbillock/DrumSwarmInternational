import { useState, useRef, useEffect } from "react";
import * as v1 from "../services/v1";

interface ChatEntry {
  role: string;
  displayName?: string;
  message: string;
  tags?: string[];
  isUser: boolean;
}

interface Props {
  showSlug: string;
  onSpecUpdate: () => void;
}

const ROLE_COLORS: Record<string, string> = {
  program_coordinator: "var(--accent, #6c9)",
  music_writer: "var(--warning, #fc6)",
  drill_writer: "var(--info, #6cf)",
  choreographer: "var(--danger, #f69)",
  judge: "var(--danger, #f44)",
};

export function DesignChat({ showSlug, onSpecUpdate }: Props) {
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load message history on mount, then greet if empty
  useEffect(() => {
    const ctrl = new AbortController();
    v1.getMessages(showSlug, ctrl.signal)
      .then(async (data) => {
        const history: ChatEntry[] = data.messages.map(m => ({
          role: m.role,
          message: m.content,
          tags: m.tags,
          isUser: m.role === "user",
        }));
        if (history.length === 0) {
          // Auto-greet: have the PC welcome the director
          try {
            const greeting = await v1.greetThread(showSlug, ctrl.signal);
            history.push({
              role: greeting.role,
              displayName: greeting.display_name,
              message: greeting.response,
              isUser: false,
            });
          } catch { /* greeting is best-effort */ }
        }
        setMessages(history);
      })
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
    return () => ctrl.abort();
  }, [showSlug]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages(prev => [...prev, { role: "user", message: text, isUser: true }]);
    setInput("");
    setSending(true);

    try {
      const resp = await v1.postMessage(showSlug, text);

      // Handle multiple agent responses
      const agentResponses = resp.responses || [{ role: resp.role, display_name: resp.role, tags: resp.tags, response: resp.response }];
      const newEntries: ChatEntry[] = agentResponses.map(r => ({
        role: r.role,
        displayName: r.display_name,
        message: r.response,
        tags: r.tags,
        isUser: false,
      }));
      setMessages(prev => [...prev, ...newEntries]);
      onSpecUpdate();
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        { role: "system", message: `Error: ${err.message}`, isUser: false },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-toolbar">
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Design Room Meeting</span>
        <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8 }}>
          PC + Music + Drill + Guard
        </span>
      </div>
      <div className="chat-messages">
        {loadingHistory && <div className="page-loading">Loading history...</div>}
        {!loadingHistory && messages.length === 0 && (
          <div className="chat-empty">
            <p className="empty" style={{ fontSize: 14 }}>
              Welcome to the Design Room. The Program Coordinator is ready to lead the discussion.
            </p>
            <p className="empty" style={{ fontSize: 12 }}>
              Describe your show concept and the design team will collaborate with you to flesh it out.
              Mention brass, drill, guard, or themes — the relevant specialists will join the conversation.
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.isUser ? "user" : "agent"}`}>
            <div className="chat-msg-header">
              <span className="chat-sender">
                {m.isUser ? "You (Director)" : (
                  <span
                    className="badge"
                    style={{
                      borderLeft: `3px solid ${ROLE_COLORS[m.role] || "var(--text-muted)"}`,
                      paddingLeft: 6,
                    }}
                  >
                    {m.displayName || m.role}
                  </span>
                )}
              </span>
              {m.tags && m.tags.length > 0 && (
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                  [{m.tags.join(", ")}]
                </span>
              )}
            </div>
            <div className="chat-msg-body">{m.message}</div>
          </div>
        ))}
        {sending && (
          <div className="chat-msg agent">
            <div className="chat-msg-body" style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
              Design team is discussing...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSend()}
          placeholder="Share your vision with the design team..."
          disabled={sending}
        />
        <button className="primary small" onClick={handleSend} disabled={sending || !input.trim()}>
          {sending ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
