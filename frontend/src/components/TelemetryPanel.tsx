import { useEffect, useState } from "react";
import { Badge } from "../ui";
import * as v1 from "../services/v1";
import { slugToTitle } from "../utils/formatters";

interface HealthData {
  status: string;
  active_corps?: number;
  total_agents?: number;
  [key: string]: unknown;
}

export function TelemetryPanel() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [recentActivity, setRecentActivity] = useState<v1.V1RecentActivity[]>([]);
  const [corpsCount, setCorpsCount] = useState(0);

  useEffect(() => {
    const ac = new AbortController();

    v1.getSystemHealth(ac.signal)
      .then(setHealth)
      .catch(() => {});

    v1.getRecentActivity(ac.signal)
      .then((activity) => setRecentActivity(activity.slice(0, 5)))
      .catch(() => {});

    v1.listCorps(ac.signal, true)
      .then((corps) => setCorpsCount(corps.length))
      .catch(() => {});

    return () => ac.abort();
  }, []);

  // Extract latest scores from the most recent activity entry
  const latestScores = recentActivity.length > 0
    ? recentActivity[0].top_standings || []
    : [];

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
        <span className="telemetry-stat">{health?.active_corps ?? 0} active / {corpsCount} total</span>
      </div>

      <div className="telemetry-section">
        <h4 className="telemetry-heading">Recent Rounds</h4>
        {recentActivity.length === 0 ? (
          <span className="text-muted">No rounds completed</span>
        ) : (
          <ul className="telemetry-run-list">
            {recentActivity.map((r) => (
              <li key={r.competition_id} className="telemetry-run-item">
                <span className="mono" title={r.competition_id}>
                  R{r.round} {slugToTitle(r.show_slug)}
                </span>
                <Badge variant="success">done</Badge>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="telemetry-section">
        <h4 className="telemetry-heading">Latest Scores</h4>
        {latestScores.length === 0 ? (
          <span className="text-muted">No scores</span>
        ) : (
          <ul className="telemetry-run-list">
            {latestScores.map((s) => (
              <li key={s.corps_id} className="telemetry-run-item">
                <span className="mono">#{s.rank} {s.corps_name || s.corps_id.slice(0, 8)}</span>
                <span className="show-score">{Number(s.final_score).toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
