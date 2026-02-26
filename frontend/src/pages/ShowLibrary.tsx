import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { formatStatus, formatTimestamp, slugToTitle } from "../utils/formatters";

interface LibraryShow {
  slug: string;
  status: string;
  has_spec: boolean;
  title?: string;
  priority?: string;
  season_id?: string;
  created_at?: string;
  updated_at?: string;
  description?: string;
  summary?: string;
}

const STATUS_ORDER: Record<string, number> = {
  active: 0, published: 1, approved: 2, needs_review: 3, draft: 4, on_tour: 5, completed: 6, archived: 7,
};

const ACTIVE_STATUSES = new Set(["active", "draft", "needs_review", "approved", "published", "on_tour"]);

const STATUS_COLORS: Record<string, string> = {
  published: "#DC143C",
  approved: "#FFA500",
  draft: "#2D3436",
};

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
      return { label: `Status: ${status}`, color: "var(--text-muted)", tooltip: `Current status: ${status}` };
  }
}

export function ShowLibrary() {
  const navigate = useNavigate();
  const [shows, setShows] = useState<LibraryShow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");

  useEffect(() => {
    const ac = new AbortController();
    v1.listThreads(ac.signal)
      .then(threads => {
        setShows(threads.map(t => ({
          ...t,
          title: slugToTitle(t.slug),
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
    if (statusFilter === "active") {
      result = result.filter(s => ACTIVE_STATUSES.has(s.status));
    } else if (statusFilter !== "all") {
      result = result.filter(s => s.status === statusFilter);
    }
    result.sort((a, b) => (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99));
    return result;
  }, [shows, search, statusFilter]);

  const statuses = useMemo(() => {
    const s = new Set(shows.map(s => s.status));
    return ["active", "all", ...Array.from(s).sort()];
  }, [shows]);

  const stats = {
    total: shows.length,
    active: shows.filter(s => ACTIVE_STATUSES.has(s.status)).length,
    published: shows.filter(s => s.status === "published").length,
    approved: shows.filter(s => s.status === "approved").length,
    draft: shows.filter(s => s.status === "draft").length,
    review: shows.filter(s => s.status === "needs_review").length,
    completed: shows.filter(s => s.status === "completed").length,
  };

  const handleDeleteShow = async (slug: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Delete show "${slug}"? This cannot be undone.`)) return;
    try {
      await v1.deleteShow(slug);
      setShows(prev => prev.filter(s => s.slug !== slug));
    } catch (err: any) {
      console.error("Failed to delete show:", err);
    }
  };

  if (loading) return <div className="page-loading">Loading show library...</div>;

  return (
    <div className="page-content show-library-page">
      {/* Page Header */}
      <div className="show-library-header page-header">
        <div className="show-library-title-block">
          <h1 className="show-library-title page-title">SHOW LIBRARY</h1>
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
          <div className="show-library-stat-value">{stats.active}</div>
          <div className="show-library-stat-label">ACTIVE</div>
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
        <div className="show-library-stat-divider"></div>
        <div className="show-library-stat-item">
          <div className="show-library-stat-value" style={{ color: "var(--text-muted)" }}>
            {stats.completed}
          </div>
          <div className="show-library-stat-label">COMPLETED</div>
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
              {s === "active" ? "Active Shows" : s === "all" ? "All Statuses" : formatStatus(s)}
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
          const statusColor = STATUS_COLORS[show.status] || "var(--border)";
          const created = show.created_at ? formatTimestamp(show.created_at) : null;
          const updated = show.updated_at ? formatTimestamp(show.updated_at) : null;
          return (
            <div
              key={show.slug}
              className="show-library-card"
              onClick={() => navigate(`/shows/${show.slug}`)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  navigate(`/shows/${show.slug}`);
                }
              }}
            >
              {/* Status indicator stripe */}
              <div
                className="show-library-card-stripe"
                style={{ background: statusColor }}
              />

              {/* Card body */}
              <div className="show-library-card-content">
                {/* Title section */}
                <div className="show-library-card-title-block">
                  <h3 className="show-library-card-title">
                    {show.title || slugToTitle(show.slug)}
                  </h3>
                  <div
                    className="show-library-card-status-badge"
                    data-tooltip-id="main"
                    data-tooltip-content={`Status: ${formatStatus(show.status)}`}
                    style={{ borderColor: statusColor, color: statusColor }}
                  >
                    {formatStatus(show.status)}
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
                  <span className="show-library-meta-item mono" title={created?.title || ""}>
                    {created ? `Created ${created.label}` : "Created —"}
                  </span>
                  <span
                    className="show-library-meta-item mono"
                    data-tooltip-id="main"
                    data-tooltip-content={show.has_spec ? "This show has a spec document defining requirements" : "No spec yet — open the Design Room to create one"}
                  >
                    {show.has_spec ? "\u2713 SPEC" : "\u2717 NO SPEC"}
                  </span>
                  <span className="show-library-meta-item mono" title={updated?.title || ""}>
                    {updated ? `Updated ${updated.label}` : "Updated —"}
                  </span>
                </div>

                {/* Next Action + Delete */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
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
                  <button
                    className="small danger"
                    style={{ fontSize: "0.7rem", padding: "2px 8px", opacity: 0.6 }}
                    onClick={(e) => handleDeleteShow(show.slug, e)}
                    data-tooltip-id="main"
                    data-tooltip-content="Delete this show permanently"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
