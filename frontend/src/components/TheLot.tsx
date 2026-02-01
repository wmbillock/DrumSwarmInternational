import { useState, useEffect, useCallback } from "react";
import * as v1 from "../services/v1";
import type { Message } from "../types";

interface Props {
  corpsId: string | null;
}

export function TheLot({ corpsId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [filterRole, setFilterRole] = useState("");

  const loadMessages = useCallback(async () => {
    if (!corpsId) return;
    const data = (await v1.pollMessages(corpsId)) as Message[];
    setMessages(data);
  }, [corpsId, filterRole]);

  useEffect(() => { loadMessages(); }, [loadMessages]);

  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Lot</h2>
        <p className="empty">Select an active show to view communications.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>The Lot</h2>
      <p className="subtitle">Messages, problem queue, escalations, approvals</p>
      <div className="lot-controls">
        <input
          placeholder="Filter by role"
          value={filterRole}
          onChange={(e) => setFilterRole(e.target.value)}
        />
        <button onClick={loadMessages}>Refresh</button>
      </div>
      <div className="message-list">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-card priority-${msg.priority} type-${msg.type}`}>
            <div className="message-header">
              <span className={`badge priority-${msg.priority}`}>{msg.priority}</span>
              <span className="badge type">{msg.type}</span>
              <span className="from">{msg.from_role}</span>
              {msg.to_role && <span className="to">&rarr; {msg.to_role}</span>}
            </div>
            <div className="message-subject">{msg.subject}</div>
            {msg.acknowledged_at && (
              <span className="badge ack">Acknowledged</span>
            )}
          </div>
        ))}
        {messages.length === 0 && <p className="empty">No messages.</p>}
      </div>
    </div>
  );
}
