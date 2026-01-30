import { useState } from "react";
import type { Rep } from "../types";

interface Props {
  corpsId: string | null;
}

const COLUMNS: Rep["status"][] = [
  "pending", "assigned", "in_progress", "review", "completed", "failed",
];

const COLUMN_LABELS: Record<string, string> = {
  pending: "Pending",
  assigned: "Assigned",
  in_progress: "In Progress",
  review: "Review",
  completed: "Completed",
  failed: "Failed",
};

export function TheReps({ corpsId }: Props) {
  const [reps] = useState<Rep[]>([]);

  // In a real app, this would fetch all reps for the corps
  // For now, we show the kanban layout structure

  if (!corpsId) {
    return (
      <div className="screen">
        <h2>The Reps</h2>
        <p className="empty">Select an active show to view its rep board.</p>
      </div>
    );
  }

  const grouped = COLUMNS.reduce(
    (acc, col) => {
      acc[col] = reps.filter((r) => r.status === col);
      return acc;
    },
    {} as Record<string, Rep[]>
  );

  return (
    <div className="screen">
      <h2>The Reps</h2>
      <p className="subtitle">Kanban board: rep workflow status</p>
      <div className="kanban">
        {COLUMNS.map((col) => (
          <div key={col} className={`kanban-column status-${col}`}>
            <h3>
              {COLUMN_LABELS[col]}{" "}
              <span className="count">{grouped[col]?.length || 0}</span>
            </h3>
            <div className="kanban-cards">
              {grouped[col]?.map((rep) => (
                <div key={rep.id} className="kanban-card">
                  <div className="rep-id">{rep.id.slice(0, 8)}</div>
                  {rep.assigned_to && (
                    <div className="rep-agent">{rep.assigned_to.slice(0, 8)}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
