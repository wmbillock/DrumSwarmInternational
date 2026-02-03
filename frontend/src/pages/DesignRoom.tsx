import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { ThreadList } from "../components/ThreadList";
import { DesignChat } from "../components/DesignChat";
import { ArtifactPanel } from "../components/ArtifactPanel";
import { DevilsAdvocate } from "../components/DevilsAdvocate";

function ThreadDetail({ showSlug }: { showSlug: string }) {
  const navigate = useNavigate();
  const [specContent, setSpecContent] = useState("");
  const [threadStatus, setThreadStatus] = useState<string>("draft");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPublishGate, setShowPublishGate] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const fetchData = useCallback(async () => {
    try {
      const [brief, threads] = await Promise.all([
        v1.getBrief(showSlug),
        v1.listThreads(),
      ]);
      setSpecContent(brief.content);
      const thread = threads.find(t => t.slug === showSlug);
      if (thread) setThreadStatus(thread.status);
      setError(null);
      setRefreshKey(k => k + 1);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [showSlug]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="page-loading">Loading thread...</div>;
  if (error) return <div className="page-error"><div className="error-banner">{error}</div></div>;

  const statusVariant = (s: string) => {
    if (s === "approved") return "success";
    if (s === "published") return "info";
    if (s === "rejected") return "danger";
    if (s === "needs_review") return "warning";
    return "default";
  };

  return (
    <div className="design-room">
      <div className="design-room-header" style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button className="back-btn small" onClick={() => navigate("/design")}>Back</button>
        <h2 style={{ margin: 0 }}>{showSlug}</h2>
        <span
          className={`badge ${statusVariant(threadStatus)}`}
          data-tooltip-id="main"
          data-tooltip-content={`Current status: ${threadStatus}. ${threadStatus === "draft" ? "Send design messages to develop the spec." : threadStatus === "needs_review" ? "Ready for approval." : threadStatus === "approved" ? "Ready to publish." : threadStatus === "published" ? "Available for seasons." : ""}`}
        >
          {threadStatus}
        </span>
        {threadStatus === "approved" && (
          <button
            className="primary small"
            onClick={() => setShowPublishGate(true)}
            style={{ marginLeft: "auto" }}
            data-tooltip-id="main"
            data-tooltip-content="Run the Devil's Advocate review, then publish this show to make it available for seasons"
          >
            Publish
          </button>
        )}
      </div>
      <div className="design-room-panes">
        <div className="design-room-left">
          <DesignChat showSlug={showSlug} onSpecUpdate={fetchData} />
        </div>
        <div className="design-room-right">
          <ArtifactPanel showSlug={showSlug} specContent={specContent} onRefresh={fetchData} refreshKey={refreshKey} />
        </div>
      </div>
      {showPublishGate && (
        <DevilsAdvocate
          showSlug={showSlug}
          onClose={() => setShowPublishGate(false)}
          onPublished={() => { setShowPublishGate(false); fetchData(); }}
        />
      )}
    </div>
  );
}

export function DesignRoom() {
  const { showSlug } = useParams<{ showSlug: string }>();

  if (!showSlug) {
    return <ThreadList />;
  }

  return <ThreadDetail showSlug={showSlug} />;
}
