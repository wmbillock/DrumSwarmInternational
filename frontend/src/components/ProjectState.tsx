import { useState, useEffect } from "react";
import { useShow } from "../contexts/ShowContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { getSegmentChildren, getSegment } from "../services/api"; // No v1 equivalent for segments
import * as v1 from "../services/v1";
import type { AgentSession, Segment } from "../types";

const STATUS_ICONS: Record<string, string> = {
  pending: "\u25cb",      // ○
  in_progress: "\u25d0",  // ◐
  review: "\u25d1",       // ◑
  completed: "\u25cf",    // ●
  failed: "\u2717",       // ✗
  blocked: "\u2298",      // ⊘
};

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

interface CoordNode {
  coord: Segment;
  children: CoordNode[];
}

export function ProjectState({ onSelectItem }: { onSelectItem?: (type: string, id: string) => void }) {
  const { activeShow, shows, setActiveShow, corpsId, rootCoordId } = useShow();
  const { lastMessage } = useWebSocket(corpsId);
  const [roster, setRoster] = useState<AgentSession[]>([]);
  const [coordTree, setCoordTree] = useState<CoordNode | null>(null);
  const [expandedCoords, setExpandedCoords] = useState<Set<string>>(new Set());

  // Load roster
  useEffect(() => {
    if (!corpsId) { setRoster([]); return; }
    v1.getCorpsRoster(corpsId).then((data) => setRoster(data as AgentSession[])).catch(() => {});
  }, [corpsId]);

  // Load segment tree
  useEffect(() => {
    if (!rootCoordId) { setCoordTree(null); return; }
    loadCoordTree(rootCoordId).then(setCoordTree).catch(() => {});
  }, [rootCoordId]);

  // Refresh on WebSocket events
  useEffect(() => {
    if (!lastMessage) return;
    const event = lastMessage as Record<string, unknown>;
    if (event.type === "segment_created" || event.type === "agent_status" || event.type === "rep_update") {
      if (corpsId) v1.getCorpsRoster(corpsId).then((d) => setRoster(d as AgentSession[])).catch(() => {});
      if (rootCoordId) loadCoordTree(rootCoordId).then(setCoordTree).catch(() => {});
    }
  }, [lastMessage, corpsId, rootCoordId]);

  async function loadCoordTree(coordId: string): Promise<CoordNode> {
    const coord = (await getSegment(coordId)) as Segment;
    const children = (await getSegmentChildren(coordId)) as Segment[];
    const childNodes = await Promise.all(children.map((c) => loadCoordTree(c.id)));
    return { coord, children: childNodes };
  }

  function toggleExpand(id: string) {
    setExpandedCoords((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function renderCoordNode(node: CoordNode, depth: number = 0) {
    const expanded = expandedCoords.has(node.coord.id);
    const hasChildren = node.children.length > 0;

    return (
      <div key={node.coord.id} style={{ marginLeft: depth * 16 }}>
        <div
          onClick={() => {
            if (hasChildren) toggleExpand(node.coord.id);
            onSelectItem?.("segment", node.coord.id);
          }}
          style={{
            display: "flex", alignItems: "center", gap: 6, padding: "3px 6px",
            cursor: "pointer", borderRadius: 4, fontSize: 12,
          }}
          className="hover-highlight"
        >
          {hasChildren && <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{expanded ? "\u25be" : "\u25b8"}</span>}
          <span style={{ color: statusColor(node.coord.status) }}>{STATUS_ICONS[node.coord.status] || "?"}</span>
          <span style={{ color: "var(--text-muted)", fontSize: 10, textTransform: "uppercase" }}>{node.coord.type}</span>
          <span style={{ color: "var(--text-primary)" }}>{node.coord.title}</span>
        </div>
        {expanded && node.children.map((child) => renderCoordNode(child, depth + 1))}
      </div>
    );
  }

  function statusColor(status: string) {
    switch (status) {
      case "completed": return "var(--success)";
      case "in_progress": case "review": return "var(--warning)";
      case "failed": return "var(--danger)";
      case "blocked": return "var(--danger)";
      default: return "var(--text-muted)";
    }
  }

  return (
    <div className="project-state" style={{ display: "flex", flexDirection: "column", gap: 16, padding: 12, fontSize: 13 }}>
      {/* Shows */}
      <div>
        <h4 style={{ fontSize: 11, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 6, letterSpacing: 1 }}>Shows</h4>
        {shows.map((s) => (
          <div
            key={s.id}
            onClick={() => setActiveShow(s)}
            style={{
              padding: "4px 8px", cursor: "pointer", borderRadius: 4,
              background: s.id === activeShow?.id ? "var(--bg-hover)" : "transparent",
              display: "flex", alignItems: "center", gap: 6,
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: statusColor(s.status), flexShrink: 0 }} />
            <span>{s.title}</span>
          </div>
        ))}
      </div>

      {/* Segment Tree */}
      {coordTree && (
        <div>
          <h4 style={{ fontSize: 11, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 6, letterSpacing: 1 }}>Segments</h4>
          {renderCoordNode(coordTree)}
        </div>
      )}

      {/* Agent Roster */}
      {roster.length > 0 && (
        <div>
          <h4 style={{ fontSize: 11, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 6, letterSpacing: 1 }}>Agents</h4>
          {roster.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelectItem?.("session", s.id)}
              style={{
                display: "flex", alignItems: "center", gap: 6, padding: "3px 6px",
                cursor: "pointer", borderRadius: 4,
              }}
              className="hover-highlight"
            >
              <span style={{
                width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                background: s.status === "active" ? "var(--success)" : s.status === "completed" ? "var(--info)" : s.status === "failed" ? "var(--danger)" : "var(--text-muted)",
              }} />
              <span style={{ color: ROLE_COLORS[s.role] || "var(--text-secondary)" }}>{formatRole(s.role)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
