import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { CorpsCreateModal } from "../components/CorpsCreateModal";
import { CORPS_THEMES } from "../contexts/CorpsThemeContext";

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

function luminance(hex: string): number {
  const rgb = hex.replace("#", "").match(/.{2}/g);
  if (!rgb) return 0;
  const [r, g, b] = rgb.map(c => {
    const v = parseInt(c, 16) / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function getCorpsColors(c: v1.V1Corps): { primary: string; secondary: string; textColor: string } {
  const theme = c.theme_id ? CORPS_THEMES[c.theme_id] : undefined;
  const primary = theme?.primary || "var(--accent, #58a6ff)";
  const secondary = theme?.secondary || "var(--bg-secondary, #1a1a2e)";
  const textColor = theme?.secondary && luminance(theme.secondary) < 0.15 ? "#e0e0e0" : "#1a1a2e";
  return { primary, secondary, textColor };
}

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

  const userCorps = corps.filter(c => c.corps_type !== "system");
  const systemCorps = corps.filter(c => c.corps_type === "system");

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

      {userCorps.length > 0 && (
        <div className="corps-card-grid">
          {userCorps.map(c => {
            const { primary, secondary, textColor } = getCorpsColors(c);
            return (
              <div
                key={c.corps_id}
                className="corps-list-card clickable"
                onClick={() => navigate(`/corps/${c.corps_id}`)}
                style={{
                  borderLeft: `4px solid ${primary}`,
                  background: secondary !== "var(--bg-secondary, #1a1a2e)"
                    ? `${secondary}18`
                    : undefined,
                  color: textColor,
                }}
              >
                <div className="corps-list-header">
                  <span className="corps-list-name">{c.display_name}</span>
                  <span className={`badge state-${c.state}`}>{STATE_LABELS[c.state] || c.state}</span>
                </div>
                {c.mascot && <p className="corps-list-mascot" style={{ fontSize: "0.8rem", opacity: 0.7, margin: "4px 0 0" }}>{c.mascot}</p>}
                {c.philosophy && <p className="corps-list-philosophy">{c.philosophy}</p>}
              </div>
            );
          })}
        </div>
      )}

      {systemCorps.length > 0 && (
        <details style={{ marginTop: 24 }}>
          <summary style={{ cursor: "pointer", fontSize: 14, color: "var(--text-secondary)" }}>
            System Corps ({systemCorps.length})
          </summary>
          <div className="corps-card-grid" style={{ marginTop: 8 }}>
            {systemCorps.map(c => (
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
