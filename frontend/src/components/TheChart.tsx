interface Props {
  corpsId: string | null;
}

export function TheChart({ corpsId }: Props) {
  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Chart</h2>
        <p className="empty">Select an active show to view its drill chart.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>The Chart</h2>
      <p className="subtitle">Timeline visualization of agent execution flow</p>
      <div className="chart-placeholder">
        <p>Drill chart timeline will render agent execution events here.</p>
        <p>Each row represents an agent session, showing:</p>
        <ul>
          <li>Spawn and termination events</li>
          <li>Rep assignments and completions</li>
          <li>Message exchanges</li>
          <li>Escalation events</li>
        </ul>
      </div>
    </div>
  );
}
