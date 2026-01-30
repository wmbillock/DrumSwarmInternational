interface Props {
  corpsId: string | null;
}

export function TheStand({ corpsId }: Props) {
  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Stand</h2>
        <p className="empty">Select an active show to browse artifacts.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>The Stand</h2>
      <p className="subtitle">Artifacts and deliverables browser</p>
      <div className="stand-layout">
        <p className="empty">
          Completed deliverables from the Souvie Crew will appear here.
        </p>
      </div>
    </div>
  );
}
