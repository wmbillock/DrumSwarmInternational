import { useState, useEffect, useRef } from "react";
import type { AgentSession, ChatMessage } from "../types";
import * as v1 from "../services/v1";
import { useWebSocket } from "../hooks/useWebSocket";

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

function TierBadge({ tier }: { tier?: string }) {
  if (!tier) return null;
  return <span className={`tier-badge tier-${tier}`}>{tier}</span>;
}

export function AdminChat() {
  const [corpsId, setCorpsId] = useState<string | null>(null);
  const [roster, setRoster] = useState<AgentSession[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatTarget, setChatTarget] = useState("executive_director");
  const chatEndRef = useRef<HTMLDivElement>(null);

  const { connected, events } = useWebSocket(corpsId);

  useEffect(() => {
    v1.getAdminCorps().then(data => {
      setCorpsId(data.id);
      setRoster(data.roster);
      v1.getCorpsChatHistory(data.id).then(setChatHistory).catch(() => setChatHistory([]));
    }).catch(() => {});
  }, []);

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
  for (const e of events) {
    if (e.type === "chat" || e.type === "agent_response") {
      const id = (e as Record<string, unknown>).message_id as string | undefined;
      const contentKey = id || `ws:${e.from_role || e.role}:${(e.content || "").slice(0, 100)}`;
      if (seenIds.has(contentKey)) continue;
      seenIds.add(contentKey);
      allChat.push({ from: e.from_role || e.role || "agent", nickname: e.nickname, content: e.content || "", time: undefined });
    }
  }

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [allChat.length]);

  const handleSend = async () => {
    if (!chatInput.trim() || !corpsId) return;
    await v1.sendCorpsChat(corpsId, chatInput.trim(), chatTarget);
    setChatInput("");
  };

  const uniqueRoles = [...new Set(roster.map(r => r.role))].sort();

  return (
    <div className="admin-chat-view">
      <div className="admin-chat-header">
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
              <p className="hint">This is where the staff gathers after the run to review, discuss, and plan.</p>
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
