import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";

export function CorpsHistory() {
  const { corpsId } = useParams<{ corpsId: string }>();
  const navigate = useNavigate();
  const [corpsList, setCorpsList] = useState<v1.V1Corps[]>([]);
  const [index, setIndex] = useState<v1.V1HistoryIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    if (!corpsId) {
      v1.listCorps(ac.signal)
        .then(setCorpsList)
        .catch(e => { if (e.name !== "AbortError") setError(e.message); })
        .finally(() => setLoading(false));
    } else {
      v1.getCorpsHistory(corpsId, ac.signal)
        .then(setIndex)
        .catch(e => { if (e.name !== "AbortError") setError(e.message); })
        .finally(() => setLoading(false));
    }
    return () => ac.abort();
  }, [corpsId]);

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
  if (error) return <div className="dashboard"><div className="error-banner">{error}</div></div>;

  // Corps picker
  if (!corpsId) {
    return (
      <div className="dashboard">
        <h2 className="page-title">Corps History</h2>
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
                <span className={`badge ${c.state}`}>{c.state}</span>
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

  return (
    <div className="dashboard">
      <div className="page-header">
        <button className="back-btn small" onClick={() => navigate("/history")}>Back</button>
        <h2 className="page-title" style={{ margin: 0 }}>History: {corpsId}</h2>
      </div>

      {entries.length === 0 ? (
        <p className="empty">No history entries found for this corps.</p>
      ) : (
        <div className="table-wrapper">
          <table className="styled-table">
            <thead>
              <tr>
                <th>Season</th>
                <th>Show</th>
                <th>Place</th>
                <th>Score</th>
                <th>Artifacts</th>
                <th>Runs</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {entries.map(entry => (
                <tr key={entry.entry_id}>
                  <td className="cell-primary">{entry.season_id}</td>
                  <td>{entry.show_slug || <span className="dim">-</span>}</td>
                  <td>
                    <span className={`placement placement-${entry.placement}`}>
                      #{entry.placement}
                    </span>
                  </td>
                  <td className="trust-score">{entry.final_score}</td>
                  <td>{Object.keys(entry.artifacts).length}</td>
                  <td>{entry.runs.length}</td>
                  <td>
                    <button
                      className="primary small"
                      disabled={starting === entry.entry_id}
                      onClick={() => handleStartSeance(entry)}
                    >
                      {starting === entry.entry_id ? "Starting..." : "Start Seance"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
