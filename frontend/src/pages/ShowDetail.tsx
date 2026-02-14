import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { Badge, Tabs, DataTable } from "../ui";
import { formatStatus, slugToTitle } from "../utils/formatters";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "prompt", label: "Show Prompt" },
  { key: "notes", label: "Design Notes" },
  { key: "competitions", label: "Competition History" },
];

export function ShowDetail() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [show, setShow] = useState<v1.V1ShowDetail | null>(null);
  const [competitions, setCompetitions] = useState<v1.V1ShowCompetition[]>([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!slug) return;
    const ac = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      v1.getShow(slug, ac.signal),
      v1.getShowCompetitions(slug, ac.signal).catch(() => []),
    ])
      .then(([showData, comps]) => {
        setShow(showData);
        setCompetitions(comps);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message || "Failed to load show");
      })
      .finally(() => setLoading(false));

    return () => ac.abort();
  }, [slug]);

  const handleCopyPrompt = async () => {
    if (!show?.show_prompt_content) return;
    try {
      await navigator.clipboard.writeText(show.show_prompt_content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-HTTPS
      const ta = document.createElement("textarea");
      ta.value = show.show_prompt_content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) return <div className="page-loading">Loading show...</div>;
  if (error || !show) {
    return (
      <div className="page-error">
        <div className="error-banner">{error || "Show not found"}</div>
        <button className="secondary" onClick={() => navigate("/shows")}>Back to Shows</button>
      </div>
    );
  }

  const statusColor: Record<string, string> = {
    published: "success",
    approved: "warning",
    needs_review: "warning",
    on_tour: "success",
    completed: "info",
    draft: "default",
  };

  const competitionColumns = [
    {
      key: "season_id",
      label: "Season",
      render: (_v: unknown, r: v1.V1ShowCompetition) => slugToTitle(r.season_id),
    },
    { key: "round", label: "Round", render: (_v: unknown, r: v1.V1ShowCompetition) => r.round ?? "—" },
    {
      key: "status",
      label: "Status",
      render: (_v: unknown, r: v1.V1ShowCompetition) => (
        <Badge variant={r.status === "completed" ? "success" : "default"}>
          {formatStatus(r.status)}
        </Badge>
      ),
    },
    {
      key: "winner",
      label: "Winner / Score",
      render: (_v: unknown, r: v1.V1ShowCompetition) => {
        if (!r.standings?.length) return <span className="text-muted">—</span>;
        const w = r.standings[0];
        return (
          <span>
            <strong>{slugToTitle(w.corps_id?.slice(0, 12))}</strong>{" "}
            {typeof w.final_score === "number" ? w.final_score.toFixed(1) : ""}
          </span>
        );
      },
    },
    {
      key: "actions",
      label: "",
      render: (_v: unknown, r: v1.V1ShowCompetition) => {
        if (!r.competition_id) return null;
        return (
          <button
            className="small"
            style={{ fontSize: 11, padding: "2px 8px" }}
            onClick={() => navigate(`/tour/${r.competition_id}`)}
          >
            View Results
          </button>
        );
      },
    },
  ];

  return (
    <div className="page-content show-detail-page">
      {/* Header */}
      <div className="show-detail-header">
        <button className="small" onClick={() => navigate("/shows")} style={{ marginBottom: 8 }}>
          &larr; Shows
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h1 className="page-title" style={{ margin: 0 }}>{show.title || slugToTitle(show.slug)}</h1>
          <Badge variant={statusColor[show.status] || "default"}>{formatStatus(show.status)}</Badge>
        </div>
        {show.summary && (
          <p className="text-muted" style={{ margin: "4px 0 0", fontSize: 13 }}>{show.summary}</p>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          {(show.status === "draft" || show.status === "needs_review") && (
            <button className="primary" onClick={() => navigate(`/design/${show.slug}`)}>
              Open Design Room
            </button>
          )}
          {show.status === "approved" && (
            <button
              className="primary"
              onClick={async () => {
                await v1.publishThread(show.slug);
                setShow({ ...show, status: "published" });
              }}
            >
              Publish
            </button>
          )}
          {(show.status === "published" || show.status === "on_tour" || show.status === "completed") && (
            <button className="secondary" onClick={() => navigate(`/design/${show.slug}`)}>
              Open Design Room
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs active={activeTab} onChange={setActiveTab} items={TABS} />

      {/* Tab Content */}
      <div className="show-detail-body">
        {activeTab === "overview" && (
          <div className="show-detail-overview">
            <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
              <div className="show-detail-meta-item">
                <span className="text-muted">Versions</span>
                <strong>{show.versions?.length || 0}</strong>
              </div>
              <div className="show-detail-meta-item">
                <span className="text-muted">Spec</span>
                <strong>{show.has_spec ? "Yes" : "None"}</strong>
              </div>
              <div className="show-detail-meta-item">
                <span className="text-muted">Prompt</span>
                <strong>{show.has_prompt ? "Yes" : "None"}</strong>
              </div>
              <div className="show-detail-meta-item">
                <span className="text-muted">Competitions</span>
                <strong>{competitions.length}</strong>
              </div>
            </div>
            {show.spec_content ? (
              <div className="show-detail-content-block">
                <h3>Spec</h3>
                <pre className="show-detail-pre">{show.spec_content}</pre>
              </div>
            ) : (
              <p className="text-muted">No spec document yet. Open the Design Room to create one.</p>
            )}
          </div>
        )}

        {activeTab === "prompt" && (
          <div className="show-detail-prompt">
            {show.show_prompt_content ? (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <h3 style={{ margin: 0 }}>Synthesized Show Prompt</h3>
                  <button className="small" onClick={handleCopyPrompt}>
                    {copied ? "Copied!" : "Copy to Clipboard"}
                  </button>
                </div>
                <pre className="show-detail-pre">{show.show_prompt_content}</pre>
              </>
            ) : (
              <p className="text-muted">No show prompt generated yet. Prompts are synthesized during the design process.</p>
            )}
          </div>
        )}

        {activeTab === "notes" && (
          <div className="show-detail-notes">
            {show.design_notes ? (
              <>
                <h3>Design Notes</h3>
                <pre className="show-detail-pre">{show.design_notes}</pre>
              </>
            ) : (
              <p className="text-muted">No design notes yet.</p>
            )}
          </div>
        )}

        {activeTab === "competitions" && (
          <div className="show-detail-competitions">
            {competitions.length > 0 ? (
              <DataTable columns={competitionColumns} data={competitions} />
            ) : (
              <p className="text-muted">This show hasn't been used in any competitions yet.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
