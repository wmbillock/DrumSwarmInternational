import type { ReactNode } from "react";

export interface TourScheduleEntry {
  competition_id: string;
  show_slug?: string;
  corps_ids: string[];
  corps_performances?: { corps_id: string; show_slug: string }[];
  is_finals?: boolean;
  round?: number;
  status?: string;
}

export interface TourScheduleProps {
  schedule: TourScheduleEntry[];
  statusByCompetition?: Record<string, string | undefined>;
  currentCompetitionId?: string | null;
  renderTitle?: (showSlug: string) => ReactNode;
}

const STATUS_COMPLETE = new Set(["completed", "final", "scored", "closed"]);
const STATUS_CURRENT = new Set(["in_progress", "running", "live", "active"]);
const PALETTE = ["#2563EB", "#16A34A", "#F97316", "#DB2777", "#8B5CF6", "#0EA5E9", "#D97706"];

export function TourSchedule({
  schedule,
  statusByCompetition = {},
  currentCompetitionId,
  renderTitle,
}: TourScheduleProps) {
  const colorByShow: Record<string, string> = {};
  let paletteIndex = 0;

  const normalized = schedule.map((entry) => {
    // Derive show slugs from corps_performances or fall back to show_slug
    const shows = entry.corps_performances
      ? [...new Set(entry.corps_performances.map((p) => p.show_slug))]
      : entry.show_slug ? [entry.show_slug] : [];
    const primaryShow = shows[0] || "unknown";
    if (!colorByShow[primaryShow]) {
      colorByShow[primaryShow] = PALETTE[paletteIndex % PALETTE.length];
      paletteIndex += 1;
    }
    const status = statusByCompetition[entry.competition_id] || entry.status || "scheduled";
    const state = currentCompetitionId === entry.competition_id
      ? "current"
      : STATUS_COMPLETE.has(status)
        ? "completed"
        : STATUS_CURRENT.has(status)
          ? "current"
          : "upcoming";
    return {
      ...entry,
      shows,
      status,
      state,
      color: colorByShow[primaryShow],
    };
  });

  const current = normalized.find((entry) => entry.state === "current") || null;
  const history = normalized.filter((entry) => entry.state === "completed");
  const upcoming = normalized.filter((entry) => entry.state === "upcoming");

  const renderRow = (entry: typeof normalized[number]) => (
    <div
      key={entry.competition_id}
      style={{
        display: "grid",
        gridTemplateColumns: "12px 1fr auto",
        gap: 12,
        alignItems: "center",
        padding: "10px 0",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: 999,
          background: entry.color,
        }}
      />
      <div>
        <div style={{ fontWeight: 600 }}>
          {entry.is_finals
            ? "Finals"
            : entry.shows.map((s: string, i: number) => (
                <span key={s}>{i > 0 && ", "}{renderTitle ? renderTitle(s) : s}</span>
              ))}
        </div>
        <div className="text-muted" style={{ fontSize: 12 }}>{entry.competition_id}</div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase" }}>{entry.state}</div>
        <div style={{ fontSize: 12 }}>{entry.corps_ids.length} corps</div>
      </div>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h4 style={{ marginBottom: 8 }}>Current Round</h4>
        {current ? renderRow(current) : <p className="empty">No current round.</p>}
      </div>
      <div>
        <h4 style={{ marginBottom: 8 }}>History</h4>
        {history.length === 0 ? <p className="empty">No completed rounds yet.</p> : history.map(renderRow)}
      </div>
      <div>
        <h4 style={{ marginBottom: 8 }}>Upcoming</h4>
        {upcoming.length === 0 ? <p className="empty">No upcoming rounds.</p> : upcoming.map(renderRow)}
      </div>
    </div>
  );
}
