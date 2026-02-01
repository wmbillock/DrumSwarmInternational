import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";

export function ThreadList() {
  const navigate = useNavigate();
  const [threads, setThreads] = useState<v1.V1Thread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    v1.listThreads(ctrl.signal)
      .then(setThreads)
      .catch(e => { if (!ctrl.signal.aborted) setError(e.message); })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const result = await v1.createThread(newTitle.trim());
      navigate(`/design/${result.slug}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const statusVariant = (s: string) => {
    if (s === "approved") return "success";
    if (s === "published") return "info";
    if (s === "rejected") return "danger";
    if (s === "needs_review") return "warning";
    return "default";
  };

  if (loading) return <div className="page-loading">Loading threads...</div>;

  return (
    <div className="dashboard">
      <h2 className="page-title">Design Room</h2>

      <div className="create-form" style={{ marginBottom: 16 }}>
        <input
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleCreate()}
          placeholder="New show title..."
        />
        <button className="primary" onClick={handleCreate} disabled={creating || !newTitle.trim()}>
          {creating ? "Creating..." : "New Thread"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {threads.length === 0 && <p className="empty">No design threads yet. Create one to get started.</p>}

      <div className="cc-table-wrap">
        <table className="cc-table">
          <thead>
            <tr>
              <th>Thread</th>
              <th>Status</th>
              <th>Spec</th>
            </tr>
          </thead>
          <tbody>
            {threads.map(t => (
              <tr key={t.slug} className="clickable" onClick={() => navigate(`/design/${t.slug}`)}>
                <td>{t.slug}</td>
                <td><span className={`badge ${statusVariant(t.status)}`}>{t.status}</span></td>
                <td>{t.has_spec ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
