import { useState, useRef, useEffect } from "react";
import * as v1 from "../services/v1";

interface ChatEntry {
  role: string;
  displayName?: string;
  message: string;
  tags?: string[];
  isUser: boolean;
  internal?: boolean;
}

interface Props {
  showSlug: string;
  onSpecUpdate: () => void;
}

const ROLE_COLORS: Record<string, string> = {
  program_coordinator: "var(--success, #3fb950)",
  music_writer: "var(--warning, #d29922)",
  drill_writer: "var(--info, #58a6ff)",
  choreographer: "var(--danger, #f85149)",
  judge: "var(--danger, #f44)",
};

const ROLE_LABELS: Record<string, string> = {
  program_coordinator: "Program Coordinator",
  music_writer: "Systems Architect",
  drill_writer: "UX Designer",
  choreographer: "QA Specialist",
  judge: "Judge",
};

const ROLE_ICONS: Record<string, string> = {
  program_coordinator: "\u{1F4E3}",
  music_writer: "\u{1F3D7}",
  drill_writer: "\u{1F3A8}",
  choreographer: "\u{1F6E1}",
  judge: "\u{2696}",
};

/** Minimal inline markdown: **bold**, *italic*, `code`, and line breaks. */
function renderInlineMarkdown(text: string) {
  const parts: (string | JSX.Element)[] = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    if (match[2]) {
      parts.push(<strong key={key++}>{match[2]}</strong>);
    } else if (match[3]) {
      parts.push(<em key={key++}>{match[3]}</em>);
    } else if (match[4]) {
      parts.push(<code key={key++} style={{ background: "var(--bg-secondary)", padding: "1px 4px", borderRadius: 3, fontSize: "0.9em" }}>{match[4]}</code>);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    parts.push(text.slice(last));
  }
  return parts;
}

function TypingIndicator({ role, displayName }: { role: string; displayName: string }) {
  const icon = ROLE_ICONS[role] || "";
  const color = ROLE_COLORS[role] || "var(--text-muted)";
  return (
    <div className="chat-typing">
      <span className="chat-typing-dots"><span /><span /><span /></span>
      <span style={{ color }}>{icon} {displayName}</span> is thinking...
    </div>
  );
}

/** Group consecutive internal messages together for collapsible display */
function groupMessages(messages: ChatEntry[]): (ChatEntry | { type: "deliberation"; entries: ChatEntry[] })[] {
  const result: (ChatEntry | { type: "deliberation"; entries: ChatEntry[] })[] = [];
  let internalBatch: ChatEntry[] = [];

  const flushInternal = () => {
    if (internalBatch.length > 0) {
      result.push({ type: "deliberation", entries: [...internalBatch] });
      internalBatch = [];
    }
  };

  for (const m of messages) {
    if (m.internal) {
      internalBatch.push(m);
    } else {
      flushInternal();
      result.push(m);
    }
  }
  flushInternal();
  return result;
}

function MessageBubble({ m }: { m: ChatEntry }) {
  const roleClass = m.isUser ? "user" : `agent ${m.role}${m.internal ? " internal" : ""}`;
  const icon = !m.isUser ? (ROLE_ICONS[m.role] || "") : "";

  return (
    <div className={`chat-msg ${roleClass}`}>
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
              {icon && <span style={{ marginRight: 4 }}>{icon}</span>}
              {m.displayName || ROLE_LABELS[m.role] || m.role}
            </span>
          )}
        </span>
        {m.tags && m.tags.length > 0 && (
          <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
            [{m.tags.join(", ")}]
          </span>
        )}
      </div>
      <div className="chat-msg-body">{renderInlineMarkdown(m.message)}</div>
    </div>
  );
}

