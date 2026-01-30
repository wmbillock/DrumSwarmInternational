interface Props {
  corpsId: string | null;
}

export function TheSheets({ corpsId }: Props) {
  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Sheets</h2>
        <p className="empty">Select an active show to view score sheets.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>The Sheets</h2>
      <p className="subtitle">Judge evaluations, composite scores, critique log</p>
      <div className="sheets-layout">
        <div className="sheet-section">
          <h3>Caption Scores</h3>
          <table className="score-table">
            <thead>
              <tr>
                <th>Caption</th>
                <th>Score</th>
                <th>Box</th>
                <th>Feedback</th>
              </tr>
            </thead>
            <tbody>
              <tr className="empty-row">
                <td colSpan={4}>Score data will appear after judge evaluations.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="sheet-section">
          <h3>Composite Score</h3>
          <div className="composite-display">
            <div className="composite-bar" style={{ width: "0%" }} />
            <span>No scores yet</span>
          </div>
        </div>
      </div>
    </div>
  );
}
