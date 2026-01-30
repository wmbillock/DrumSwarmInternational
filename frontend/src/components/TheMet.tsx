import { useState } from "react";
import * as api from "../services/api";
import type { MetronomeResult } from "../types";

interface Props {
  corpsId: string | null;
}

export function TheMet({ corpsId }: Props) {
  const [result, setResult] = useState<MetronomeResult | null>(null);
  const [history, setHistory] = useState<MetronomeResult[]>([]);

  const handleTick = async () => {
    if (!corpsId) return;
    const data = (await api.metronomeTick(corpsId)) as MetronomeResult;
    setResult(data);
    setHistory((prev) => [data, ...prev.slice(0, 49)]);
  };

  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Met</h2>
        <p className="empty">Select an active show to use the metronome dashboard.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>The Met</h2>
      <p className="subtitle">Metronome reclamation log + manual staff override</p>
      <button className="primary" onClick={handleTick}>Run Metronome Tick</button>

      {result && (
        <div className="met-result">
          <div className="stat">
            <span className="stat-value">{result.checked}</span>
            <span className="stat-label">Checked</span>
          </div>
          <div className="stat">
            <span className="stat-value">{result.reclaimed}</span>
            <span className="stat-label">Reclaimed</span>
          </div>
        </div>
      )}

      <h3>History</h3>
      <div className="met-history">
        {history.map((h, i) => (
          <div key={i} className="met-entry">
            Checked {h.checked}, reclaimed {h.reclaimed}
            {h.reclaimed_rep_ids.length > 0 && (
              <span className="reclaimed-ids">
                : {h.reclaimed_rep_ids.map((id) => id.slice(0, 8)).join(", ")}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
