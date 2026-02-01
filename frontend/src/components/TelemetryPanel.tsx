import { useEffect, useState } from "react";
import { Badge } from "../ui";
import * as v1 from "../services/v1";

interface HealthData {
  status: string;
  active_corps?: number;
  total_agents?: number;
  [key: string]: unknown;
}

export function TelemetryPanel() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [recentRuns, setRecentRuns] = useState<v1.V1Run[]>([]);
  const [corpsCount, setCorpsCount] = useState(0);

  useEffect(() => {
    const ac = new AbortController();

    fetch(
      `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/system-health`,
      { signal: ac.signal }
    )
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => {});

    v1.listRuns(undefined, ac.signal)
      .then((runs) => setRecentRuns(runs.slice(0, 5)))
      .catch(() => {});

    v1.listCorps(ac.signal)
      .then((corps) => setCorpsCount(corps.length))
      .catch(() => {});

    return () => ac.abort();
  }, []);

  return (
    <aside className="telemetry-panel">
      <div className="telemetry-section">
        <h4 className="telemetry-heading">System Health</h4>
        {health ? (
          <div className="telemetry-health">
            <Badge variant={health.status === "ok" ? "success" : "warning"}>
              {health.status || "unknown"}
            </Badge>
            {health.total_agents !== undefined && (
              <span className="telemetry-stat">{health.total_agents} agents</span>
            )}
          </div>
        ) : (
          <span className="text-muted">Loading...</span>
        )}
      </div>

      <div className="telemetry-section">
        <h4 className="telemetry-heading">Corps</h4>
        <span className="telemetry-stat">{corpsCount} registered</span>
      </div>

      <div className="telemetry-section">
        <h4 className="telemetry-heading">Recent Runs</h4>
        {recentRuns.length === 0 ? (
          <span className="text-muted">No runs</span>
        ) : (
          <ul className="telemetry-run-list">
            {recentRuns.map((r) => (
              <li key={r.run_id} className="telemetry-run-item">
                <span className="mono">{r.run_id.slice(0, 20)}</span>
                <Badge
                  variant={
                    r.status === "completed"
                      ? "success"
                      : r.status === "failed"
                        ? "danger"
                        : "warning"
                  }
                >
                  {r.status}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
