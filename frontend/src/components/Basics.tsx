import { useState } from "react";
import * as v1 from "../services/v1";
import type { BasicsResult } from "../types";

interface Props {
  corpsId: string | null;
}

const CAPTIONS = ["brass", "percussion", "guard", "visual"];

export function Basics({ corpsId }: Props) {
  const [results, setResults] = useState<BasicsResult[]>([]);
  const [running, setRunning] = useState(false);

  const handleRun = async (caption: string) => {
    if (!corpsId) return;
    setRunning(true);
    try {
      const result = (await v1.runBasics(corpsId, caption)) as BasicsResult;
      setResults((prev) => [{ ...result, caption }, ...prev]);
    } finally {
      setRunning(false);
    }
  };

  const handleRunAll = async () => {
    if (!corpsId) return;
    setRunning(true);
    try {
      for (const caption of CAPTIONS) {
        const result = (await v1.runBasics(corpsId, caption)) as BasicsResult;
        setResults((prev) => [{ ...result, caption }, ...prev]);
      }
    } finally {
      setRunning(false);
    }
  };

  if (!corpsId) {
    return (
      <div className="screen">
        <h2>Basics</h2>
        <p className="empty">Select an active show to run basics.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>Basics</h2>
      <p className="subtitle">Per-caption self-improvement cycle</p>
      <div className="basics-controls">
        {CAPTIONS.map((c) => (
          <button key={c} onClick={() => handleRun(c)} disabled={running}>
            {c}
          </button>
        ))}
        <button className="primary" onClick={handleRunAll} disabled={running}>
          Run All
        </button>
      </div>
      <div className="basics-results">
        {results.map((r, i) => (
          <div key={i} className="basics-card">
            <h3>{r.caption}</h3>
            <div className="stat-row">
              <span>Definitions reviewed: {r.definitions_reviewed}</span>
              <span>Improvements suggested: {r.improvements_suggested}</span>
            </div>
            {r.suggestions && r.suggestions.length > 0 && (
              <ul className="suggestions">
                {r.suggestions.map((s, j) => (
                  <li key={j}>{s.suggestion || s.aspect || JSON.stringify(s)}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
