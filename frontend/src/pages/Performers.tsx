import { useState, useEffect } from "react";
import * as v1 from "../services/v1";
import { Badge, DataTable } from "../ui";
import { AwardsPanel } from "../components/AwardsPanel";
import { formatRole, formatStatus, formatTimestamp } from "../utils/formatters";

export function Performers() {
  const [performers, setPerformers] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [ledger, setLedger] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [awards, setAwards] = useState<v1.V1Award[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadPerformers = () => {
    setError(null);
    v1.listPerformers()
      .then(setPerformers)
      .catch((e) => {
        setPerformers([]);
        setError(e instanceof Error ? e.message : "Failed to load performers");
      });
  };

  useEffect(() => {
    loadPerformers();
  }, []);

  const handleSelect = async (id: string) => {
    try {
      const [detail, led, st, awardList] = await Promise.all([
        v1.getPerformer(id),
        v1.getPerformerLedger(id).catch(() => []),
        v1.getPerformerStats(id).catch(() => null),
        v1.listAwards({ recipient_id: id }).catch(() => []),
      ]);
      setSelected(detail);
      setLedger(led);
      setStats(st);
      setAwards(awardList);
    } catch { setSelected(null); }
  };

  const handleRetire = async (id: string) => {
    await v1.retirePerformer(id);
    v1.listPerformers().then(setPerformers);
    setSelected(null);
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h2 className="page-title">Performers</h2>
      </div>
      <DataTable<any>
        columns={[
          { key: "id", label: "Name", render: (v, row) => (
            <span className="cell-primary" title={String(v)}>
              {row.name || `Performer • ${String(v).slice(0, 8)}`}
            </span>
          ) },
          { key: "role_type", label: "Role", render: (v) => formatRole(String(v || "")) },
          { key: "trust_score", label: "Trust", render: (v) => <span className="trust-score">{v ?? "-"}</span> },
          { key: "status", label: "Status", render: (v) => <Badge>{formatStatus(String(v || "active"))}</Badge> },
          { key: "total_sessions", label: "Sessions", render: (v) => String(v ?? 0) },
        ]}
        data={performers}
        onRowClick={(row) => handleSelect(row.id)}
        emptyMessage="No performers yet."
      />
      {error && (
        <div className="error-banner" style={{ marginTop: 8 }}>
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={loadPerformers}>Retry</button>
        </div>
      )}
      {selected && (
        <div className="detail-panel">
          <h3 title={selected.id}>{selected.name || `Performer • ${selected.id.slice(0, 8)}`}</h3>
          <p className="dim" style={{ marginBottom: 8 }}>{formatRole(selected.role_type || "")}</p>
          <button className="small danger" onClick={() => handleRetire(selected.id)}>Retire</button>
          {stats && (
            <div className="stats-grid">
              <div><strong>Total Sessions</strong><span>{stats.total_sessions ?? 0}</span></div>
              <div><strong>Success Rate</strong><span>{stats.success_rate != null ? `${(stats.success_rate * 100).toFixed(0)}%` : "-"}</span></div>
              <div><strong>Avg Score</strong><span>{stats.avg_score != null ? stats.avg_score.toFixed(1) : "-"}</span></div>
            </div>
          )}
          <AwardsPanel
            title={selected.role_type === "performer" ? "Performer Achievements" : "Staff Achievements"}
            awards={awards}
            emptyText="No achievements yet."
          />
          {ledger.length > 0 && (
            <>
              <h4>Capability Ledger</h4>
              <DataTable<any>
                columns={[
                  { key: "capability", label: "Capability", render: (_v, row) => row.capability || row.tool_name || "-" },
                  { key: "level", label: "Level", render: (_v, row) => String(row.level ?? row.score ?? "-") },
                  { key: "updated_at", label: "Updated", render: (v) => (
                    <span title={v ? formatTimestamp(String(v)).title : ""}>
                      {v ? formatTimestamp(String(v)).label : "-"}
                    </span>
                  ) },
                ]}
                data={ledger}
                emptyMessage="No capability ledger entries."
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}
