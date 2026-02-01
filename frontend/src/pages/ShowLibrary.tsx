import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge } from "../ui";

interface LibraryShow {
  slug: string;
  status: string;
  has_spec: boolean;
  title?: string;
  priority?: string;
  season_id?: string;
  created_at?: string;
  description?: string;
}

const STATUS_ORDER: Record<string, number> = {
  published: 0, approved: 1, needs_review: 2, draft: 3, archived: 4,
};

function statusVariant(s: string): "success" | "warning" | "danger" | "info" | "default" {
  if (s === "published") return "success";
  if (s === "approved") return "info";
  if (s === "needs_review") return "warning";
  if (s === "draft") return "default";
  return "default";
}

export function ShowLibrary() {
  const navigate = useNavigate();
  const [shows, setShows] = useState<LibraryShow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [seasons, setSeasons] = useState<v1.V1Season[]>([]);

  useEffect(() => {
    const ac = new AbortController();
    Promise.allSettled([
      v1.listThreads(ac.signal),
      v1.listSeasons(ac.signal),
    ]).then(([threadsRes, seasonsRes]) => {
      if (threadsRes.status === "fulfilled") {
        setShows(threadsRes.value.map(t => ({
          ...t,
          title: t.slug.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
        })));
      }
      if (seasonsRes.status === "fulfilled") {
        setSeasons(seasonsRes.value);
      }
      setLoading(false);
    });
    return () => ac.abort();
  }, []);

  const filtered = useMemo(() => {
    let result = [...shows];
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(s =>
        s.slug.includes(q) || (s.title || "").toLowerCase().includes(q)
      );
    }
    if (statusFilter !== "all") {
      result = result.filter(s => s.status === statusFilter);
    }
    result.sort((a, b) => (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99));
    return result;
  }, [shows, search, statusFilter]);

  const statuses = useMemo(() => {
    const s = new Set(shows.map(s => s.status));
    return ["all", ...Array.from(s)];
  }, [shows]);

  if (loading) return <div className="page-loading">Loading show library...</div>;

  return (
    <div className="show-library">
      <h1 className="page-title">Show Library</h1>

      <div className="summary-bar">
        <div className="summary-stat">
          <span className="summary-value">{shows.length}</span>
          <span className="summary-label">Total</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{shows.filter(s => s.status === "published").length}</span>
          <span className="summary-label">Published</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{shows.filter(s => s.status === "draft").length}</span>
          <span className="summary-label">Drafts</span>
        </div>
        <div className="summary-stat">
          <span className="summary-value">{shows.filter(s => s.status === "approved").length}</span>
          <span className="summary-label">Approved</span>
        </div>
      </div>

      <div className="library-toolbar">
        <input
          className="library-search"
          placeholder="Search shows..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          className="library-filter"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          {statuses.map(s => (
            <option key={s} value={s}>{s === "all" ? "All Statuses" : s}</option>
          ))}
        </select>
        <button className="primary" onClick={() => navigate("/design")}>
          + New Show
        </button>
      </div>

      {filtered.length === 0 && (
        <p className="empty">No shows match your filters.</p>
      )}

      <div className="library-grid">
        {filtered.map(show => (
          <div
            key={show.slug}
            className="library-card"
            onClick={() => navigate(`/design/${show.slug}`)}
          >
            <div
              className="library-card-stage"
              style={{
                background: show.status === "published" ? "var(--stage-tour)"
                  : show.status === "approved" ? "var(--stage-library)"
                  : show.status === "needs_review" ? "var(--stage-season)"
                  : "var(--border)",
              }}
            />
            <div className="library-card-body">
              <div className="library-card-header">
                <h3>{show.title || show.slug}</h3>
                <Badge variant={statusVariant(show.status)}>{show.status}</Badge>
              </div>
              <div className="library-card-meta">
                {show.has_spec && <span className="badge">Has Spec</span>}
                {show.priority && (
                  <span className={`priority-badge ${show.priority}`}>{show.priority}</span>
                )}
              </div>
              {show.description && (
                <p className="library-card-desc">{show.description}</p>
              )}
              <div className="library-card-footer">
                <span>{show.slug}</span>
                <div className="library-card-actions" onClick={e => e.stopPropagation()}>
                  {seasons.length > 0 && (
                    <select
                      className="library-filter"
                      style={{ fontSize: "10px", padding: "2px 4px" }}
                      defaultValue=""
                      onClick={e => e.stopPropagation()}
                    >
                      <option value="" disabled>Assign Season</option>
                      {seasons.map(s => (
                        <option key={s.season_id} value={s.season_id}>{s.season_id}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
