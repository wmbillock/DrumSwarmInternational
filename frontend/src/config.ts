/**
 * Shared configuration for API and WebSocket URLs.
 *
 * When VITE_API_URL / VITE_WS_URL env vars are set, those are used.
 * Otherwise, the host is derived from window.location.hostname so the
 * frontend works from any device on the local network (not just localhost).
 */

const API_PORT = 4224;

function resolveApiBase(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL as string;
  }
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `http://${host}:${API_PORT}`;
}

function resolveWsBase(): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL as string;
  }
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `ws://${host}:${API_PORT}`;
}

export const API_BASE = resolveApiBase();
export const WS_BASE = resolveWsBase();
