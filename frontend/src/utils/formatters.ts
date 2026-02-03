/**
 * Systemic display formatters — consistent rendering across all pages.
 */

const KNOWN_STATUS = new Set([
  "initializing",
  "winter_camps",
  "on_tour",
  "ready_for_contest",
  "completed",
  "disbanded",
  "commissioned",
  "active",
  "contending",
  "stagnant",
  "archived",
  "in_progress",
  "pending",
  "retired",
  "ready",
  "scored",
  "touring",
  "planning",
  "draft",
  "published",
  "approved",
  "rejected",
  "needs_review",
  "closed",
]);

const KNOWN_MODES = new Set([
  "design_room",
  "show_mode",
  "rehearsal_mode",
  "judging",
  "offseason_review",
  "basics",
  "sectionals",
  "full_ensemble",
  "run_through",
]);

const KNOWN_CAPTIONS = new Set([
  "general_effect",
  "visual",
  "guard",
  "brass",
  "percussion",
  "ensemble_technique",
]);

const KNOWN_ROLES = new Set([
  "executive_director",
  "program_coordinator",
  "drum_major",
  "drill_writer",
  "music_writer",
  "choreographer",
  "brass_caption_head",
  "percussion_caption_head",
  "guard_caption_head",
  "visual_caption_head",
  "brass_tech",
  "percussion_tech",
  "front_ensemble_tech",
  "guard_tech",
  "visual_tech",
  "timing_judge",
  "performer",
]);

function warnUnknown(kind: string, value: string) {
  if (value && typeof value === "string") {
    console.warn(`[formatters] Unknown ${kind}:`, value);
  }
}

function formatSnake(value: string): string {
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Convert snake_case status to Title Case display: "on_tour" -> "On Tour" */
export function formatStatus(status: string): string {
  if (!status) return status;
  if (!KNOWN_STATUS.has(status)) warnUnknown("status", status);
  return formatSnake(status);
}

/** Convert snake_case role to readable: "brass_caption_head" -> "Brass Caption Head" */
export function formatRole(role: string): string {
  if (!role) return role;
  if (!KNOWN_ROLES.has(role)) warnUnknown("role", role);
  return formatSnake(role);
}

/** Convert slug to title: "my-cool-show" -> "My Cool Show" */
export function slugToTitle(slug: string): string {
  if (!slug) return slug;
  return slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Format caption name: "brass" -> "Brass", "general_effect" -> "General Effect" */
export function formatCaption(caption: string): string {
  if (!caption) return caption;
  if (!KNOWN_CAPTIONS.has(caption)) warnUnknown("caption", caption);
  return formatSnake(caption);
}

/** Format rehearsal mode: "full_ensemble" -> "Full Ensemble" */
export function formatMode(mode: string): string {
  if (!mode) return mode;
  if (!KNOWN_MODES.has(mode)) warnUnknown("mode", mode);
  return formatSnake(mode);
}

/** Format a number as currency: 1234.5 -> "$1,234.50" */
export function formatCurrency(amount: number): string {
  return `$${amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Format a number with commas: 1234567 -> "1,234,567" */
export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

/** Relative time: "3d ago", "2h ago", "just now" */
export function relativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function formatTimestamp(isoDate?: string): { label: string; title: string } {
  if (!isoDate) return { label: "", title: "" };
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return { label: isoDate, title: isoDate };
  }
  return { label: relativeTime(isoDate), title: date.toLocaleString() };
}

/** Trust score color class: green (70+), yellow (40-69), red (<40) */
export function trustColor(score: number): string {
  if (score >= 70) return "trust-high";
  if (score >= 40) return "trust-mid";
  return "trust-low";
}

export type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";

export function badgeForCorpsStatus(status: string): BadgeVariant {
  switch (status) {
    case "on_tour":
      return "success";
    case "winter_camps":
      return "warning";
    case "completed":
      return "info";
    case "disbanded":
      return "danger";
    case "initializing":
      return "default";
    default:
      return "default";
  }
}

export function badgeForShowStatus(status: string): BadgeVariant {
  switch (status) {
    case "draft":
      return "default";
    case "active":
      return "success";
    case "needs_review":
      return "warning";
    case "approved":
      return "success";
    case "completed":
      return "info";
    case "published":
      return "info";
    case "archived":
      return "default";
    default:
      return "default";
  }
}

export function badgeForRunStatus(status: string): BadgeVariant {
  switch (status) {
    case "running":
      return "warning";
    case "completed":
      return "success";
    case "failed":
      return "danger";
    default:
      return "default";
  }
}
