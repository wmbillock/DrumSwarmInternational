import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { CorpsCreateModal } from "../components/CorpsCreateModal";

const STATE_LABELS: Record<string, string> = {
  initializing: "Initializing",
  winter_camps: "Winter Camps",
  on_tour: "On Tour",
  completed: "Completed",
  disbanded: "Disbanded",
  commissioned: "Commissioned",
  active: "Active",
  contending: "Contending",
};

export function CorpsList() {
  const navigate = useNavigate();
  const [corps, setCorps] = useState<v1.V1Corps[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    v1.listCorps(undefined, true)
      .then(setCorps)
      .catch(e => setError(e instanceof Error ? e.message : "Failed to load corps"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading Corps...</div>;

  return (
    <div className="corps-list-page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Corps</h1>
        <button className="primary" onClick={() => setShowModal(true)}>
          Create Corps
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {showModal && (
        <CorpsCreateModal
          onCreated={(created) => {
            setCorps(prev => [...prev, created]);
            setShowModal(false);
          }}
          onClose={() => setShowModal(false)}
        />
      )}

      {corps.length === 0 && !error && (
        <p className="empty">No corps found. Create one to get started.</p>
      )}

      {corps.filter(c => c.corps_type !== "system").length > 0 && (
        <div className="corps-card-grid">
          {corps.filter(c => c.corps_type !== "system").map(c => (
            <div key={c.corps_id} className="corps-list-card clickable" onClick={() => navigate(`/corps/${c.corps_id}`)}>
              <div className="corps-list-header">
                <span className="corps-list-name">{c.display_name}</span>
                <span className={`badge state-${c.state}`}>{STATE_LABELS[c.state] || c.state}</span>
              </div>
              {c.philosophy && <p className="corps-list-philosophy">{c.philosophy}</p>}
            </div>
          ))}
        </div>
      )}

      {corps.filter(c => c.corps_type === "system").length > 0 && (
        <details style={{ marginTop: 24 }}>
          <summary style={{ cursor: "pointer", fontSize: 14, color: "var(--text-secondary)" }}>
            System Corps ({corps.filter(c => c.corps_type === "system").length})
          </summary>
          <div className="corps-card-grid" style={{ marginTop: 8 }}>
            {corps.filter(c => c.corps_type === "system").map(c => (
              <div key={c.corps_id} className="corps-list-card clickable" onClick={() => navigate(`/corps/${c.corps_id}`)}>
                <div className="corps-list-header">
                  <span className="corps-list-name">{c.display_name}</span>
                  <span className={`badge state-${c.state}`}>{STATE_LABELS[c.state] || c.state}</span>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
