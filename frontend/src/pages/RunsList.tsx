import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import type { V1Run } from "../services/v1";
import { Badge, DataTable } from "../ui";
import { badgeForRunStatus, formatStatus, formatTimestamp, slugToTitle } from "../utils/formatters";

export function RunsList() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<V1Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = () => {
    setLoading(true);
    setError(null);
    v1.listRuns()
      .then(setRuns)
      .catch(e => setError(e instanceof Error ? e.message : "Failed to load runs"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRuns();
  }, []);

  if (loading) return <div className="page-loading">Loading Runs & Rehearsals...</div>;

  return (
    <div className="runs-page">
      <h1 className="page-title">Runs & Rehearsals</h1>

      {error && (
        <div className="error-banner">
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={loadRuns}>Retry</button>
        </div>
      )}

      {runs.length === 0 && !error && (
        <p className="empty">No runs found. Execute a show run to see results here.</p>
      )}

      {runs.length > 0 && (
        <DataTable<V1Run & Record<string, unknown>>
          columns={[
            { key: "run_id", label: "Run ID", render: (v) => <span className="mono" title={String(v)}>{String(v).slice(0, 8)}</span> },
            { key: "show_slug", label: "Show", render: (v) => slugToTitle(String(v || "")) },
            { key: "corps_id", label: "Corps", render: (v) => <span title={String(v)}>Corps • {String(v).slice(0, 8)}</span> },
            { key: "season_id", label: "Season", render: (v) => <span title={String(v)}>{slugToTitle(String(v || ""))}</span> },
            { key: "status", label: "Status", render: (v) => <Badge variant={badgeForRunStatus(String(v))}>{formatStatus(String(v))}</Badge> },
            { key: "started_at", label: "Started", render: (v) => {
              const ts = formatTimestamp(String(v));
              return <span title={ts.title}>{ts.label || "—"}</span>;
            } },
            { key: "completed_at", label: "Duration", render: (_v, row) => {
              let duration = "—";
              if (row.started_at && row.completed_at) {
                const ms = new Date(row.completed_at).getTime() - new Date(row.started_at).getTime();
                if (ms < 60000) duration = `${Math.round(ms / 1000)}s`;
                else duration = `${Math.round(ms / 60000)}m`;
              }
              return duration;
            } },
          ]}
          data={runs as (V1Run & Record<string, unknown>)[]}
          onRowClick={(row) => navigate(`/runs/${encodeURIComponent(row.run_id)}`)}
          emptyMessage="No runs found. Execute a show run to see results here."
        />
      )}
    </div>
  );
}
