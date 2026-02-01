import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";

interface LibraryShow {
  slug: string;
  status: string;
  has_spec: boolean;
  title?: string;
  priority?: string;
  season_id?: string;
  created_at?: string;
  description?: string;
  summary?: string;
}

const STATUS_ORDER: Record<string, number> = {
  published: 0, approved: 1, needs_review: 2, draft: 3, archived: 4,
};

function getStatusColor(status: string): string {
  switch (status) {
    case "published":
      return "var(--stage-tour)"; // Green
    case "approved":
      return "var(--stage-library)"; // Blue
    case "needs_review":
      return "var(--stage-season)"; // Amber
    default:
      return "var(--border)"; // Gray
  }
}

function getStatusLabel(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function getNextAction(show: LibraryShow): { label: string; color: string; tooltip: string } {
  switch (show.status) {
    case "draft":
      return { label: "\u2192 Open Design Room", color: "var(--text-muted)", tooltip: "This show needs design work. Open the Design Room to collaborate with AI staff." };
    case "needs_review":
      return { label: "\u2192 Review & Approve", color: "var(--warning)", tooltip: "The spec is ready for review. Approve it to move forward." };
    case "approved":
      return { label: "\u2192 Publish Show", color: "var(--accent)", tooltip: "Show is approved. Publish it to make it available for seasons." };
    case "published":
      return { label: "\u2192 Add to Season", color: "var(--success)", tooltip: "Show is published. Add it to a season to begin competitions." };
    case "on_tour":
      return { label: "\u2192 Monitor Tour", color: "var(--success)", tooltip: "Corps are performing this show. Monitor progress on the Tour page." };
    case "completed":
      return { label: "\u2713 Done", color: "var(--text-muted)", tooltip: "This show has been completed." };
    default:
      return { label: "", color: "var(--text-muted)", tooltip: "" };
  }
}

export function ShowLibrary() {
  const navigate = useNavigate();
  const [shows, setShows] = useState<LibraryShow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    const ac = new AbortController();
    v1.listThreads(ac.signal)
      .then(threads => {
        setShows(threads.map(t => ({
          ...t,
          title: t.slug.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
        })));
      })
      .catch((e) => {
        if (e.name !== "AbortError") console.error(e);
      })
      .finally(() => setLoading(false));
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
    return ["all", ...Array.from(s).sort()];
  }, [shows]);

  const stats = {
    total: shows.length,
    published: shows.filter(s => s.status === "published").length,
    approved: shows.filter(s => s.status === "approved").length,
    draft: shows.filter(s => s.status === "draft").length,
    review: shows.filter(s => s.status === "needs_review").length,
  };

  if (loading) return <div className="page-loading">Loading show library...</div>;

  return (
    <div className="show-library-page">
      {/* Page Header */}
      <div className="show-library-header">
        <div className="show-library-title-block">
          <h1 className="show-library-title">SHOW LIBRARY</h1>
          <p className="show-library-subtitle">Manage and edit all shows in the system</p>
        </div>
        <button
          className="primary show-library-new-btn"
          onClick={() => navigate("/design")}
        >
          + NEW SHOW
        </button>
      </div>

      {/* Stats Bar */}
      <div className="show-library-stats">
        <div className="show-library-stat-item">
          <div className="show-library-stat-value">{stats.total}</div>
          <div className="show-library-stat-label">TOTAL</div>
        </div>
        <div className="show-library-stat-divider"></div>
        <div className="show-library-stat-item">
          <div className="show-library-stat-value" style={{ color: "var(--stage-tour)" }}>
            {stats.published}
          </div>
          <div className="show-library-stat-label">PUBLISHED</div>
        </div>
        <div className="show-library-stat-divider"></div>
        <div className="show-library-stat-item">
          <div className="show-library-stat-value" style={{ color: "var(--stage-library)" }}>
            {stats.approved}
          </div>
          <div className="show-library-stat-label">APPROVED</div>
        </div>
        <div className="show-library-stat-divider"></div>
        <div className="show-library-stat-item">
          <div className="show-library-stat-value" style={{ color: "var(--stage-season)" }}>
            {stats.review}
          </div>
          <div className="show-library-stat-label">IN REVIEW</div>
        </div>
        <div className="show-library-stat-divider"></div>
        <div className="show-library-stat-item">
          <div className="show-library-stat-value" style={{ color: "var(--text-muted)" }}>
            {stats.draft}
          </div>
          <div className="show-library-stat-label">DRAFT</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="show-library-toolbar">
        <input
          className="show-library-search"
          type="text"
          placeholder="Search by title or slug..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          className="show-library-filter"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          {statuses.map(s => (
            <option key={s} value={s}>
              {s === "all" ? "All Statuses" : getStatusLabel(s)}
            </option>
          ))}
        </select>
      </div>

      {/* Empty State */}
      {filtered.length === 0 && (
        <div className="show-library-empty">
          <div className="show-library-empty-icon">&#8709;</div>
          <p className="show-library-empty-text">No shows match your filters</p>
        </div>
      )}

      {/* Grid */}
      <div className="show-library-grid">
        {filtered.map(show => {
          const nextAction = getNextAction(show);
          return (
            <div
              key={show.slug}
              className="show-library-card"
              onClick={() => navigate(`/design/${show.slug}`)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  navigate(`/design/${show.slug}`);
                }
              }}
            >
              {/* Status indicator stripe */}
              <div
                className="show-library-card-stripe"
                style={{ background: getStatusColor(show.status) }}
              />

              {/* Card body */}
              <div className="show-library-card-content">
                {/* Title section */}
                <div className="show-library-card-title-block">
                  <h3 className="show-library-card-title">
                    {show.title || show.slug}
                  </h3>
                  <div
                    className="show-library-card-status-badge"
                    style={{
                      borderColor: getStatusColor(show.status),
                      color: getStatusColor(show.status),
                    }}
                    data-tooltip-id="main"
                    data-tooltip-content={`Status: ${getStatusLabel(show.status)}`}
                  >
                    {getStatusLabel(show.status)}
                  </div>
                </div>

                {/* Summary */}
                {show.summary && (
                  <p className="show-library-card-description" style={{ fontStyle: "italic", fontSize: 12 }}>
                    {show.summary}
                  </p>
                )}

                {/* Description */}
                {show.description && !show.summary && (
                  <p className="show-library-card-description">
                    {show.description}
                  </p>
                )}

                {/* Metadata */}
                <div className="show-library-card-meta">
                  <span
                    className="show-library-meta-item"
                    data-tooltip-id="main"
                    data-tooltip-content={show.has_spec ? "This show has a spec document defining requirements" : "No spec yet — open the Design Room to create one"}
                  >
                    {show.has_spec ? "\u2713 SPEC" : "\u2717 NO SPEC"}
                  </span>
                  {show.priority && (
                    <span className="show-library-meta-item">
                      {show.priority.toUpperCase()}
                    </span>
                  )}
                </div>

                {/* Next Action Badge */}
                {nextAction.label && (
                  <div
                    className="show-library-next-action"
                    style={{ color: nextAction.color, borderColor: nextAction.color }}
                    data-tooltip-id="main"
                    data-tooltip-content={nextAction.tooltip}
                  >
                    {nextAction.label}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
