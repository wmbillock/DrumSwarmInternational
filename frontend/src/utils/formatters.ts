/**
 * Systemic display formatters — consistent rendering across all pages.
 */

/** Convert snake_case status to Title Case display: "on_tour" -> "On Tour" */
export function formatStatus(status: string): string {
  return status
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Convert snake_case role to readable: "brass_caption_head" -> "Brass Caption Head" */
export function formatRole(role: string): string {
  return role
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Convert slug to title: "my-cool-show" -> "My Cool Show" */
export function slugToTitle(slug: string): string {
  return slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Format caption name: "brass" -> "Brass", "general_effect" -> "General Effect" */
export function formatCaption(caption: string): string {
  return formatRole(caption);
}

/** Format rehearsal mode: "full_ensemble" -> "Full Ensemble" */
export function formatMode(mode: string): string {
  return formatStatus(mode);
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

/** Trust score color class: green (70+), yellow (40-69), red (<40) */
export function trustColor(score: number): string {
  if (score >= 70) return "trust-high";
  if (score >= 40) return "trust-mid";
  return "trust-low";
}