export function DesignChat({ showSlug, onSpecUpdate }: Props) {
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [typingRole, setTypingRole] = useState<{ role: string; displayName: string } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load message history on mount, then greet if empty
  useEffect(() => {
    const ctrl = new AbortController();
    v1.getMessages(showSlug, ctrl.signal)
      .then(async (data) => {
        const history: ChatEntry[] = data.messages.map(m => ({
          role: m.role,
          displayName: m.display_name,
          message: m.content,
          tags: m.tags,
          isUser: m.role === "user",
        }));
        if (history.length === 0) {
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
  }, [messages, typingRole]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages(prev => [...prev, { role: "user", message: text, isUser: true }]);
    setInput("");
    setSending(true);
    setTypingRole(null);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      await v1.postMessageStream(showSlug, text, {
        onTyping: (typing) => {
          setTypingRole({ role: typing.role, displayName: typing.display_name });
        },
        onMessage: (msg) => {
          setTypingRole(null);
          setMessages(prev => [...prev, {
            role: msg.role,
            displayName: msg.display_name,
            message: msg.response,
            tags: msg.tags,
            isUser: false,
            internal: msg.internal,
          }]);
        },
        onDone: () => {
          setTypingRole(null);
          onSpecUpdate();
        },
        onError: (err) => {
          setTypingRole(null);
          setMessages(prev => [...prev, { role: "system", message: `Error: ${err.message}`, isUser: false }]);
        },
      }, ctrl.signal);
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setTypingRole(null);
        setMessages(prev => [...prev, { role: "system", message: `Error: ${err.message}`, isUser: false }]);
      }
    } finally {
      setSending(false);
      setTypingRole(null);
      abortRef.current = null;
    }
  };

  const handleContinue = async () => {
    if (sending) return;
    setSending(true);

    try {
      const resp = await v1.continueDesign(showSlug);
      appendAgentResponses(resp);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        { role: "system", message: `Error: ${err.message}`, isUser: false },
      ]);
    } finally {
      setSending(false);
    }
  };

  const appendAgentResponses = (resp: v1.V1MessageResp) => {
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
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.ctrlKey && !e.metaKey) {
      handleSend();
    } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleContinue();
    }
  };

  const grouped = groupMessages(messages);

  return (
    <div className="chat-panel">
      <div className="chat-toolbar">
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Design Room Meeting</span>
        <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8 }}>
          {ROLE_ICONS.program_coordinator} PC
          {" "}{ROLE_ICONS.music_writer} Arch
          {" "}{ROLE_ICONS.drill_writer} UX
          {" "}{ROLE_ICONS.choreographer} QA
        </span>
      </div>
      <div className="chat-messages">
        {loadingHistory && <div className="page-loading">Loading history...</div>}
        {!loadingHistory && messages.length === 0 && (
          <div className="chat-empty">
            <p className="empty" style={{ fontSize: 14 }}>
              Welcome to the Design Room. Your full design team is here.
            </p>
            <p className="empty" style={{ fontSize: 12 }}>
              Describe what you want to build. The Systems Architect, UX Designer, and QA Specialist
              will collaborate on the design while the Program Coordinator drives decisions.
            </p>
          </div>
        )}
        {grouped.map((item, i) => {
          if ("type" in item && item.type === "deliberation") {
            return (
              <details key={`delib-${i}`} className="chat-deliberation" open>
                <summary>Team Deliberation ({item.entries.length} messages)</summary>
                {item.entries.map((m, j) => (
                  <MessageBubble key={`${i}-${j}`} m={m} />
                ))}
              </details>
            );
          }
          const m = item as ChatEntry;
          // Find original index to count user rounds
          const originalIdx = messages.indexOf(m);
          return (
            <div key={i}>
              {m.isUser && originalIdx > 0 && (
                <div style={{
                  borderTop: "1px solid var(--border, #333)",
                  margin: "12px 0 8px",
                  paddingTop: 4,
                  fontSize: 10,
                  color: "var(--text-muted)",
                  textAlign: "center",
                }}>
                  Round {messages.slice(0, originalIdx).filter(msg => msg.isUser).length + 1}
                </div>
              )}
              <MessageBubble m={m} />
            </div>
          );
        })}
        {typingRole && <TypingIndicator role={typingRole.role} displayName={typingRole.displayName} />}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <button
          className="small"
          onClick={handleContinue}
          disabled={sending || messages.length === 0}
          title="Let the PC drive the next design round (Ctrl+Enter)"
          style={{ flexShrink: 0 }}
        >
          {sending ? "..." : "Continue"}
        </button>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Direct the design team... (Enter to send, Ctrl+Enter to continue)"
          disabled={sending}
        />
        <button className="primary small" onClick={handleSend} disabled={sending || !input.trim()}>
          {sending ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
