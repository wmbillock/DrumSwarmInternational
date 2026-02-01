import { useState, useEffect } from "react";
import type { SystemHealth as SystemHealthData } from "../types";
import * as v1 from "../services/v1";

export function SystemHealth() {
  const [health, setHealth] = useState<SystemHealthData | null>(null);

  useEffect(() => {
    v1.getSystemHealth().then(setHealth).catch(() => {});
    const iv = setInterval(() => {
      v1.getSystemHealth().then(setHealth).catch(() => {});
    }, 15000);
    return () => clearInterval(iv);
  }, []);

  if (!health) return null;

  return (
    <div className="system-health-bar">
      <span className="health-stat">
        <span className="health-stat-value">{health.active_corps}</span> corps
      </span>
      <span className="health-stat">
        <span className="health-stat-value">{health.active_agents}</span>/{health.total_agents} agents
      </span>
      {health.failure_rate > 0 && (
        <span className="health-stat health-stat-warn">
          <span className="health-stat-value">{health.failure_rate}%</span> failure
        </span>
      )}
      {health.stale_reps > 0 && (
        <span className="health-stat health-stat-warn">
          <span className="health-stat-value">{health.stale_reps}</span> stale
        </span>
      )}
    </div>
  );
}
