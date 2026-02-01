import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Tabs, Panel, DataTable, Badge } from "../ui";
import * as v1 from "../services/v1";

const TAB_ITEMS = [
  { key: "overview", label: "Overview" },
  { key: "runs", label: "Runs" },
  { key: "shows", label: "Shows" },
  { key: "history", label: "History" },
];

export function CorpsDetailV2() {
  const { corpsId, tab } = useParams<{ corpsId: string; tab?: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(tab || "overview");
  const [corps, setCorps] = useState<v1.V1CorpsDetail | null>(null);
  const [runs, setRuns] = useState<v1.V1Run[]>([]);
  const [history, setHistory] = useState<v1.V1HistoryIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!corpsId) return;
    const ac = new AbortController();

    v1.getCorps(corpsId, ac.signal)
      .then(setCorps)
      .catch((e) => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => setLoading(false));

    v1.listRuns(corpsId, ac.signal)
      .then(setRuns)
      .catch(() => {});

    v1.getCorpsHistory(corpsId, ac.signal)
      .then(setHistory)
      .catch(() => {});

    return () => ac.abort();
  }, [corpsId]);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    navigate(`/corps/${corpsId}/${key}`, { replace: true });
  };

  if (loading) return <div className="page-loading">Loading corps...</div>;
  if (error) return <div className="page-error"><div className="error-banner">{error}</div></div>;
  if (!corps) return <div className="page-error">Corps not found</div>;

  return (
    <div className="page-content">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate("/corps")}>Back</button>
        <h2>{corps.display_name}</h2>
        <Badge variant={corps.state === "on_tour" ? "success" : "default"}>{corps.state}</Badge>
      </div>

      <Tabs active={activeTab} onChange={handleTabChange} items={TAB_ITEMS} />

      <div style={{ marginTop: 16 }}>
        {activeTab === "overview" && (
          <OverviewTab corps={corps} />
        )}
        {activeTab === "runs" && (
          <RunsTab runs={runs} navigate={navigate} />
        )}
        {activeTab === "shows" && (
          <ShowsTab history={history} />
        )}
        {activeTab === "history" && (
          <HistoryTab corps={corps} history={history} corpsId={corpsId!} />
        )}
      </div>
    </div>
  );
}

function OverviewTab({ corps }: { corps: v1.V1CorpsDetail }) {
  return (
    <div>
      <Panel title="Corps Info">
        <table className="styled-table">
          <tbody>
            <tr><td className="cell-primary">ID</td><td className="mono">{corps.corps_id}</td></tr>
            <tr><td className="cell-primary">State</td><td>{corps.state}</td></tr>
            <tr><td className="cell-primary">Roster Size</td><td>{corps.roster_size}</td></tr>
            <tr><td className="cell-primary">History Entries</td><td>{corps.history_count}</td></tr>
          </tbody>
        </table>
      </Panel>
      {corps.philosophy && (
        <Panel title="Philosophy" className="mt-16">
          <p style={{ fontSize: 13, color: "var(--text-secondary)", fontStyle: "italic" }}>
            {corps.philosophy}
          </p>
        </Panel>
      )}
    </div>
  );
}

function RunsTab({ runs, navigate }: { runs: v1.V1Run[]; navigate: ReturnType<typeof useNavigate> }) {
  return (
    <Panel title="Run History">
      <DataTable<v1.V1Run & Record<string, unknown>>
        columns={[
          { key: "run_id", label: "Run", render: (v) => <span className="mono">{String(v).slice(0, 30)}</span> },
          { key: "show_slug", label: "Show" },
          {
            key: "status",
            label: "Status",
            render: (v) => (
              <Badge variant={v === "completed" ? "success" : v === "failed" ? "danger" : "warning"}>
                {String(v)}
              </Badge>
            ),
          },
          { key: "started_at", label: "Started", render: (v) => v ? new Date(String(v)).toLocaleString() : "" },
        ]}
        data={runs as (v1.V1Run & Record<string, unknown>)[]}
        onRowClick={(row) => navigate(`/runs/${row.run_id}`)}
        emptyMessage="No runs found for this corps"
      />
    </Panel>
  );
}

function ShowsTab({ history }: { history: v1.V1HistoryIndex | null }) {
  if (!history || history.entries.length === 0) {
    return <p className="empty">No show participation recorded</p>;
  }

  const showEntries = history.entries.filter((e) => e.show_slug);
  return (
    <Panel title="Show Participation">
      <DataTable<v1.V1HistoryEntry & Record<string, unknown>>
        columns={[
          { key: "show_slug", label: "Show", render: (v) => String(v || "N/A") },
          { key: "season_id", label: "Season" },
          { key: "placement", label: "Placement", render: (v) => <strong>#{String(v)}</strong> },
          { key: "final_score", label: "Score", render: (v) => Number(v).toFixed(2) },
        ]}
        data={showEntries as (v1.V1HistoryEntry & Record<string, unknown>)[]}
        emptyMessage="No shows found"
      />
    </Panel>
  );
}

function HistoryTab({ corps, history, corpsId }: { corps: v1.V1CorpsDetail; history: v1.V1HistoryIndex | null; corpsId: string }) {
  return (
    <div>
      {corps.history.length > 0 && (
        <Panel title="Past Placements">
          <DataTable<v1.V1Placement & Record<string, unknown>>
            columns={[
              { key: "season_id", label: "Season" },
              { key: "placement", label: "Place", render: (v) => <strong>#{String(v)}</strong> },
              { key: "final_score", label: "Score", render: (v) => Number(v).toFixed(2) },
              { key: "notes", label: "Notes" },
            ]}
            data={corps.history as (v1.V1Placement & Record<string, unknown>)[]}
            emptyMessage="No placement history"
          />
        </Panel>
      )}

      {history && history.entries.length > 0 && (
        <Panel title="Seance Sessions" className="mt-16">
          <p className="hint">Start a seance session to query past show data with the Executive Director.</p>
          <ul style={{ listStyle: "none", padding: 0, marginTop: 8 }}>
            {history.entries.map((e) => (
              <li key={e.entry_id} style={{ marginBottom: 8 }}>
                <a href={`/seance`} className="link">
                  {e.season_id} - {e.show_slug || "Unknown Show"} (#{e.placement})
                </a>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {corps.history.length === 0 && (!history || history.entries.length === 0) && (
        <p className="empty">No history available for {corpsId}</p>
      )}
    </div>
  );
}
