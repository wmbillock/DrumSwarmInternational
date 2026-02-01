import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getDesignSpec, createDesignShow } from "../services/api";
import { DesignChat } from "../components/DesignChat";
import { SpecViewer } from "../components/SpecViewer";

export function DesignRoom() {
  const { showSlug } = useParams<{ showSlug: string }>();
  const navigate = useNavigate();
  const [specContent, setSpecContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  const fetchSpec = useCallback(async () => {
    if (!showSlug) return;
    try {
      const data = await getDesignSpec(showSlug);
      setSpecContent(data.content);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [showSlug]);

  useEffect(() => {
    if (showSlug) {
      fetchSpec();
    } else {
      setLoading(false);
    }
  }, [showSlug, fetchSpec]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const result = await createDesignShow(newTitle.trim());
      navigate(`/design/${result.slug}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  // No slug — show create form
  if (!showSlug) {
    return (
      <div className="dashboard">
        <h2 className="page-title">Design Room</h2>
        <p style={{ marginBottom: 16, color: "var(--text-secondary)" }}>
          Create a new show to start the design process.
        </p>
        <div className="create-form">
          <input
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleCreate()}
            placeholder="Show title..."
          />
          <button className="primary" onClick={handleCreate} disabled={creating || !newTitle.trim()}>
            {creating ? "Creating..." : "Create Show"}
          </button>
        </div>
        {error && <div className="error-banner">{error}</div>}
      </div>
    );
  }

  if (loading) return <div className="page-loading">Loading spec...</div>;
  if (error) return <div className="page-error"><div className="error-banner">{error}</div></div>;

  return (
    <div className="design-room">
      <div className="design-room-header">
        <button className="back-btn small" onClick={() => navigate("/design")}>Back</button>
        <h2>{showSlug}</h2>
      </div>
      <div className="design-room-panes">
        <div className="design-room-left">
          <DesignChat showSlug={showSlug} onSpecUpdate={fetchSpec} />
        </div>
        <div className="design-room-right">
          <SpecViewer showSlug={showSlug} content={specContent} onRefresh={fetchSpec} />
        </div>
      </div>
    </div>
  );
}
