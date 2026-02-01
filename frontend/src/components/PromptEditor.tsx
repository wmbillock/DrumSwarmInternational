import { useState, useEffect } from "react";
import * as v1 from "../services/v1";

interface Props {
  showSlug: string;
}

export function PromptEditor({ showSlug }: Props) {
  const [content, setContent] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lintReport, setLintReport] = useState<v1.V1LintReport | null>(null);
  const [linting, setLinting] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    v1.getPrompt(showSlug, ctrl.signal)
      .then(data => { setContent(data.content); setEditContent(data.content); })
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [showSlug]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await v1.updatePrompt(showSlug, editContent);
      setContent(editContent);
      setEditing(false);
      setLintReport(null);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleLint = async () => {
    setLinting(true);
    try {
      const report = await v1.lintPrompt(showSlug);
      setLintReport(report);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLinting(false);
    }
  };

  if (loading) return <div className="page-loading">Loading prompt...</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="chat-toolbar" style={{ justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Show Prompt</span>
        <div style={{ display: "flex", gap: 4 }}>
          <button className="small" onClick={handleLint} disabled={linting}>
            {linting ? "Linting..." : "Lint"}
          </button>
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
        {lintReport && (
          <div style={{ marginBottom: 12 }}>
            {lintReport.required_fix.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <strong style={{ color: "var(--danger)" }}>Required Fixes ({lintReport.required_fix.length})</strong>
                {lintReport.required_fix.map((f, i) => (
                  <div key={i} style={{ fontSize: 12, padding: "4px 0", color: "var(--danger)" }}>
                    <strong>{f.section}:</strong> {f.message}
                  </div>
                ))}
              </div>
            )}
            {lintReport.nice_to_have.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <strong style={{ color: "var(--warning)" }}>Nice to Have ({lintReport.nice_to_have.length})</strong>
                {lintReport.nice_to_have.map((f, i) => (
                  <div key={i} style={{ fontSize: 12, padding: "4px 0", color: "var(--warning)" }}>
                    <strong>{f.section}:</strong> {f.message}
                  </div>
                ))}
              </div>
            )}
            {lintReport.acceptable_risk.length > 0 && (
              <div>
                <strong style={{ color: "var(--text-secondary)" }}>Acceptable Risk ({lintReport.acceptable_risk.length})</strong>
                {lintReport.acceptable_risk.map((f, i) => (
                  <div key={i} style={{ fontSize: 12, padding: "4px 0", color: "var(--text-secondary)" }}>
                    <strong>{f.section}:</strong> {f.message}
                  </div>
                ))}
              </div>
            )}
            {lintReport.required_fix.length === 0 && lintReport.nice_to_have.length === 0 && lintReport.acceptable_risk.length === 0 && (
              <div style={{ color: "var(--success)", fontSize: 13 }}>Prompt is clean — no findings.</div>
            )}
          </div>
        )}

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
            {content || <span className="empty">No prompt yet. Click Edit to write one.</span>}
          </div>
        )}

      </div>
    </div>
  );
}
