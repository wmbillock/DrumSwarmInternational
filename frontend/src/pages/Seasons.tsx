import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Panel, Badge, DataTable } from "../ui";
import * as v1 from "../services/v1";
import { formatStatus, slugToTitle } from "../utils/formatters";

export function Seasons() {
  const navigate = useNavigate();
  const { seasonId } = useParams<{ seasonId?: string }>();
  const [seasons, setSeasons] = useState<v1.V1Season[]>([]);
  const [detail, setDetail] = useState<(v1.V1Season & { registered_corps?: string[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [corpsMap, setCorpsMap] = useState<Record<string, string>>({});
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    const ac = new AbortController();
    setError("");
    v1.listSeasons(ac.signal)
      .then(setSeasons)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [refreshToken]);

  useEffect(() => {
    const ac = new AbortController();
    v1.listCorps(ac.signal)
      .then((corps) => {
        const map: Record<string, string> = {};
        for (const c of corps) map[c.corps_id] = c.display_name;
        setCorpsMap(map);
      })
      .catch(() => {});
    return () => ac.abort();
  }, []);

  useEffect(() => {
    if (!seasonId) {
      setDetail(null);
      return;
    }
    const ac = new AbortController();
    setDetailLoading(true);
    v1.getSeason(seasonId, ac.signal)
      .then(setDetail)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setDetailLoading(false));
    return () => ac.abort();
  }, [seasonId]);

  if (loading) return <div className="page-loading">Loading seasons...</div>;
  if (error) {
    return (
      <div className="page-error">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
      </div>
    );
  }

  if (seasonId && detail) {
    return (
      <div className="page-content">
        <Panel
          title={`Season: ${slugToTitle(detail.season_id)}`}
          actions={
            <button className="primary" onClick={() => navigate("/seasons")}>
              Back to Seasons
            </button>
          }
        >
          <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
            <Badge variant={detail.status === "active" ? "success" : detail.status === "completed" ? "info" : "default"}>
              {formatStatus(detail.status)}
            </Badge>
            <span>{detail.registered_corps_count ?? detail.registered_corps?.length ?? 0} registered corps</span>
          </div>

          {detail.registered_corps && detail.registered_corps.length > 0 && (
            <Panel title="Registered Corps">
              <DataTable<{ corps_id: string } & Record<string, unknown>>
                columns={[
                  {
                    key: "corps_id",
                    label: "Corps",
                    render: (v) => (
                      <span className="mono" title={String(v)}>
                        {corpsMap[String(v)] || `Corps • ${String(v).slice(0, 8)}`}
                      </span>
                    ),
                  },
                ]}
                data={detail.registered_corps.map((c) => ({ corps_id: c }))}
                onRowClick={(row) => navigate(`/corps/${row.corps_id}`)}
                emptyMessage="No corps registered"
              />
            </Panel>
          )}

          {detail.metadata && Object.keys(detail.metadata).length > 0 && (
            <Panel title="Metadata">
              <pre style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap" }}>
                {JSON.stringify(detail.metadata, null, 2)}
              </pre>
            </Panel>
          )}
        </Panel>
      </div>
    );
  }

  if (seasonId && detailLoading) {
    return <div className="page-loading">Loading season details...</div>;
  }

  return (
    <div className="page-content">
      <Panel title="Seasons">
        <DataTable<v1.V1Season & Record<string, unknown>>
          columns={[
            {
              key: "season_id",
              label: "Season",
              render: (v) => <span className="mono" title={String(v)}>{slugToTitle(String(v))}</span>,
            },
            {
              key: "status",
              label: "Status",
              render: (v) => (
                <Badge variant={v === "active" ? "success" : v === "completed" ? "info" : "default"}>
                  {formatStatus(String(v))}
                </Badge>
              ),
            },
            {
              key: "registered_corps_count",
              label: "Corps",
              render: (v) => <span>{v != null ? String(v) : "—"}</span>,
            },
          ]}
          data={seasons as (v1.V1Season & Record<string, unknown>)[]}
          onRowClick={(row) => navigate(`/seasons/${row.season_id}`)}
          emptyMessage="No seasons found"
        />
      </Panel>
    </div>
  );
}
