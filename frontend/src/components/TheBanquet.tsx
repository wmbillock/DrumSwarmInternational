import { useState } from "react";
import * as v1 from "../services/v1";
import type { BanquetReport } from "../types";

interface Props {
  corpsId: string | null;
}

export function TheBanquet({ corpsId }: Props) {
  const [report, setReport] = useState<BanquetReport | null>(null);

  const handleGenerate = async () => {
    if (!corpsId) return;
    const data = (await v1.getBanquet(corpsId)) as BanquetReport;
    setReport(data);
  };

  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Banquet</h2>
        <p className="empty">Select an active show to generate a retrospective.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>The Banquet</h2>
      <p className="subtitle">End-of-project retrospective and season report</p>
      <button className="primary" onClick={handleGenerate}>
        Generate Season Report
      </button>

      {report && (
        <div className="banquet-report">
          <div className="stat-grid">
            <div className="stat">
              <span className="stat-value">{report.total_reps}</span>
              <span className="stat-label">Total Reps</span>
            </div>
            <div className="stat">
              <span className="stat-value">{report.completed_reps}</span>
              <span className="stat-label">Completed</span>
            </div>
            <div className="stat">
              <span className="stat-value">{report.failed_reps}</span>
              <span className="stat-label">Failed</span>
            </div>
            <div className="stat">
              <span className="stat-value">{report.average_score.toFixed(1)}</span>
              <span className="stat-label">Avg Score</span>
            </div>
          </div>
          {report.top_caption && (
            <p>Top caption: <strong>{report.top_caption}</strong></p>
          )}
          {report.what_worked.length > 0 && (
            <div className="section">
              <h3>What Worked</h3>
              <ul>{report.what_worked.map((w, i) => <li key={i}>{w}</li>)}</ul>
            </div>
          )}
          {report.what_failed.length > 0 && (
            <div className="section">
              <h3>What Failed</h3>
              <ul>{report.what_failed.map((w, i) => <li key={i}>{w}</li>)}</ul>
            </div>
          )}
          {report.improvements.length > 0 && (
            <div className="section">
              <h3>Improvements</h3>
              <ul>{report.improvements.map((w, i) => <li key={i}>{w}</li>)}</ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
