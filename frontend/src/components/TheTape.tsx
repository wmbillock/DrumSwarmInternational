import { useState, useEffect } from "react";
import { useWebSocket } from "../hooks/useWebSocket";

interface Props {
  corpsId: string | null;
}

interface LogEntry {
  id: number;
  timestamp: string;
  type: string;
  message: string;
}

export function TheTape({ corpsId }: Props) {
  const { connected, lastMessage } = useWebSocket(corpsId);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (!lastMessage || paused) return;
    setLogs((prev) => [
      {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        type: lastMessage.type,
        message: JSON.stringify(lastMessage.data),
      },
      ...prev.slice(0, 499),
    ]);
  }, [lastMessage, paused]);

  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Tape</h2>
        <p className="empty">Select an active show to view the rehearsal log.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>The Tape</h2>
      <p className="subtitle">Real-time activity feed</p>
      <div className="tape-controls">
        <span className={`ws-status ${connected ? "connected" : "disconnected"}`}>
          {connected ? "Connected" : "Disconnected"}
        </span>
        <button onClick={() => setPaused(!paused)}>
          {paused ? "Resume" : "Pause"}
        </button>
        <button onClick={() => setLogs([])}>Clear</button>
      </div>
      <div className="tape-log">
        {logs.map((entry) => (
          <div key={entry.id} className={`log-entry type-${entry.type}`}>
            <span className="log-time">
              {new Date(entry.timestamp).toLocaleTimeString()}
            </span>
            <span className="log-type">{entry.type}</span>
            <span className="log-msg">{entry.message}</span>
          </div>
        ))}
        {logs.length === 0 && (
          <p className="empty">Waiting for activity...</p>
        )}
      </div>
    </div>
  );
}
