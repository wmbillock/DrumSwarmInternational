import { useState, useEffect, useCallback } from "react";
import { Panel, Tabs } from "../ui";
import * as v1 from "../services/v1";

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
    <div className="dashboard">
      <h1 className="page-title">Staff Marketplace</h1>
      <Tabs active={tab} onChange={setTab} items={TABS} />

      {tab === "marketplace" && (
        <Panel title="Available Performers">
          {loading && <p className="empty">Loading...</p>}
          {error && <p className="empty" style={{ color: "#f44336" }}>{error}</p>}
          {!loading && !error && marketplace.length === 0 && (
            <p className="empty">No performers available.</p>
          )}
          {marketplace.length > 0 && (
            <table className="data-table" style={{ width: "100%" }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Trust Score</th>
                  <th>Sessions</th>
                  <th>Status</th>
                  <th>Specialties</th>
                </tr>
              </thead>
              <tbody>
                {marketplace.map((m) => (
                  <tr key={m.id}>
                    <td>{m.name}</td>
                    <td>{m.role_type}</td>
                    <td>
                      <span
                        style={{
                          color: trustColor(m.trust_score),
                          fontWeight: 600,
                        }}
                      >
                        {m.trust_score}
                      </span>
                    </td>
                    <td>
                      {m.successful_sessions}/{m.total_sessions}
                    </td>
                    <td>
                      <span className={`badge ${m.status}`}>{m.status}</span>
                    </td>
                    <td>{m.specialties || "--"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
            <table className="data-table" style={{ width: "100%" }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Trust Score</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {corpsStaff.map((s: any) => (
                  <tr key={s.id || s.performer_id}>
                    <td>{s.name || s.performer_id}</td>
                    <td>{s.role_type || s.role || "--"}</td>
                    <td>
                      <span
                        style={{
                          color: trustColor(s.trust_score ?? 0),
                          fontWeight: 600,
                        }}
                      >
                        {s.trust_score ?? "--"}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${s.status || ""}`}>
                        {s.status || "--"}
                      </span>
                    </td>
                    <td>
                      <button
                        className="small danger"
                        onClick={() => handleRelease(s.id || s.performer_id)}
                      >
                        Release
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      )}
    </div>
  );
}
