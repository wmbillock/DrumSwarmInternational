import type { CorpsMode } from "../types";

const MODE_CONFIG: Record<CorpsMode, { label: string; color: string; bg: string }> = {
  design_room: { label: "Design Room", color: "#c084fc", bg: "#2d1a4e" },
  show_mode: { label: "Show Mode", color: "#3fb950", bg: "#1a3a2a" },
  rehearsal_mode: { label: "Rehearsal", color: "#67e8f9", bg: "#1a3a4e" },
  judging: { label: "Judging", color: "#d29922", bg: "#2a2a1a" },
  offseason_review: { label: "Offseason", color: "#8b949e", bg: "#2a2a2a" },
};

export function ModeIndicator({ mode }: { mode?: CorpsMode | null }) {
  if (!mode) return null;
  const cfg = MODE_CONFIG[mode];
  return (
    <span
      className="mode-indicator"
      style={{ color: cfg.color, background: cfg.bg, padding: "2px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 600 }}
    >
      {cfg.label}
    </span>
  );
}
