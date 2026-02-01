import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Panel, Badge, DataTable, Tabs } from "../ui";
import type { TabItem } from "../ui";
import * as v1 from "../services/v1";

export function SeasonWorkshop() {
  const navigate = useNavigate();
  const { seasonId } = useParams<{ seasonId?: string }>();
  const [seasons, setSeasons] = useState<v1.V1Season[]>([]);
  const [detail, setDetail] = useState<(v1.V1Season & { registered_corps?: string[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("setup");
  const [corps, setCorps] = useState<v1.V1Corps[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newSeasonId, setNewSeasonId] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const ac = new AbortController();
    Promise.allSettled([
      v1.listSeasons(ac.signal),
      v1.listCorps(ac.signal),
    ]).then(([seasonsRes, corpsRes]) => {
      if (seasonsRes.status === "fulfilled") setSeasons(seasonsRes.value);
      if (corpsRes.status === "fulfilled") setCorps(corpsRes.value);
      setLoading(false);
    });
    return () => ac.abort();
  }, []);

  useEffect(() => {
    if (!seasonId) { setDetail(null); return; }
    const ac = new AbortController();
    setDetailLoading(true);
    v1.getSeason(seasonId, ac.signal)
      .then(setDetail)
      .catch(e => { if (e.name !== "AbortError") setError(e.message); })
      .finally(() => setDetailLoading(false));
    return () => ac.abort();
  }, [seasonId]);

  const handleCreateSeason = async () => {
    if (!newSeasonId.trim()) return;
    setCreating(true);
    try {
      const s = await v1.createSeason(newSeasonId.trim());
      setSeasons(prev => [...prev, s]);
      setNewSeasonId("");
      setShowCreate(false);
      navigate(`/seasons/${s.season_id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleRegisterCorps = async (corpsId: string) => {
    if (!seasonId) return;
    try {
      await v1.registerSeasonCorps(seasonId, corpsId);
      const updated = await v1.getSeason(seasonId);
      setDetail(updated);
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading) return <div className="page-loading">Loading seasons...</div>;
  if (error) return <div className="page-error"><div className="error-banner">{error}</div></div>;

  // Detail view
  if (seasonId && detail) {
    const tabs: TabItem[] = [
      { key: "setup", label: "Setup" },
      { key: "camps", label: "Winter Camps" },
      { key: "ready", label: "Ready Check" },
    ];

    const registeredCorps = detail.registered_corps || [];
    const unregisteredCorps = corps.filter(c => !registeredCorps.includes(c.corps_id));

    return (
      <div className="season-workshop">
        <div className="page-header">
          <button className="back-btn" onClick={() => navigate("/seasons")}>Back</button>
          <h1 className="page-title" style={{ marginBottom: 0 }}>
            {detail.season_id}
          </h1>
        </div>

        <Tabs items={tabs} active={activeTab} onChange={setActiveTab} />

        {activeTab === "setup" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Season Details">
              <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
                <Badge variant={(detail as any).status === "active" ? "success" : "default"}>
                  {(detail as any).status || "planning"}
                </Badge>
                <span>{registeredCorps.length} corps registered</span>
              </div>

              {detail.metadata && Object.keys(detail.metadata).length > 0 && (
                <pre style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap", marginBottom: 16 }}>
                  {JSON.stringify(detail.metadata, null, 2)}
                </pre>
              )}
            </Panel>

            <Panel title="Registered Corps" style={{ marginTop: 16 }}>
              {registeredCorps.length === 0 && <p className="empty">No corps registered yet.</p>}
              {registeredCorps.map(id => (
                <div key={id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between" }}>
                  <span className="mono">{id}</span>
                  <button className="small" onClick={() => navigate(`/corps/${id}`)}>View</button>
                </div>
              ))}
            </Panel>

            {unregisteredCorps.length > 0 && (
              <Panel title="Add Corps" style={{ marginTop: 16 }}>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {unregisteredCorps.map(c => (
                    <button key={c.corps_id} className="small" onClick={() => handleRegisterCorps(c.corps_id)}>
                      + {c.display_name}
                    </button>
                  ))}
                </div>
              </Panel>
            )}
          </div>
        )}

        {activeTab === "camps" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Winter Camps — Corps Readiness">
              {registeredCorps.length === 0 && <p className="empty">Register corps first.</p>}
              {registeredCorps.map(id => {
                const c = corps.find(x => x.corps_id === id);
                return (
                  <div key={id} style={{ padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 600 }}>{c?.display_name || id}</span>
                      <Badge variant={c?.state === "winter_camps" ? "warning" : c?.state === "on_tour" ? "success" : "default"}>
                        {c?.state || "unknown"}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </Panel>
          </div>
        )}

        {activeTab === "ready" && (
          <div style={{ marginTop: 16 }}>
            <Panel title="Ready Check">
              <p className="hint" style={{ marginBottom: 16 }}>
                All corps must be in RUN_THROUGH mode before starting the tour.
              </p>
              <div className="ready-check-list">
                {registeredCorps.map(id => {
                  const c = corps.find(x => x.corps_id === id);
                  const isReady = c?.state === "on_tour" || c?.state === "winter_camps";
                  return (
                    <div key={id} className={`ready-check-item ${isReady ? "ready" : "not-ready"}`}>
                      <span className={`ready-check-dot ${isReady ? "ready" : "not-ready"}`} />
                      <span style={{ flex: 1, fontWeight: 500 }}>{c?.display_name || id}</span>
                      <Badge variant={isReady ? "success" : "warning"}>
                        {isReady ? "Ready" : "Not Ready"}
                      </Badge>
                    </div>
                  );
                })}
              </div>
              {registeredCorps.length > 0 && (
                <button
                  className="primary"
                  style={{ marginTop: 16, fontFamily: "var(--font-display)", fontSize: 14, padding: "12px 24px" }}
                  disabled={registeredCorps.length === 0}
                >
                  Start Tour
                </button>
              )}
            </Panel>
          </div>
        )}
      </div>
    );
  }

  if (seasonId && detailLoading) {
    return <div className="page-loading">Loading season details...</div>;
  }

  // List view
  return (
    <div className="season-workshop">
      <h1 className="page-title">Season Workshop</h1>

      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{seasons.length}</span>
          <span className="summary-label">Seasons</span>
        </div>
      </div>

      <div style={{ marginBottom: 16, display: "flex", gap: 8 }}>
        {!showCreate ? (
          <button className="primary" onClick={() => setShowCreate(true)}>+ New Season</button>
        ) : (
          <form onSubmit={e => { e.preventDefault(); handleCreateSeason(); }} style={{ display: "flex", gap: 8 }}>
            <input
              className="library-search"
              style={{ width: 240 }}
              placeholder="Season ID (e.g. tour-s1)..."
              value={newSeasonId}
              onChange={e => setNewSeasonId(e.target.value)}
              autoFocus
            />
            <button type="submit" className="primary" disabled={creating || !newSeasonId.trim()}>Create</button>
            <button type="button" onClick={() => setShowCreate(false)}>Cancel</button>
          </form>
        )}
      </div>

      <Panel title="All Seasons">
        <DataTable<v1.V1Season & Record<string, unknown>>
          columns={[
            {
              key: "season_id",
              label: "Season",
              render: v => <span className="mono">{String(v)}</span>,
            },
            {
              key: "status",
              label: "Status",
              render: v => (
                <Badge variant={v === "active" ? "success" : v === "completed" ? "info" : "default"}>
                  {String(v || "planning")}
                </Badge>
              ),
            },
            {
              key: "registered_corps_count",
              label: "Corps",
              render: v => <span>{v != null ? String(v) : "—"}</span>,
            },
          ]}
          data={seasons as (v1.V1Season & Record<string, unknown>)[]}
          onRowClick={row => navigate(`/seasons/${row.season_id}`)}
          emptyMessage="No seasons found"
        />
      </Panel>
    </div>
  );
}
