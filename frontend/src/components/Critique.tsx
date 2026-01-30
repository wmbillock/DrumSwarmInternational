import { useState } from "react";
import * as api from "../services/api";
import type { CritiqueResult } from "../types";

interface Props {
  corpsId: string | null;
}

export function Critique({ corpsId }: Props) {
  const [repId, setRepId] = useState("");
  const [result, setResult] = useState<CritiqueResult | null>(null);

  const handleRun = async () => {
    if (!repId.trim() || !corpsId) return;
    const data = (await api.runCritique(repId, corpsId)) as CritiqueResult;
    setResult(data);
  };

  if (!corpsId) {
    return (
      <div className="screen">
        <h2>Critique</h2>
        <p className="empty">Select an active show to view critiques.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>Critique</h2>
      <p className="subtitle">Post-performance judge feedback to staff</p>
      <div className="critique-input">
        <input
          placeholder="Rep ID"
          value={repId}
          onChange={(e) => setRepId(e.target.value)}
        />
        <button onClick={handleRun}>Run Critique</button>
      </div>
      {result && (
        <div className="critique-result">
          <h3>Assessment: {result.overall_assessment}</h3>
          {result.needs_rework && (
            <div className="badge warning">Needs Rework</div>
          )}
          {result.feedbacks.map((f, i) => (
            <div key={i} className="feedback-card">
              <h4>{f.judge_type} - Score: {f.score}</h4>
              {f.strengths.length > 0 && (
                <div className="strengths">
                  <strong>Strengths:</strong> {f.strengths.join(", ")}
                </div>
              )}
              {f.weaknesses.length > 0 && (
                <div className="weaknesses">
                  <strong>Weaknesses:</strong> {f.weaknesses.join(", ")}
                </div>
              )}
              {f.action_items.length > 0 && (
                <div className="actions">
                  <strong>Action Items:</strong>
                  <ul>
                    {f.action_items.map((a, j) => (
                      <li key={j}>{a}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
