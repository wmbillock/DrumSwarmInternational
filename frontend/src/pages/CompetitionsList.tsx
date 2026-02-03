import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Panel, DataTable, Badge } from "../ui";
import { CompetitionForm } from "../components/CompetitionForm";
import * as v1 from "../services/v1";
import { formatStatus, slugToTitle } from "../utils/formatters";

export function CompetitionsList() {
  const navigate = useNavigate();
  const [competitions, setCompetitions] = useState<v1.V1Competition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    const ac = new AbortController();
    setError("");
    v1.listCompetitions(ac.signal)
      .then(setCompetitions)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [refreshToken]);

  if (loading) return <div className="page-loading">Loading competitions...</div>;
  if (error) {
    return (
      <div className="page-error">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
      </div>
    );
  }

  return (
    <div className="page-content">
      <Panel
        title="Competitions"
        actions={
          <button className="primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Create Competition"}
          </button>
        }
      >
        {showForm && (
          <CompetitionForm
            onCreated={(comp) => {
              setCompetitions((prev) => [...prev, comp]);
              setShowForm(false);
            }}
            onCancel={() => setShowForm(false)}
          />
        )}
        <DataTable<v1.V1Competition & Record<string, unknown>>
          columns={[
            { key: "competition_id", label: "ID", render: (v) => <span className="mono" title={String(v)}>{slugToTitle(String(v))}</span> },
            { key: "season_id", label: "Season", render: (v) => <span title={String(v)}>{slugToTitle(String(v))}</span> },
            { key: "show_slug", label: "Show", render: (v) => <span title={String(v)}>{slugToTitle(String(v))}</span> },
            {
              key: "status",
              label: "Status",
              render: (v) => (
                <Badge variant={v === "ready" ? "success" : v === "completed" ? "info" : "default"}>
                  {formatStatus(String(v))}
                </Badge>
              ),
            },
            {
              key: "corps_ids",
              label: "Corps",
              render: (v) => <span>{Array.isArray(v) ? (v as string[]).length : 0} corps</span>,
            },
          ]}
          data={competitions as (v1.V1Competition & Record<string, unknown>)[]}
          onRowClick={(row) => navigate(`/competitions/${row.competition_id}`)}
          emptyMessage="No competitions found"
        />
      </Panel>
    </div>
  );
}
