import { useState, useEffect } from "react";
import * as api from "../services/api";
import type { AgentSession } from "../types";

interface Props {
  corpsId: string | null;
}

const ROLE_COLORS: Record<string, string> = {
  executive_director: "#e74c3c",
  program_coordinator: "#e67e22",
  drill_writer: "#f1c40f",
  music_writer: "#f1c40f",
  choreographer: "#f1c40f",
  brass_caption_head: "#3498db",
  percussion_caption_head: "#3498db",
  guard_caption_head: "#3498db",
  visual_caption_head: "#3498db",
  drum_major: "#9b59b6",
  brass_tech: "#1abc9c",
  percussion_tech: "#1abc9c",
  front_ensemble_tech: "#1abc9c",
  guard_tech: "#1abc9c",
  visual_tech: "#1abc9c",
};

export function TheRoster({ corpsId }: Props) {
  const [roster, setRoster] = useState<AgentSession[]>([]);

  useEffect(() => {
    if (!corpsId) return;
    api.getRoster(corpsId).then((data) => setRoster(data as AgentSession[]));
  }, [corpsId]);

  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Roster</h2>
        <p className="empty">Select an active show to view its corps roster.</p>
      </div>
    );
  }

  // Build hierarchy tree
  const byParent = new Map<string | undefined, AgentSession[]>();
  for (const agent of roster) {
    const key = agent.parent_session_id || "root";
    if (!byParent.has(key)) byParent.set(key, []);
    byParent.get(key)!.push(agent);
  }

  const renderTree = (parentId: string): React.ReactElement[] => {
    const children = byParent.get(parentId) || [];
    return children.map((agent) => (
      <div key={agent.id} className="tree-node">
        <div
          className={`agent-card status-${agent.status}`}
          style={{ borderLeftColor: ROLE_COLORS[agent.role] || "#95a5a6" }}
        >
          <span className="role-name">{agent.role.replace(/_/g, " ")}</span>
          <span className={`badge ${agent.status}`}>{agent.status}</span>
        </div>
        <div className="tree-children">{renderTree(agent.id)}</div>
      </div>
    ));
  };

  return (
    <div className="screen">
      <h2>The Roster</h2>
      <p className="subtitle">Agent hierarchy tree, status, chain of command</p>
      <div className="tree">{renderTree("root")}</div>
    </div>
  );
}
