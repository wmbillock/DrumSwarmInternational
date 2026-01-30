import { useEffect, useRef, useState, useCallback } from "react";
import type { WebSocketMessage } from "../types";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export function useWebSocket(corpsId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    if (!corpsId) return;

    const ws = new WebSocket(`${WS_URL}/ws/${corpsId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        setLastMessage(JSON.parse(event.data));
      } catch {
        setLastMessage({ type: "raw", data: event.data });
      }
    };

    return () => {
      ws.close();
      setConnected(false);
    };
  }, [corpsId]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === "string" ? data : JSON.stringify(data));
    }
  }, []);

  return { connected, lastMessage, send };
}
