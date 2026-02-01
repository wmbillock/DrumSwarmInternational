import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Panel, Badge } from "../ui";
import * as v1 from "../services/v1";

interface Props {
  corpsId: string;
  entry: v1.V1HistoryEntry;
  onBack: () => void;
}

export function ShowDetail({ corpsId, entry, onBack }: Props) {
  const navigate = useNavigate();
  const [seances, setSeances] = useState<v1.V1Seance[]>([]);
  const [preview, setPreview] = useState<{ path: string; content: string; truncated: boolean } | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    v1.listCorpsSeances(corpsId)
      .then(all => setSeances(all.filter(s => s.entry_id === entry.entry_id)))
      .catch(() => {});
  }, [corpsId, entry.entry_id]);

  const handlePreviewArtifact = async (artifactKey: string, artifactPath: string) => {
    // Artifacts in history entries are relative paths — we need a seance to preview them
    // For now, show the path info
    setPreview({ path: artifactPath, content: `Artifact: ${artifactKey}\nPath: ${artifactPath}`, truncated: false });
  };

  const handleTalkToED = async () => {
    if (creating) return;
    setCreating(true);
    try {
      const session = await v1.createSeance(corpsId, entry.entry_id);
      navigate(`/seance-session/${session.seance_id}`);
    } catch (e: any) {
      alert(`Failed to start seance: ${e.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <button className="back-btn small" onClick={onBack} style={{ marginBottom: 12 }}>
        ← Back to Show List
      </button>

      <Panel title={`${entry.show_slug || "Unknown Show"} — ${entry.season_id}`}>
        <div style={{ display: "flex", gap: 24, alignItems: "center", marginBottom: 16 }}>
          <div>
            <Badge variant={entry.placement <= 3 ? "success" : "default"}>
              #{entry.placement}
            </Badge>
          </div>
          <div>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Final Score: </span>
            <strong>{entry.final_score.toFixed(2)}</strong>
          </div>
          <div>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Runs: </span>
            <strong>{entry.runs.length}</strong>
          </div>
        </div>
      </Panel>

      {/* Artifacts */}
      <Panel title="Artifacts" className="mt-16">
        {Object.keys(entry.artifacts).length === 0 ? (
          <p className="empty">No artifacts recorded</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {Object.entries(entry.artifacts).map(([key, path]) => (
              <div
                key={key}
                className="agent-row clickable"
                onClick={() => handlePreviewArtifact(key, path)}
              >
                <span className="badge" style={{ fontSize: 10, minWidth: 90, textAlign: "center" }}>
                  {key}
                </span>
                <span className="agent-nickname" style={{ fontSize: 12 }}>{path}</span>
              </div>
            ))}
          </div>
        )}
        {preview && (
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h4 style={{ fontSize: 13, color: "var(--text-secondary)" }}>Preview: {preview.path}</h4>
              <button className="small" onClick={() => setPreview(null)}>Close</button>
            </div>
            <div className="code-block">
              <pre style={{ whiteSpace: "pre-wrap", fontSize: 11 }}>{preview.content}</pre>
            </div>
            {preview.truncated && (
              <p style={{ fontSize: 11, color: "var(--warning)", marginTop: 4 }}>Content truncated.</p>
            )}
          </div>
        )}
      </Panel>

      {/* Talk to the ED */}
      <Panel title="Talk to the ED" className="mt-16">
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>
          Start a seance session to discuss this show with the Executive Director, grounded in the show artifacts.
        </p>
        <button className="primary" onClick={handleTalkToED} disabled={creating}>
          {creating ? "Starting..." : "Talk to the ED"}
        </button>
      </Panel>

      {/* Past Seance Sessions */}
      {seances.length > 0 && (
        <Panel title="Past Seance Sessions" className="mt-16">
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {seances.map(s => (
              <div
                key={s.seance_id}
                className="agent-row clickable"
                onClick={() => navigate(`/seance-session/${s.seance_id}`)}
              >
                <span className={`badge ${s.status}`}>{s.status}</span>
                <span className="agent-nickname" style={{ fontSize: 12 }}>
                  {new Date(s.created_at).toLocaleString()}
                </span>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{s.seance_id.slice(0, 8)}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
