import { useState, useEffect } from "react";
import { useShow } from "../contexts/ShowContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { getRoster, getSessionActivity } from "../services/api";
import type { AgentSession, SessionActivity } from "../types";

const ROLE_COLORS: Record<string, string> = {
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

function formatRole(role: string): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

interface TreeNode {
  session: AgentSession;
  children: TreeNode[];
}

function buildTree(sessions: AgentSession[]): TreeNode[] {
  const map = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];

  for (const s of sessions) {
    map.set(s.id, { session: s, children: [] });
  }
  for (const s of sessions) {
    const node = map.get(s.id)!;
    if (s.parent_session_id && map.has(s.parent_session_id)) {
      map.get(s.parent_session_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

export function CorpsDetail() {
  const { corpsId } = useShow();
  const { lastMessage } = useWebSocket(corpsId);
  const [roster, setRoster] = useState<AgentSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [activity, setActivity] = useState<SessionActivity | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!corpsId) return;
    getRoster(corpsId).then((d) => setRoster(d as AgentSession[])).catch(() => {});
  }, [corpsId]);

  useEffect(() => {
    if (!lastMessage) return;
    if (corpsId) getRoster(corpsId).then((d) => setRoster(d as AgentSession[])).catch(() => {});
  }, [lastMessage, corpsId]);

  useEffect(() => {
    if (!selectedSession) { setActivity(null); return; }
    getSessionActivity(selectedSession).then((d) => setActivity(d as SessionActivity)).catch(() => {});
  }, [selectedSession]);

  function toggleNode(id: string) {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  const tree = buildTree(roster);

  function renderNode(node: TreeNode, depth: number = 0) {
    const { session } = node;
    const expanded = expandedNodes.has(session.id);
    const isSelected = selectedSession === session.id;
    const color = ROLE_COLORS[session.role] || "var(--text-secondary)";

    return (
      <div key={session.id} style={{ marginLeft: depth * 20 }}>
        <div
          onClick={() => {
            setSelectedSession(session.id);
            if (node.children.length) toggleNode(session.id);
          }}
          style={{
            display: "flex", alignItems: "center", gap: 8, padding: "6px 8px",
            cursor: "pointer", borderRadius: 6,
            background: isSelected ? "var(--bg-hover)" : "transparent",
            border: isSelected ? "1px solid var(--border)" : "1px solid transparent",
          }}
        >
          {/* Status dot */}
          <span style={{
            width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
            background: session.status === "active" ? "var(--success)" : session.status === "completed" ? "var(--info)" : session.status === "failed" ? "var(--danger)" : "var(--text-muted)",
            animation: session.status === "active" ? "pulse 2s infinite" : "none",
          }} />
          <span style={{ color, fontWeight: 500, fontSize: 13 }}>{formatRole(session.role)}</span>
          <span className={`badge ${session.status}`} style={{ fontSize: 10 }}>{session.status}</span>
          {node.children.length > 0 && (
            <span style={{ fontSize: 10, color: "var(--text-muted)", marginLeft: "auto" }}>
              {expanded ? "\u25be" : "\u25b8"} {node.children.length}
            </span>
          )}
        </div>
        {expanded && node.children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  }

  if (!corpsId) {
    return <div style={{ padding: 20, color: "var(--text-muted)" }}>Select an active show to see corps details.</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%" }}>
      <h3 style={{ fontSize: 14, color: "var(--text-secondary)", padding: "0 8px" }}>Agent Invocation Hierarchy</h3>

      {/* Tree */}
      <div style={{ flex: activity ? 0.5 : 1, overflowY: "auto", padding: "0 8px" }}>
        {tree.map((node) => renderNode(node))}
      </div>

      {/* Activity detail */}
      {activity && (
        <div style={{ flex: 0.5, borderTop: "1px solid var(--border)", overflowY: "auto", padding: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h4 style={{ fontSize: 13, color: ROLE_COLORS[activity.role] || "var(--text-secondary)" }}>
              {formatRole(activity.role)} Activity
            </h4>
            <span className={`badge ${activity.status}`}>{activity.status}</span>
          </div>

          {/* @ts-ignore */}
          {activity.iterations && activity.iterations.length > 0 && (
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
              {activity.iterations.length} iterations
            </div>
          )}

          {/* Tool calls */}
          {/* @ts-ignore */}
          {activity.tool_calls && activity.tool_calls.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h5 style={{ fontSize: 11, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>Tool Calls</h5>
              {activity.tool_calls.map((tc: any, i: number) => (
                <div key={i} style={{ fontSize: 12, padding: "4px 8px", background: "var(--bg-card)", borderRadius: 4, marginBottom: 4, fontFamily: "monospace", border: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--accent)" }}>{tc.tool || "unknown"}</span>
                  <span style={{ color: "var(--text-muted)" }}>({JSON.stringify(tc.arguments || {}).slice(0, 100)})</span>
                  {tc.result && (
                    <div style={{ color: (tc.result as any).success ? "var(--success)" : "var(--danger)", marginTop: 2 }}>
                      {(tc.result as any).success ? "\u2713" : "\u2717"} {JSON.stringify((tc.result as any).output || (tc.result as any).error).slice(0, 100)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Final response */}
          {activity.final_response && (
            <div>
              <h5 style={{ fontSize: 11, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>Response</h5>
              <div style={{ fontSize: 12, padding: 8, background: "var(--bg-card)", borderRadius: 4, border: "1px solid var(--border)", whiteSpace: "pre-wrap", maxHeight: 200, overflowY: "auto" }}>
                {String(activity.final_response)}
              </div>
            </div>
          )}

          {/* Messages */}
          {/* @ts-ignore */}
          {activity.messages && activity.messages.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h5 style={{ fontSize: 11, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>Messages</h5>
              {activity.messages.map((m: any) => (
                <div key={m.id || Math.random()} style={{ fontSize: 12, padding: "4px 8px", marginBottom: 4, border: "1px solid var(--border)", borderRadius: 4 }}>
                  <span style={{ color: ROLE_COLORS[m.from_role] || "var(--text-muted)" }}>{formatRole(m.from_role || "unknown")}</span>
                  {" \u2192 "}
                  <span style={{ color: ROLE_COLORS[m.to_role || ""] || "var(--text-muted)" }}>{formatRole(m.to_role || "broadcast")}</span>
                  <span style={{ color: "var(--text-secondary)", marginLeft: 8 }}>{m.subject || ""}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
