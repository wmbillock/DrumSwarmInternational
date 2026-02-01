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
  const [topScores, setTopScores] = useState<v1.V1StandingEntry[]>([]);

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

    v1.listCompetitions(ac.signal)
      .then((comps) => {
        const completed = comps.filter((c) => c.status === "completed");
        if (completed.length === 0) return;
        const latest = completed[completed.length - 1];
        return v1.getScores(latest.competition_id, ac.signal);
      })
      .then((standings) => {
        if (standings) {
          setTopScores(standings.results.slice(0, 3));
        }
      })
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

      <div className="telemetry-section">
        <h4 className="telemetry-heading">Latest Scores</h4>
        {topScores.length === 0 ? (
          <span className="text-muted">No scores</span>
        ) : (
          <ul className="telemetry-run-list">
            {topScores.map((s) => (
              <li key={s.corps_id} className="telemetry-run-item">
                <span className="mono">#{s.rank} {s.corps_id}</span>
                <span className="show-score">{s.final_score.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
