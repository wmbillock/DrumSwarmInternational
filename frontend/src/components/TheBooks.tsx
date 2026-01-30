interface Props {
  corpsId: string | null;
}

export function TheBooks({ corpsId }: Props) {
  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Books</h2>
        <p className="empty">Select an active show to view budget reports.</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>The Books</h2>
      <p className="subtitle">Token costs, model tier spend per caption/corps</p>
      <div className="books-layout">
        <div className="budget-section">
          <h3>Spend by Caption</h3>
          <div className="budget-bars">
            {["Brass", "Percussion", "Guard", "Visual"].map((caption) => (
              <div key={caption} className="budget-row">
                <span className="caption-name">{caption}</span>
                <div className="budget-bar-track">
                  <div className="budget-bar-fill" style={{ width: "0%" }} />
                </div>
                <span className="budget-value">$0.00</span>
              </div>
            ))}
          </div>
        </div>
        <div className="budget-section">
          <h3>Spend by Model Tier</h3>
          <div className="tier-breakdown">
            {["Opus", "Sonnet", "Haiku"].map((tier) => (
              <div key={tier} className="tier-row">
                <span className="tier-name">{tier}</span>
                <span className="tier-value">$0.00</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
