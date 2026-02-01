import { useState, useEffect } from "react";
import * as v1 from "../services/v1";

interface Props {
  showSlug: string;
  onClose: () => void;
  onPublished: () => void;
}

const CHECKLIST_ITEMS = [
  "I have reviewed the prompt for completeness",
  "Edge cases and constraints are addressed",
  "Evaluation rubric matches show goals",
];

export function DevilsAdvocate({ showSlug, onClose, onPublished }: Props) {
  const [lintReport, setLintReport] = useState<v1.V1LintReport | null>(null);
  const [linting, setLinting] = useState(true);
  const [checked, setChecked] = useState<boolean[]>(CHECKLIST_ITEMS.map(() => false));
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    v1.lintPrompt(showSlug)
      .then(setLintReport)
      .catch(e => setError(e.message))
      .finally(() => setLinting(false));
  }, [showSlug]);

  const allChecked = checked.every(Boolean);
  const lintClean = lintReport ? lintReport.required_fix.length === 0 : false;
  const canPublish = allChecked && lintClean && !publishing;

  const handlePublish = async () => {
    setPublishing(true);
    setError(null);
    try {
      await v1.publishThread(showSlug);
      onPublished();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setPublishing(false);
    }
  };

  const toggleCheck = (i: number) => {
    setChecked(prev => prev.map((v, idx) => idx === i ? !v : v));
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{
        background: "var(--bg-primary)", borderRadius: 12, padding: 24,
        maxWidth: 560, width: "90%", maxHeight: "80vh", overflowY: "auto",
        border: "1px solid var(--border)",
      }}>
        <h3 style={{ marginTop: 0 }}>Devil's Advocate Review</h3>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
          "Hold on — before this hits the field, let's make sure it survives a
          Drum Corps World opinion column. Would this prompt hold up under scrutiny
          from someone who'd question switching from G to Bb-keyed instruments?"
        </p>

        {linting && <div className="page-loading">Running lint...</div>}
        {error && <div className="error-banner">{error}</div>}

        {lintReport && (
          <div style={{ marginBottom: 16 }}>
            {lintReport.required_fix.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <span className="badge danger">Required Fixes ({lintReport.required_fix.length})</span>
                {lintReport.required_fix.map((f, i) => (
                  <div key={i} style={{ fontSize: 12, padding: "4px 0 4px 8px", color: "var(--danger)" }}>
                    <strong>{f.section}:</strong> {f.message}
                  </div>
                ))}
              </div>
            )}
            {lintReport.nice_to_have.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <span className="badge warning">Nice to Have ({lintReport.nice_to_have.length})</span>
                {lintReport.nice_to_have.map((f, i) => (
                  <div key={i} style={{ fontSize: 12, padding: "4px 0 4px 8px", color: "var(--warning)" }}>
                    <strong>{f.section}:</strong> {f.message}
                  </div>
                ))}
              </div>
            )}
            {lintReport.acceptable_risk.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <span className="badge" style={{ background: "var(--bg-secondary)" }}>Acceptable Risk ({lintReport.acceptable_risk.length})</span>
                {lintReport.acceptable_risk.map((f, i) => (
                  <div key={i} style={{ fontSize: 12, padding: "4px 0 4px 8px", color: "var(--text-secondary)" }}>
                    <strong>{f.section}:</strong> {f.message}
                  </div>
                ))}
              </div>
            )}
            {lintClean && lintReport.nice_to_have.length === 0 && lintReport.acceptable_risk.length === 0 && (
              <div style={{ color: "var(--success)", fontSize: 13 }}>All clear — no lint findings.</div>
            )}
          </div>
        )}

        <div style={{ marginBottom: 16 }}>
          <strong style={{ fontSize: 13 }}>Pre-publish checklist:</strong>
          {CHECKLIST_ITEMS.map((label, i) => (
            <label key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", fontSize: 13, cursor: "pointer" }}>
              <input type="checkbox" checked={checked[i]} onChange={() => toggleCheck(i)} />
              {label}
            </label>
          ))}
        </div>

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="small" onClick={onClose}>Cancel</button>
          <button
            className="primary"
            onClick={handlePublish}
            disabled={!canPublish}
          >
            {publishing ? "Publishing..." : "Confirm Publish"}
          </button>
        </div>
      </div>
    </div>
  );
}
