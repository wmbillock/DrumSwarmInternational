import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge, DataTable } from "../ui";
import { badgeForCorpsStatus, formatNumber, formatStatus, formatTimestamp, slugToTitle } from "../utils/formatters";

export function CorpsHistory() {
  const { corpsId } = useParams<{ corpsId: string }>();
  const navigate = useNavigate();
  const [corpsList, setCorpsList] = useState<v1.V1Corps[]>([]);
  const [index, setIndex] = useState<v1.V1HistoryIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    if (!corpsId) {
      v1.listCorps(ac.signal)
        .then(setCorpsList)
        .catch(e => { if (e.name !== "AbortError") setError(e.message); })
        .finally(() => setLoading(false));
    } else {
      const historyPromise = v1.getCorpsHistory(corpsId, ac.signal)
        .then(setIndex)
        .catch(e => { if (e.name !== "AbortError") setError(e.message); });
      const corpsPromise = v1.listCorps(ac.signal)
        .then(setCorpsList)
        .catch(e => { if (e.name !== "AbortError") console.warn("Failed to load corps list", e); });
      Promise.allSettled([historyPromise, corpsPromise]).finally(() => setLoading(false));
    }
    return () => ac.abort();
  }, [corpsId, refreshToken]);

  const handleStartSeance = async (entry: v1.V1HistoryEntry) => {
    if (!corpsId) return;
    setStarting(entry.entry_id);
    try {
      const session = await v1.createSeance(corpsId, entry.entry_id);
      navigate(`/seance-session/${session.seance_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start seance");
    } finally {
      setStarting(null);
    }
  };

  if (loading) return <div className="page-loading">Loading...</div>;
  if (error) {
    return (
      <div className="page-content dashboard">
        <div className="error-banner">{error}</div>
        <button className="secondary" onClick={() => setRefreshToken(t => t + 1)}>Retry</button>
      </div>
    );
  }

  // Corps picker
  if (!corpsId) {
    return (
      <div className="page-content dashboard">
        <div className="page-header">
          <h2 className="page-title">Corps History</h2>
        </div>
        <p style={{ marginBottom: 16, color: "var(--text-secondary)" }}>
          Select a corps to view competition history.
        </p>
        <div className="corps-card-grid">
          {corpsList.map(c => (
            <div
              key={c.corps_id}
              className="corps-list-card clickable"
              onClick={() => navigate(`/history/${c.corps_id}`)}
            >
              <div className="corps-list-header">
                <span className="corps-list-name">{c.display_name}</span>
                <Badge variant={badgeForCorpsStatus(c.state)}>{formatStatus(c.state)}</Badge>
              </div>
            </div>
          ))}
          {corpsList.length === 0 && <p className="empty">No corps found.</p>}
        </div>
      </div>
    );
  }

  // History entries
  const entries = index?.entries || [];
  const corpsName = corpsList.find(c => c.corps_id === corpsId)?.display_name;
  const generated = index?.generated_at ? formatTimestamp(index.generated_at) : null;

  return (
    <div className="page-content dashboard">
      <div className="page-header">
        <button className="back-btn small" onClick={() => navigate("/history")}>Back</button>
        <div>
          <h2 className="page-title" style={{ margin: 0 }}>
            History: {corpsName || `Corps • ${corpsId?.slice(0, 8)}`}
          </h2>
          {generated && (
            <p className="text-muted" title={generated.title} style={{ marginTop: 4 }}>
              Generated {generated.label}
            </p>
          )}
        </div>
      </div>

      {entries.length === 0 ? (
        <p className="empty">No history entries found for this corps.</p>
      ) : (
        <DataTable<v1.V1HistoryEntry & Record<string, unknown>>
          columns={[
            { key: "season_id", label: "Season", render: (v) => <span className="cell-primary" title={String(v)}>{slugToTitle(String(v || ""))}</span> },
            { key: "show_slug", label: "Show", render: (v) => v ? <span title={String(v)}>{slugToTitle(String(v))}</span> : <span className="dim">-</span> },
            { key: "placement", label: "Place", render: (v) => <span className={`placement placement-${String(v)}`}>#{String(v)}</span> },
            { key: "final_score", label: "Score", render: (v) => <span className="trust-score">{formatNumber(Number(v))}</span> },
            { key: "artifacts", label: "Artifacts", render: (v) => String(Object.keys(v as Record<string, string>).length) },
            { key: "runs", label: "Runs", render: (v) => String((v as string[]).length) },
            {
              key: "entry_id",
              label: "",
              render: (_v, row) => (
                <button
                  className="primary small"
                  disabled={starting === row.entry_id}
                  onClick={() => handleStartSeance(row)}
                >
                  {starting === row.entry_id ? "Starting..." : "Start Seance"}
                </button>
              ),
            },
          ]}
          data={entries as (v1.V1HistoryEntry & Record<string, unknown>)[]}
          emptyMessage="No history entries found for this corps."
        />
      )}
    </div>
  );
}
