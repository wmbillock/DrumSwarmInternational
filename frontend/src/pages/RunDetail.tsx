import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import type { V1RunDetail } from "../services/v1";
import { Badge } from "../ui";
import { badgeForRunStatus, formatStatus, formatTimestamp, slugToTitle } from "../utils/formatters";

export function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<V1RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRun = () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    v1.getRun(runId)
      .then(setRun)
      .catch(e => setError(e instanceof Error ? e.message : "Failed to load run"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRun();
  }, [runId]);

  if (loading) return <div className="page-loading">Loading run details...</div>;
  if (error) {
    return (
      <div className="page-error">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={loadRun}>Retry</button>
        <button onClick={() => navigate("/runs")}>Back to Runs</button>
      </div>
    );
  }
  if (!run) {
    return (
      <div className="page-error">
        <div className="error-banner">Run not found.</div>
        <button className="secondary" onClick={loadRun}>Retry</button>
      </div>
    );
  }

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
        <h1 className="page-title">Run: {run.run_id.slice(0, 8)}</h1>
      </div>

      <div className="run-manifest-grid">
        <div className="manifest-card">
          <h3>Manifest</h3>
          <dl className="manifest-dl">
            <dt>Run ID</dt><dd className="mono" title={run.run_id}>{run.run_id.slice(0, 8)}</dd>
            <dt>Show</dt><dd>{slugToTitle(run.show_slug)}</dd>
            <dt>Corps</dt>
            <dd>
              <span className="clickable link" title={run.corps_id} onClick={() => navigate(`/corps/${run.corps_id}`)}>
                Corps • {run.corps_id.slice(0, 8)}
              </span>
            </dd>
            <dt>Season</dt><dd>{slugToTitle(run.season_id)}</dd>
            <dt>Status</dt><dd><Badge variant={badgeForRunStatus(run.status)}>{formatStatus(run.status)}</Badge></dd>
            <dt>Started</dt><dd title={formatTimestamp(run.started_at).title}>{formatTimestamp(run.started_at).label || "—"}</dd>
            <dt>Completed</dt><dd title={formatTimestamp(run.completed_at).title}>{formatTimestamp(run.completed_at).label || "—"}</dd>
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
