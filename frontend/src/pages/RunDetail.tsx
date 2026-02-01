import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type { RunDetail as RunDetailType } from "../types";
import * as api from "../services/api";

function formatTimestamp(ts?: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<RunDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    api.getRunDetail(runId)
      .then(setRun)
      .catch(e => setError(e instanceof Error ? e.message : "Failed to load run"))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) return <div className="page-loading">Loading run details...</div>;
  if (error) return <div className="page-error"><div className="error-banner">{error}</div><button onClick={() => navigate("/runs")}>Back to Runs</button></div>;
  if (!run) return <div className="page-error">Run not found.</div>;

  let duration = "—";
  if (run.started_at && run.completed_at) {
    const ms = new Date(run.completed_at).getTime() - new Date(run.started_at).getTime();
    if (ms < 60000) duration = `${Math.round(ms / 1000)}s`;
    else duration = `${Math.round(ms / 60000)}m`;
  }

  return (
    <div className="run-detail-page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate("/runs")}>Back to Runs</button>
        <h1 className="page-title">Run: {run.run_id}</h1>
      </div>

      <div className="run-manifest-grid">
        <div className="manifest-card">
          <h3>Manifest</h3>
          <dl className="manifest-dl">
            <dt>Run ID</dt><dd className="mono">{run.run_id}</dd>
            <dt>Show</dt><dd>{run.show_slug}</dd>
            <dt>Corps</dt>
            <dd>
              <span className="clickable link" onClick={() => navigate(`/corps/${run.corps_id}`)}>{run.corps_id}</span>
            </dd>
            <dt>Season</dt><dd>{run.season_id}</dd>
            <dt>Status</dt><dd><span className={`badge ${run.status}`}>{run.status}</span></dd>
            <dt>Started</dt><dd>{formatTimestamp(run.started_at)}</dd>
            <dt>Completed</dt><dd>{formatTimestamp(run.completed_at)}</dd>
            <dt>Duration</dt><dd>{duration}</dd>
          </dl>
        </div>

        <div className="manifest-card">
          <h3>Configuration</h3>
          <dl className="manifest-dl">
            <dt>Max Iterations</dt><dd>{run.config?.max_iterations ?? "—"}</dd>
            <dt>Timeout</dt><dd>{run.config?.timeout ? `${run.config.timeout}s` : "—"}</dd>
          </dl>
          {run.inputs && Object.keys(run.inputs).length > 0 && (
            <>
              <h3>Inputs</h3>
              <dl className="manifest-dl">
                {Object.entries(run.inputs).map(([k, v]) => (
                  <><dt key={`dt-${k}`}>{k}</dt><dd key={`dd-${k}`} className="mono">{v}</dd></>
                ))}
              </dl>
            </>
          )}
        </div>
      </div>

      {run.output && (
        <section className="cc-section">
          <h2>Output</h2>
          <pre className="run-output">{run.output}</pre>
        </section>
      )}
    </div>
  );
}
