import { useState, useEffect, useCallback } from "react";
import { Panel, Tabs, Badge, DataTable } from "../ui";
import { useSearchParams } from "react-router-dom";
import * as v1 from "../services/v1";
import { formatRole, formatStatus } from "../utils/formatters";

const TABS = [
  { key: "marketplace", label: "Marketplace" },
  { key: "corps-staff", label: "Corps Staff" },
];

function trustColor(score: number): string {
  if (score > 70) return "#4caf50";
  if (score > 40) return "#ff9800";
  return "#f44336";
}

export function StaffMarketplace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState("marketplace");
  const [marketplace, setMarketplace] = useState<v1.StaffMember[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Corps Staff tab state
  const [corpsList, setCorpsList] = useState<v1.V1Corps[]>([]);
  const [selectedCorps, setSelectedCorps] = useState("");
  const [corpsStaff, setCorpsStaff] = useState<any[]>([]);
  const [staffLoading, setStaffLoading] = useState(false);

  const fetchMarketplace = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await v1.listMarketplace();
      setMarketplace(data);
    } catch (e: any) {
      setError(e.message || "Failed to load marketplace");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCorpsList = useCallback(async () => {
    try {
      const data = await v1.listCorps();
      setCorpsList(data);
    } catch {}
  }, []);

  const fetchCorpsStaff = useCallback(async (corpsId: string) => {
    if (!corpsId) return;
    setStaffLoading(true);
    try {
      const data = await v1.getCorpsStaff(corpsId);
      setCorpsStaff(data);
    } catch {
      setCorpsStaff([]);
    } finally {
      setStaffLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMarketplace();
    fetchCorpsList();
  }, [fetchMarketplace, fetchCorpsList]);

  useEffect(() => {
    const nextTab = searchParams.get("tab");
    if (nextTab && nextTab !== tab) {
      setTab(nextTab);
    }
  }, [searchParams, tab]);

  useEffect(() => {
    if (selectedCorps) fetchCorpsStaff(selectedCorps);
  }, [selectedCorps, fetchCorpsStaff]);

  const handleRelease = async (performerId: string) => {
    if (!selectedCorps) return;
    if (!confirm("Release this staff member?")) return;
    try {
      await v1.releaseStaff(selectedCorps, performerId);
      fetchCorpsStaff(selectedCorps);
      fetchMarketplace();
    } catch (e: any) {
      alert(e.message || "Failed to release staff");
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Staff Marketplace</h1>
      </div>
      <Tabs
        active={tab}
        onChange={(next) => {
          setTab(next);
          const params = new URLSearchParams(searchParams);
          params.set("tab", next);
          setSearchParams(params, { replace: true });
        }}
        items={TABS}
      />

      {tab === "marketplace" && (
        <Panel title="Available Performers">
          {loading && <p className="empty">Loading...</p>}
          {error && (
            <div className="error-banner">
              {error}
              <button className="small" style={{ marginLeft: 8 }} onClick={fetchMarketplace}>Retry</button>
            </div>
          )}
          {!loading && !error && marketplace.length === 0 && (
            <p className="empty">No performers available.</p>
          )}
          {marketplace.length > 0 && (
            <DataTable<v1.StaffMember & Record<string, unknown>>
              columns={[
                { key: "id", label: "Name", render: (v, row) => <span title={String(v)}>{row.name || `Performer • ${String(v).slice(0, 8)}`}</span> },
                { key: "role_type", label: "Role", render: (v) => formatRole(String(v || "")) },
                { key: "trust_score", label: "Trust Score", render: (v) => (
                  <span style={{ color: trustColor(Number(v ?? 0)), fontWeight: 600 }}>{v ?? "--"}</span>
                ) },
                { key: "successful_sessions", label: "Sessions", render: (_v, row) => `${row.successful_sessions}/${row.total_sessions}` },
                { key: "status", label: "Status", render: (v) => <Badge>{formatStatus(String(v || ""))}</Badge> },
                { key: "specialties", label: "Specialties", render: (v) => String(v || "--") },
              ]}
              data={marketplace as (v1.StaffMember & Record<string, unknown>)[]}
              emptyMessage="No performers available."
            />
          )}
        </Panel>
      )}

      {tab === "corps-staff" && (
        <Panel title="Corps Staff">
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="corps-select" style={{ marginRight: "0.5rem" }}>
              Select Corps:
            </label>
            <select
              id="corps-select"
              value={selectedCorps}
              onChange={(e) => setSelectedCorps(e.target.value)}
            >
              <option value="">-- Choose a corps --</option>
              {corpsList.map((c) => (
                <option key={c.corps_id} value={c.corps_id}>
                  {c.display_name}
                </option>
              ))}
            </select>
          </div>

          {!selectedCorps && <p className="empty">Select a corps to view staff.</p>}
          {selectedCorps && staffLoading && <p className="empty">Loading...</p>}
          {selectedCorps && !staffLoading && corpsStaff.length === 0 && (
            <p className="empty">No staff assigned to this corps.</p>
          )}
          {selectedCorps && corpsStaff.length > 0 && (
            <DataTable<any>
              columns={[
                { key: "performer_id", label: "Name", render: (_v, row) => (
                  <span title={row.performer_id || row.id}>
                    {row.name || `Performer • ${(row.performer_id || row.id || "").slice(0, 8)}`}
                  </span>
                ) },
                { key: "role_type", label: "Role", render: (_v, row) => formatRole(row.role_type || row.role || "") },
                { key: "trust_score", label: "Trust Score", render: (v) => (
                  <span style={{ color: trustColor(Number(v ?? 0)), fontWeight: 600 }}>{v ?? "--"}</span>
                ) },
                { key: "status", label: "Status", render: (v) => <Badge>{formatStatus(String(v || "active"))}</Badge> },
                { key: "id", label: "Actions", render: (_v, row) => (
                  <button className="small danger" onClick={() => handleRelease(row.id || row.performer_id)}>
                    Release
                  </button>
                ) },
              ]}
              data={corpsStaff}
              emptyMessage="No staff assigned to this corps."
            />
          )}
        </Panel>
      )}
    </div>
  );
}
