import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";

const ACTIVE_STATUSES = new Set(["draft", "needs_review", "approved", "published", "on_tour"]);

export function ThreadList() {
  const navigate = useNavigate();
  const [threads, setThreads] = useState<v1.V1Thread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState("active");

  useEffect(() => {
    const ctrl = new AbortController();
    v1.listThreads(ctrl.signal)
      .then(setThreads)
      .catch(e => { if (!ctrl.signal.aborted) setError(e.message); })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  const filteredThreads = useMemo(() => {
    if (statusFilter === "all") return threads;
    if (statusFilter === "active") return threads.filter(t => ACTIVE_STATUSES.has(t.status));
    return threads.filter(t => t.status === statusFilter);
  }, [threads, statusFilter]);

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

      <div className="create-form" style={{ marginBottom: 16, display: "flex", gap: 8, alignItems: "center" }}>
        <input
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleCreate()}
          placeholder="New show title..."
        />
        <button className="primary" onClick={handleCreate} disabled={creating || !newTitle.trim()}>
          {creating ? "Creating..." : "New Thread"}
        </button>
        <select
          className="show-library-filter"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          style={{ marginLeft: "auto" }}
        >
          <option value="active">Active ({threads.filter(t => ACTIVE_STATUSES.has(t.status)).length})</option>
          <option value="all">All ({threads.length})</option>
          <option value="draft">Draft</option>
          <option value="needs_review">Needs Review</option>
          <option value="approved">Approved</option>
          <option value="published">Published</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {filteredThreads.length === 0 && <p className="empty">{statusFilter === "all" ? "No design threads yet. Create one to get started." : "No threads match this filter."}</p>}

      <div className="cc-table-wrap">
        <table className="cc-table">
          <thead>
            <tr>
              <th>Thread</th>
              <th>Summary</th>
              <th>Status</th>
              <th>Spec</th>
            </tr>
          </thead>
          <tbody>
            {filteredThreads.map(t => (
              <tr key={t.slug} className="clickable" onClick={() => navigate(`/design/${t.slug}`)}>
                <td>{t.slug}</td>
                <td style={{ fontSize: 12, fontStyle: "italic", color: "var(--text-secondary)" }}>{t.summary || "—"}</td>
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
