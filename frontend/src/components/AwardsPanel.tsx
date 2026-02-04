import { Panel, Badge } from "../ui";
import type { V1Award } from "../services/v1";

interface AwardsPanelProps {
  title: string;
  awards: V1Award[];
  emptyText?: string;
}

function formatLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

export function AwardsPanel({ title, awards, emptyText = "No achievements yet." }: AwardsPanelProps) {
  return (
    <Panel title={title} className="mt-16">
      {awards.length === 0 ? (
        <div className="text-muted">{emptyText}</div>
      ) : (
        <div className="awards-grid">
          {awards.map((award) => (
            <div key={award.id} className="award-card">
              <div className="award-header">
                <div>
                  <div className="award-title">{award.name}</div>
                  <div className="award-subtitle">{formatLabel(award.category)}</div>
                </div>
                <Badge variant="success">{formatLabel(award.tier)}</Badge>
              </div>
              <div className="award-description">{award.description}</div>
              <div className="award-meta">
                <span className="award-recipient">{award.recipient_name}</span>
                {award.awarded_at && (
                  <span className="award-date">{new Date(award.awarded_at).toLocaleString()}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
