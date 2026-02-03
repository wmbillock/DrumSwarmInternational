import { Badge } from "../../ui";

interface LeaderboardRow {
  id: string;
  rank: number;
  label: string;
  value?: string;
  status?: "good" | "warning" | "critical" | "neutral";
}

interface LeaderboardProps {
  title?: string;
  rows: LeaderboardRow[];
  onRowClick?: (row: LeaderboardRow) => void;
}

const medalForRank = (rank: number) => {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return `#${rank}`;
};

const statusVariant = (status?: string) => {
  switch (status) {
    case "good":
      return "success";
    case "warning":
      return "warning";
    case "critical":
      return "danger";
    default:
      return "default";
  }
};

export function Leaderboard({ title, rows, onRowClick }: LeaderboardProps) {
  return (
    <div className="leaderboard">
      {title && <div className="metrics-label" style={{ marginBottom: 8 }}>{title}</div>}
      <div className="leaderboard-list">
        {rows.map(row => (
          <div
            key={row.id}
            className={`leaderboard-row ${onRowClick ? "clickable" : ""}`}
            onClick={() => onRowClick?.(row)}
          >
            <span className="leaderboard-rank">{medalForRank(row.rank)}</span>
            <span className="leaderboard-label">{row.label}</span>
            {row.value && <span className="leaderboard-value">{row.value}</span>}
            {row.status && <Badge variant={statusVariant(row.status)}>{row.status}</Badge>}
          </div>
        ))}
      </div>
    </div>
  );
}
