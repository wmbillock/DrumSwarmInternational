import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Panel, DataTable, Badge } from "../ui";
import * as v1 from "../services/v1";

export function CompetitionsList() {
  const navigate = useNavigate();
  const [competitions, setCompetitions] = useState<v1.V1Competition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const ac = new AbortController();
    v1.listCompetitions(ac.signal)
      .then(setCompetitions)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, []);

  if (loading) return <div className="page-loading">Loading competitions...</div>;
  if (error) return <div className="page-error"><div className="error-banner">{error}</div></div>;

  return (
    <div className="page-content">
      <Panel title="Competitions">
        <DataTable<v1.V1Competition & Record<string, unknown>>
          columns={[
            { key: "competition_id", label: "ID", render: (v) => <span className="mono">{String(v)}</span> },
            { key: "season_id", label: "Season" },
            { key: "show_slug", label: "Show" },
            {
              key: "status",
              label: "Status",
              render: (v) => (
                <Badge variant={v === "ready" ? "success" : v === "completed" ? "info" : "default"}>
                  {String(v)}
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
