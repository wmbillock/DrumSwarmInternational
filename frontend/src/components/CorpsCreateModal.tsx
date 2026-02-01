import { useState, useEffect } from "react";
import * as v1 from "../services/v1";

interface CorpsCreateModalProps {
  onCreated: (corps: v1.V1CreatedCorps) => void;
  onClose: () => void;
}

function ColorSwatch({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 6,
          backgroundColor: color,
          border: "1px solid var(--border)",
        }}
      />
      <div>
        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{label}</div>
        <div className="mono" style={{ fontSize: 12 }}>{color}</div>
      </div>
    </div>
  );
}

export function CorpsCreateModal({ onCreated, onClose }: CorpsCreateModalProps) {
  const [identity, setIdentity] = useState<v1.CorpsIdentity | null>(null);
  const [iconDesc, setIconDesc] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  // Editable overrides
  const [editName, setEditName] = useState("");
  const [editMascot, setEditMascot] = useState("");
  const [editUniform, setEditUniform] = useState("");
  const [editColors, setEditColors] = useState<{ primary: string; secondary: string; accent: string } | null>(null);

  const generate = async () => {
    setLoading(true);
    setError("");
    try {
      const id = await v1.generateCorpsIdentity();
      setIdentity(id);
      setEditName(id.name);
      setEditMascot(id.mascot);
      setEditUniform(id.uniform_concept);
      setEditColors(id.color_scheme);
      // Fire off icon generation in background
      v1.generateCorpsIcon(id.icon_prompt)
        .then((r) => setIconDesc(r.description))
        .catch(() => setIconDesc("Icon generation unavailable"));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate identity");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { generate(); }, []);

  const handleCreate = async () => {
    if (!editName.trim()) return;
    setCreating(true);
    setError("");
    try {
      const corps = await v1.createCorps({
        name: editName.trim(),
        mascot: editMascot || undefined,
        color_scheme: editColors || undefined,
        uniform_concept: editUniform || undefined,
      });
      onCreated(corps);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create corps");
      setCreating(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create New Corps</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-muted)" }}>
            Generating corps identity...
          </div>
        ) : identity ? (
          <div className="modal-body">
            <div className="form-group">
              <label className="form-label">
                Corps Name
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    className="form-input"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                  />
                  <button className="small" onClick={() => {
                    v1.generateCorpsIdentity().then((id) => setEditName(id.name)).catch(() => {});
                  }}>Re-roll</button>
                </div>
              </label>
            </div>

            <div className="form-group">
              <label className="form-label">
                Mascot
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    className="form-input"
                    value={editMascot}
                    onChange={(e) => setEditMascot(e.target.value)}
                  />
                  <button className="small" onClick={() => {
                    v1.generateCorpsIdentity().then((id) => setEditMascot(id.mascot)).catch(() => {});
                  }}>Re-roll</button>
                </div>
              </label>
            </div>

            <div className="form-group">
              <label className="form-label">Color Scheme</label>
              {editColors && (
                <div style={{ display: "flex", gap: 16, marginBottom: 8 }}>
                  <ColorSwatch color={editColors.primary} label="Primary" />
                  <ColorSwatch color={editColors.secondary} label="Secondary" />
                  <ColorSwatch color={editColors.accent} label="Accent" />
                </div>
              )}
              <button className="small" onClick={() => {
                v1.generateCorpsIdentity().then((id) => setEditColors(id.color_scheme)).catch(() => {});
              }}>Re-roll Colors</button>
            </div>

            <div className="form-group">
              <label className="form-label">
                Uniform Concept
                <textarea
                  className="form-input"
                  rows={2}
                  value={editUniform}
                  onChange={(e) => setEditUniform(e.target.value)}
                />
              </label>
            </div>

            {iconDesc && (
              <div className="form-group">
                <label className="form-label">Icon Description</label>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", fontStyle: "italic" }}>
                  {iconDesc}
                </p>
              </div>
            )}

            {/* Preview banner */}
            {editColors && (
              <div
                style={{
                  padding: "12px 16px",
                  borderRadius: 8,
                  background: `linear-gradient(135deg, ${editColors.primary}, ${editColors.secondary})`,
                  color: "#fff",
                  marginTop: 12,
                }}
              >
                <div style={{ fontSize: 18, fontWeight: "bold" }}>{editName || "Unnamed Corps"}</div>
                <div style={{ fontSize: 13, opacity: 0.9 }}>{editMascot}</div>
                <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>{editUniform}</div>
              </div>
            )}
          </div>
        ) : null}

        <div className="modal-footer">
          <button className="primary" onClick={generate} disabled={loading}>
            {loading ? "Generating..." : "Re-generate All"}
          </button>
          <button className="primary" onClick={handleCreate} disabled={creating || loading || !editName.trim()}>
            {creating ? "Creating..." : "Approve & Create"}
          </button>
          <button onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
