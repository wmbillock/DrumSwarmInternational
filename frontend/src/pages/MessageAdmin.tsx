import { useCallback, useEffect, useMemo, useState } from "react";
import * as v1 from "../services/v1";
import "../styles/MessageAdmin.css";
import { formatTimestamp } from "../utils/formatters";

interface ThreadListItem {
  thread_id: string;
  originator_role: string;
  subject: string;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export default function MessageAdmin() {
  const [threads, setThreads] = useState<ThreadListItem[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState("");
  const [userRole] = useState("admin"); // TODO: wire auth

  const loadThreads = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await v1.listMessagingThreads("completed", undefined, 200, 0);
      setThreads(res.threads || []);
      setSelected({});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load completed threads");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  const selectedIds = useMemo(
    () => Object.entries(selected).filter(([, v]) => v).map(([k]) => k),
    [selected],
  );

  const toggleAll = (checked: boolean) => {
    const next: Record<string, boolean> = {};
    for (const t of threads) next[t.thread_id] = checked;
    setSelected(next);
  };

  const handleArchive = useCallback(async () => {
    if (!selectedIds.length) return;
    setArchiving(true);
    setError("");
    setResult("");
    try {
      const res = await v1.bulkArchiveThreads(selectedIds, userRole, "admin-user");
      setResult(`Archived ${res.count_archived} thread(s).`);
      await loadThreads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to bulk archive");
    } finally {
      setArchiving(false);
    }
  }, [selectedIds, userRole, loadThreads]);

  const canAccess = userRole === "admin";
  if (!canAccess) {
    return (
      <div className="page-content message-admin">
        <div className="page-header">
          <h1 className="page-title">Message Admin</h1>
        </div>
        <div className="error-banner">
          <p>Access denied. Only administrators can bulk-archive threads.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content message-admin">
      <div className="admin-header page-header">
        <h1 className="page-title">Message Admin</h1>
        <p>Bulk archive completed threads with LLM summaries.</p>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={loadThreads}>Retry</button>
        </div>
      )}
      {result && <div className="admin-success">{result}</div>}

      <div className="admin-actions">
        <button onClick={() => loadThreads()} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
        <button
          className="danger"
          onClick={handleArchive}
          disabled={archiving || selectedIds.length === 0}
        >
          {archiving ? "Archiving..." : `Archive Selected (${selectedIds.length})`}
        </button>
      </div>

      <div className="admin-list">
        <div className="admin-list-header">
          <label>
            <input
              type="checkbox"
              onChange={(e) => toggleAll(e.target.checked)}
              checked={threads.length > 0 && selectedIds.length === threads.length}
            />
            Select all
          </label>
          <span>{threads.length} completed thread(s)</span>
        </div>
        {threads.length === 0 && !loading && (
          <div className="admin-empty">No completed threads available.</div>
        )}
        {threads.map((t) => (
          <label key={t.thread_id} className="admin-item">
            <input
              type="checkbox"
              checked={!!selected[t.thread_id]}
              onChange={(e) =>
                setSelected((prev) => ({ ...prev, [t.thread_id]: e.target.checked }))
              }
            />
            <div className="admin-item-body">
              <div className="admin-item-subject">{t.subject}</div>
              <div className="admin-item-meta">
                <span>{t.originator_role}</span>
                <span>{t.message_count} msgs</span>
                {(() => {
                  const ts = formatTimestamp(t.updated_at);
                  return <span title={ts.title}>{ts.label}</span>;
                })()}
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
