import { useState, useEffect, useRef, useCallback } from "react";
import { useShow } from "../contexts/ShowContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { sendChat } from "../services/api"; // No v1 equivalent yet
import * as v1 from "../services/v1";
import type { ChatMessage, WebSocketEvent } from "../types";

const ROLE_COLORS: Record<string, string> = {
  user: "#58a6ff",
  system: "#8b949e",
  executive_director: "#f0883e",
  program_coordinator: "#a371f7",
  drum_major: "#e3b341",
  drill_writer: "#3fb950",
  music_writer: "#79c0ff",
  choreographer: "#d2a8ff",
  brass_caption_head: "#f78166",
  percussion_caption_head: "#d29922",
  guard_caption_head: "#bc8cff",
  visual_caption_head: "#7ee787",
  brass_tech: "#ffa657",
  percussion_tech: "#e6b422",
  front_ensemble_tech: "#d4a72c",
  guard_tech: "#c69eff",
  visual_tech: "#56d364",
};

const ROLES = [
  "executive_director", "program_coordinator", "drum_major",
  "drill_writer", "music_writer", "choreographer",
  "brass_caption_head", "percussion_caption_head",
  "guard_caption_head", "visual_caption_head",
];

function formatRole(role: string): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function ChatRoom() {
  const { corpsId } = useShow();
  const { lastMessage, connected } = useWebSocket(corpsId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [targetRole, setTargetRole] = useState("executive_director");
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load history on mount
  useEffect(() => {
    if (!corpsId) return;
    v1.getCorpsChatHistory(corpsId).then((data) => {
      setMessages(data as ChatMessage[]);
    }).catch(() => {});
  }, [corpsId]);

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;
    const event = lastMessage as unknown as WebSocketEvent;
    const ev = event as Record<string, unknown>;
    const now = new Date().toISOString();

    if (event.type === "chat") {
      // User or agent chat message
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(),
        type: "directive",
        from_role: (ev.from_role as string) || "user",
        to_role: ev.to_role as string,
        subject: (ev.content as string) || "",
        body: ev.content as string,
        created_at: now,
      }]);
    } else if (event.type === "agent_response") {
      // Agent finished and has a substantive response
      const content = ev.content as string;
      if (content && content !== "Mock response") {
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(),
          type: "feedback",
          from_role: (ev.role as string) || "system",
          subject: content.slice(0, 100),
          body: content,
          created_at: now,
        }]);
      }
    } else if (event.type === "agent_status") {
      // Show status changes as subtle system events
      const status = ev.status as string;
      const role = ev.role as string;
      // Only show meaningful transitions, skip noisy ones
      if (status === "started" || status === "completed" || status === "failed") {
        const label = role ? formatRole(role) : "Agent";
        const verb = status === "started" ? "is working..." : status === "completed" ? "finished." : "encountered an error.";
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(),
          type: "status",
          from_role: "system",
          subject: `${label} ${verb}`,
          body: ev.error ? `Error: ${ev.error}` : undefined,
          created_at: now,
        } as ChatMessage]);
      }
    } else if (event.type === "message") {
      // System broadcast (e.g. "Show activated...")
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(),
        type: "status",
        from_role: "system",
        subject: (ev.content as string) || "",
        body: ev.content as string,
        created_at: now,
      }]);
    } else if (event.type === "tool_call") {
      // Show tool use as a compact system note
      const role = ev.role as string;
      const tool = ev.tool as string;
      if (role && tool) {
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(),
          type: "status",
          from_role: "system",
          subject: `${formatRole(role)} used ${tool}`,
          created_at: now,
        }]);
      }
    }
  }, [lastMessage]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || !corpsId) return;
    const content = input.trim();
    setInput("");

    // Parse @role from input
    let role = targetRole;
    const atMatch = content.match(/^@(\w+)\s/);
    if (atMatch) {
      const matchedRole = atMatch[1].toLowerCase().replace(/ /g, "_");
      if (ROLES.includes(matchedRole)) {
        role = matchedRole;
      }
    }

    try {
      await sendChat(corpsId, content, role);
    } catch (e) {
      console.error("Failed to send chat:", e);
    }
  }, [input, corpsId, targetRole]);

  if (!corpsId) {
    return (
      <div className="chat-room" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
        Select and activate a show to start chatting with agents.
      </div>
    );
  }

  return (
    <div className="chat-room" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Connection status */}
      <div style={{ padding: "4px 12px", borderBottom: "1px solid var(--border)", fontSize: 12, color: "var(--text-muted)" }}>
        <span className={`ws-status ${connected ? "connected" : "disconnected"}`} style={{ fontSize: 11 }}>
          {connected ? "Connected" : "Disconnected"}
        </span>
        <span style={{ marginLeft: 8 }}>{messages.length} messages</span>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px" }}>
        {messages.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
            <div style={{ fontSize: 14, marginBottom: 8 }}>No messages yet.</div>
            <div style={{ fontSize: 12 }}>Send a message to an agent to get started, or activate a show to trigger autonomous work.</div>
          </div>
        )}
        {messages.map((msg, i) => {
          const isUser = msg.from_role === "user";
          const isSystem = msg.from_role === "system" || msg.type === "status";
          const roleColor = ROLE_COLORS[msg.from_role] || "var(--text-secondary)";

          if (isSystem) {
            return (
              <div key={msg.id || i} style={{ textAlign: "center", padding: "4px 0", fontSize: 12, color: "var(--text-muted)" }}>
                {msg.body || msg.subject}
              </div>
            );
          }

          return (
            <div key={msg.id || i} style={{
              display: "flex", flexDirection: "column",
              alignItems: isUser ? "flex-end" : "flex-start",
              marginBottom: 12,
            }}>
              <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 2 }}>
                <span style={{
                  fontSize: 11, fontWeight: 600, color: roleColor,
                  padding: "1px 6px", borderRadius: 4,
                  background: `${roleColor}18`,
                }}>
                  {formatRole(msg.from_role)}
                </span>
                {msg.to_role && (
                  <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    to {formatRole(msg.to_role)}
                  </span>
                )}
                {msg.created_at && (
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                    {new Date(msg.created_at).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <div style={{
                padding: "8px 12px", borderRadius: 8, maxWidth: "80%",
                background: isUser ? "var(--accent)" : "var(--bg-card)",
                color: isUser ? "#fff" : "var(--text-primary)",
                border: isUser ? "none" : "1px solid var(--border)",
                fontSize: 14, lineHeight: 1.5, whiteSpace: "pre-wrap",
              }}>
                {msg.body || msg.subject}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
        <div style={{ position: "relative", flexShrink: 0 }}>
          <button
            onClick={() => setShowRoleMenu(!showRoleMenu)}
            style={{
              padding: "8px 12px", fontSize: 12, whiteSpace: "nowrap",
              color: ROLE_COLORS[targetRole] || "var(--text-secondary)",
              background: `${ROLE_COLORS[targetRole] || "var(--text-secondary)"}18`,
              borderColor: ROLE_COLORS[targetRole] || "var(--border)",
            }}
          >
            @{formatRole(targetRole)}
          </button>
          {showRoleMenu && (
            <div style={{
              position: "absolute", bottom: "100%", left: 0, zIndex: 100,
              background: "var(--bg-card)", border: "1px solid var(--border)",
              borderRadius: 8, padding: 4, minWidth: 200, marginBottom: 4,
              boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
            }}>
              {ROLES.map((r) => (
                <button
                  key={r}
                  onClick={() => { setTargetRole(r); setShowRoleMenu(false); }}
                  style={{
                    display: "block", width: "100%", textAlign: "left", padding: "4px 8px",
                    background: r === targetRole ? "var(--bg-hover)" : "transparent",
                    border: "none", borderRadius: 4, fontSize: 12,
                    color: ROLE_COLORS[r] || "var(--text-secondary)",
                  }}
                >
                  {formatRole(r)}
                </button>
              ))}
            </div>
          )}
        </div>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder={`Message @${formatRole(targetRole)}...`}
          style={{
            flex: "1 1 auto", minWidth: 0, padding: "8px 12px", background: "var(--bg-card)",
            border: "1px solid var(--border)", borderRadius: 6,
            color: "var(--text-primary)", fontSize: 14,
          }}
        />
        <button className="primary" onClick={handleSend} style={{ flexShrink: 0 }}>Send</button>
      </div>
    </div>
  );
}
