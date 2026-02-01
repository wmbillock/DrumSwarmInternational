import { useState, useEffect } from "react";
import * as v1 from "../services/v1";

interface Props {
  showSlug: string;
}

export function VersionList({ showSlug }: Props) {
  const [versions, setVersions] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ctrl = new AbortController();
    v1.listVersions(showSlug, ctrl.signal)
      .then(data => setVersions(data.versions))
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [showSlug]);

  if (loading) return <div className="page-loading">Loading versions...</div>;

  return (
    <div style={{ padding: "12px 16px" }}>
      <div className="chat-toolbar">
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Approved Versions</span>
      </div>
      {versions.length === 0 ? (
        <p className="empty">No approved versions yet.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {versions.map(v => (
            <li key={v} style={{
              padding: "8px 12px",
              borderBottom: "1px solid var(--border)",
              fontSize: 13,
            }}>
              <span className="badge default">v{v}</span>
              <span style={{ marginLeft: 8, color: "var(--text-secondary)" }}>spec_v{v}.md</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
