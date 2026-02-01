import { useState, useRef, useEffect } from "react";
import { sendDesignMessage } from "../services/api";
import type { DesignMessage } from "../types";

interface ChatEntry {
  role: string;
  message: string;
  tags?: string[];
  isUser: boolean;
}

interface Props {
  showSlug: string;
  onSpecUpdate: () => void;
}

export function DesignChat({ showSlug, onSpecUpdate }: Props) {
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages(prev => [...prev, { role: "user", message: text, isUser: true }]);
    setInput("");
    setSending(true);

    try {
      const resp: DesignMessage = await sendDesignMessage(showSlug, text);
      setMessages(prev => [
        ...prev,
        { role: resp.role, message: resp.response, tags: resp.tags, isUser: false },
      ]);
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
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Design Chat</span>
      </div>
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p className="empty">Send a message to start designing your show.</p>
            <p className="empty">Mention brass, drill, guard, or themes to route to creative staff.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.isUser ? "user" : "agent"}`}>
            <div className="chat-msg-header">
              <span className="chat-sender">{m.isUser ? "You" : m.role}</span>
              {m.tags && m.tags.length > 0 && (
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                  [{m.tags.join(", ")}]
                </span>
              )}
            </div>
            <div className="chat-msg-body">{m.message}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSend()}
          placeholder="Describe your show idea..."
          disabled={sending}
        />
        <button className="primary small" onClick={handleSend} disabled={sending || !input.trim()}>
          {sending ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
