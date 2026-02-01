import { useEffect, useRef, useState, useCallback } from "react";
import type { WebSocketEvent } from "../types";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];
const HEARTBEAT_INTERVAL = 25000;
const MAX_RECONNECT_ATTEMPTS = 20;

export function useWebSocket(corpsId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketEvent | null>(null);
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimer = useRef<NodeJS.Timeout | null>(null);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimer.current) {
      clearInterval(heartbeatTimer.current as any);
      heartbeatTimer.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    stopHeartbeat();
    heartbeatTimer.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, HEARTBEAT_INTERVAL);
  }, [stopHeartbeat]);

  const connect = useCallback(() => {
    if (!corpsId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (reconnectAttempt.current >= MAX_RECONNECT_ATTEMPTS) return;

    const ws = new WebSocket(`${WS_URL}/ws/${corpsId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectAttempt.current = 0;
      startHeartbeat();
    };

    ws.onclose = () => {
      setConnected(false);
      stopHeartbeat();
      if (reconnectAttempt.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = RECONNECT_DELAYS[Math.min(reconnectAttempt.current, RECONNECT_DELAYS.length - 1)];
        reconnectAttempt.current++;
        reconnectTimer.current = setTimeout(connect, delay);
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "pong" || data.type === "ack") return;
        setLastMessage(data);
        setEvents(prev => [...prev.slice(-200), data]);
      } catch {
        // ignore unparseable messages
      }
    };

    ws.onerror = () => {};
  }, [corpsId, startHeartbeat, stopHeartbeat]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current as any);
      }
      stopHeartbeat();
      wsRef.current?.close();
      setConnected(false);
    };
  }, [connect, stopHeartbeat]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === "string" ? data : JSON.stringify(data));
    }
  }, []);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { connected, lastMessage, events, send, clearEvents };
}
