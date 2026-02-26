import { useState, useEffect } from "react";
import * as v1 from "../services/v1";
import { Badge, DataTable, Tabs } from "../ui";
import { AwardsPanel } from "../components/AwardsPanel";
import { formatRole, formatStatus, formatTimestamp } from "../utils/formatters";

type TabId = "performers" | "staff" | "all";

function categoryLabel(cat: string): string {
  switch (cat) {
    case "instructional_staff": return "Instructional Staff";
    case "administrative_staff": return "Administrative Staff";
    case "performer": return "Performer";
    default: return cat;
  }
}

export function Performers() {
  const [tab, setTab] = useState<TabId>("performers");
  const [performers, setPerformers] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [ledger, setLedger] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [awards, setAwards] = useState<v1.V1Award[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadPerformers = (signal?: AbortSignal) => {
    setError(null);
    const opts =
      tab === "staff" ? { staff_only: true }
      : tab === "performers" ? { performers_only: true }
      : undefined;
    v1.listPerformers(opts, signal)
      .then(setPerformers)
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setPerformers([]);
        setError(e instanceof Error ? e.message : "Failed to load");
      });
  };

  useEffect(() => {
    const ac = new AbortController();
    loadPerformers(ac.signal);
    setSelected(null);
    return () => ac.abort();
  }, [tab]);

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
    loadPerformers();
    setSelected(null);
  };

  const handleRelease = async (id: string) => {
    await v1.releaseStaffMember(id);
    loadPerformers();
    setSelected(null);
  };

  const columns = [
    { key: "id", label: "Name", render: (v: any, row: any) => (
      <span className="cell-primary" title={String(v)}>
        {row.name || `${row.is_verified ? "Staff" : "Performer"} \u2022 ${String(v).slice(0, 8)}`}
      </span>
    ) },
    { key: "role_type", label: "Role", render: (v: any) => formatRole(String(v || "")) },
    ...(tab === "all" ? [{
      key: "agent_category", label: "Category", render: (v: any) => (
        <Badge>{categoryLabel(String(v || "performer"))}</Badge>
      ),
    }] : []),
    { key: "trust_score", label: "Trust", render: (v: any) => <span className="trust-score">{v ?? "-"}</span> },
    { key: "is_verified", label: "Verified", render: (v: any) => v ? "Yes" : "No" },
    { key: "status", label: "Status", render: (v: any) => <Badge>{formatStatus(String(v || "active"))}</Badge> },
    { key: "total_sessions", label: "Sessions", render: (v: any) => String(v ?? 0) },
  ];

  return (
    <div className="page-content">
      <div className="page-header">
        <h2 className="page-title">Talent</h2>
      </div>
      <Tabs
        tabs={[
          { id: "performers", label: "Performers" },
          { id: "staff", label: "Staff" },
          { id: "all", label: "All" },
        ]}
        active={tab}
        onChange={(id) => setTab(id as TabId)}
      />
      <DataTable<any>
        columns={columns}
        data={performers}
        onRowClick={(row) => handleSelect(row.id)}
        emptyMessage={tab === "staff" ? "No verified staff yet." : "No performers yet."}
      />
      {error && (
        <div className="error-banner" style={{ marginTop: 8 }}>
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={() => loadPerformers()}>Retry</button>
        </div>
      )}
      {selected && (
        <div className="detail-panel">
          <h3 title={selected.id}>{selected.name || `${selected.is_verified ? "Staff" : "Performer"} \u2022 ${selected.id.slice(0, 8)}`}</h3>
          <p className="dim" style={{ marginBottom: 4 }}>{formatRole(selected.role_type || "")}</p>
          <p className="dim" style={{ marginBottom: 8 }}>
            {categoryLabel(selected.agent_category || "performer")}
            {selected.is_verified && selected.verified_at && (
              <> &mdash; verified {formatTimestamp(selected.verified_at).label}</>
            )}
          </p>
          <div style={{ display: "flex", gap: 8 }}>
            {!selected.is_verified && (
              <button className="small danger" onClick={() => handleRetire(selected.id)}>Retire</button>
            )}
            {selected.is_verified && (
              <button className="small" onClick={() => handleRelease(selected.id)}>Release from Staff</button>
            )}
          </div>
          {stats && (
            <div className="stats-grid">
              <div><strong>Total Sessions</strong><span>{stats.total_sessions ?? 0}</span></div>
              <div><strong>Success Rate</strong><span>{stats.success_rate != null ? `${(stats.success_rate * 100).toFixed(0)}%` : "-"}</span></div>
              <div><strong>Avg Score</strong><span>{stats.avg_score != null ? stats.avg_score.toFixed(1) : "-"}</span></div>
            </div>
          )}
          <AwardsPanel
            title={selected.is_verified ? "Staff Achievements" : "Performer Achievements"}
            awards={awards}
            emptyText="No achievements yet."
          />
          {ledger.length > 0 && (
            <>
              <h4>Trust Ledger</h4>
              <DataTable<any>
                columns={[
                  { key: "entry_type", label: "Event", render: (v: any) => formatRole(String(v || "-")) },
                  { key: "role_type", label: "Role", render: (v: any) => formatRole(String(v || "-")) },
                  { key: "score", label: "Score", render: (v: any) => v != null ? String(v) : "-" },
                  { key: "created_at", label: "When", render: (v: any) => (
                    <span title={v ? formatTimestamp(String(v)).title : ""}>
                      {v ? formatTimestamp(String(v)).label : "-"}
                    </span>
                  ) },
                ]}
                data={ledger}
                emptyMessage="No ledger entries."
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}
