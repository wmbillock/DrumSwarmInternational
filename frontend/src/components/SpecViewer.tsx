import { useState } from "react";
import * as v1 from "../services/v1";

interface Props {
  showSlug: string;
  content: string;
  onRefresh: () => void;
}

export function SpecViewer({ showSlug, content, onRefresh }: Props) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(content);
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approveResult, setApproveResult] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    try {
      await v1.updateBrief(showSlug, editContent);
      setEditing(false);
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!confirm("Approve this spec? This will freeze the current version and mark the show as approved.")) return;
    setApproving(true);
    setApproveResult(null);
    try {
      const result = await v1.approveThread(showSlug);
      setApproveResult(`Approved as version ${result.version}`);
      onRefresh();
    } catch (err: any) {
      setApproveResult(`Error: ${err.message}`);
    } finally {
      setApproving(false);
    }
  };

  // Strip YAML front matter for display
  const displayContent = content.replace(/^---[\s\S]*?---\n?/, "");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="chat-toolbar" style={{ justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Show Spec</span>
        <div style={{ display: "flex", gap: 4 }}>
          {editing ? (
            <>
              <button className="small" onClick={() => { setEditing(false); setEditContent(content); }}>Cancel</button>
              <button className="primary small" onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </button>
            </>
          ) : (
            <button className="small" onClick={() => { setEditContent(content); setEditing(true); }}>Edit</button>
          )}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px" }}>
        {editing ? (
          <textarea
            value={editContent}
            onChange={e => setEditContent(e.target.value)}
            style={{
              width: "100%", height: "100%", minHeight: 300,
              background: "var(--bg-primary)", color: "var(--text-primary)",
              border: "1px solid var(--border)", borderRadius: 6,
              padding: 12, fontSize: 13, fontFamily: "monospace", resize: "vertical",
            }}
          />
        ) : (
          <div className="spec-content" style={{ fontSize: 13, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
            {displayContent || <span className="empty">Empty spec. Start chatting or click Edit.</span>}
          </div>
        )}
      </div>

      <div style={{
        padding: "8px 16px", borderTop: "1px solid var(--border)",
        background: "var(--bg-secondary)", display: "flex", alignItems: "center", gap: 8,
      }}>
        <button
          className="primary"
          onClick={handleApprove}
          disabled={approving || !content.trim()}
        >
          {approving ? "Approving..." : "Approve Show"}
        </button>
        {approveResult && (
          <span style={{ fontSize: 12, color: approveResult.startsWith("Error") ? "var(--danger)" : "var(--success)" }}>
            {approveResult}
          </span>
        )}
      </div>
    </div>
  );
}
