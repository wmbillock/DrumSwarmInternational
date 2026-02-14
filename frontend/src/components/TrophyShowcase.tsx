import type { AwardsSummary } from "../types";
import { Badge } from "../ui";

const TIER_COLORS: Record<string, string> = {
  bronze: "#CD7F32",
  silver: "#C0C0C0",
  gold: "#FFD700",
  platinum: "#E5E4E2",
  diamond: "#B9F2FF",
};

const TIER_ORDER = ["bronze", "silver", "gold", "platinum", "diamond"];

const CATEGORY_LABELS: Record<string, string> = {
  brass_excellence: "Brass Excellence",
  percussion_mastery: "Percussion Mastery",
  guard_artistry: "Guard Artistry",
  visual_innovation: "Visual Innovation",
  general_effect: "General Effect",
  endurance: "Endurance",
  velocity: "Velocity",
  collaboration: "Collaboration",
  reliability: "Reliability",
  creativity: "Creativity",
  mentorship: "Mentorship",
  comeback: "Comeback",
};

function TierDistributionBar({ byTier }: { byTier: Record<string, number> }) {
  const total = Object.values(byTier).reduce((s, n) => s + n, 0);
  if (total === 0) {
    return (
      <div className="trophy-tier-bar">
        <div style={{ color: "var(--text-secondary)", fontSize: 12, padding: 8 }}>
          No awards earned yet
        </div>
      </div>
    );
  }

  return (
    <div className="trophy-tier-bar">
      <svg width="100%" height="32" style={{ display: "block" }}>
        {TIER_ORDER.reduce<{ offset: number; elements: JSX.Element[] }>(
          (acc, tier) => {
            const count = byTier[tier] || 0;
            if (count === 0) return acc;
            const pct = (count / total) * 100;
            const el = (
              <g key={tier}>
                <rect
                  x={`${acc.offset}%`}
                  y="0"
                  width={`${pct}%`}
                  height="32"
                  fill={TIER_COLORS[tier]}
                  rx="0"
                />
                {pct > 8 && (
                  <text
                    x={`${acc.offset + pct / 2}%`}
                    y="20"
                    textAnchor="middle"
                    fontSize="11"
                    fontFamily="JetBrains Mono, monospace"
                    fill={tier === "diamond" || tier === "silver" || tier === "platinum" ? "#111" : "#fff"}
                  >
                    {count}
                  </text>
                )}
              </g>
            );
            return { offset: acc.offset + pct, elements: [...acc.elements, el] };
          },
          { offset: 0, elements: [] }
        ).elements}
      </svg>
      <div style={{ display: "flex", gap: 12, marginTop: 6, flexWrap: "wrap" }}>
        {TIER_ORDER.map((tier) => (
          <span key={tier} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11 }}>
            <span
              style={{
                width: 10,
                height: 10,
                background: TIER_COLORS[tier],
                display: "inline-block",
                border: "1px solid rgba(255,255,255,0.15)",
              }}
            />
            <span style={{ textTransform: "capitalize" }}>{tier}</span>
            <span style={{ color: "var(--text-secondary)" }}>({byTier[tier] || 0})</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function TierProgress({ tiers }: { tiers: Record<string, number> }) {
  return (
    <div style={{ display: "flex", gap: 3, marginTop: 4 }}>
      {TIER_ORDER.map((tier) => {
        const count = tiers[tier] || 0;
        return (
          <div
            key={tier}
            title={`${tier}: ${count}`}
            style={{
              width: 18,
              height: 18,
              border: `2px solid ${count > 0 ? TIER_COLORS[tier] : "var(--border)"}`,
              background: count > 0 ? TIER_COLORS[tier] : "transparent",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 9,
              fontWeight: 700,
              color: count > 0 && (tier === "diamond" || tier === "silver" || tier === "platinum") ? "#111" : count > 0 ? "#fff" : "var(--text-secondary)",
            }}
          >
            {count > 0 ? count : ""}
          </div>
        );
      })}
    </div>
  );
}

function CategoryGrid({ byCategory }: { byCategory: AwardsSummary["by_category"] }) {
  const categories = Object.keys(CATEGORY_LABELS);

  return (
    <div className="trophy-category-grid">
      {categories.map((cat) => {
        const data = byCategory[cat] || { total: 0, tiers: {}, highest_tier: null };
        return (
          <div key={cat} className="trophy-category-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>
                {CATEGORY_LABELS[cat]}
              </span>
              {data.highest_tier && (
                <Badge variant={data.highest_tier === "diamond" || data.highest_tier === "gold" ? "success" : "default"}>
                  {data.highest_tier}
                </Badge>
              )}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
              {data.total} award{data.total !== 1 ? "s" : ""}
            </div>
            <TierProgress tiers={data.tiers} />
          </div>
        );
      })}
    </div>
  );
}

function RecentUnlocks({ unlocks }: { unlocks: AwardsSummary["recent_unlocks"] }) {
  if (unlocks.length === 0) {
    return <p className="empty">No recent unlocks</p>;
  }

  return (
    <div className="trophy-timeline">
      {unlocks.slice(0, 10).map((u, i) => (
        <div key={i} className="trophy-unlock-row">
          <span
            className="trophy-unlock-tier"
            style={{ color: TIER_COLORS[u.tier] || "var(--text-secondary)" }}
          >
            {u.tier.toUpperCase()}
          </span>
          <div>
            <span className="trophy-unlock-name">{u.name}</span>
            <div className="trophy-unlock-meta">
              {u.recipient_name} &middot; {CATEGORY_LABELS[u.category] || u.category}
              {u.awarded_at && (
                <> &middot; {new Date(u.awarded_at).toLocaleDateString()}</>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function TopRecipients({ recipients }: { recipients: AwardsSummary["top_recipients"] }) {
  if (recipients.length === 0) {
    return <p className="empty">No award recipients</p>;
  }

  return (
    <div className="leaderboard-list">
      {recipients.map((r, i) => (
        <div key={i} className="leaderboard-row">
          <span className="leaderboard-rank">#{i + 1}</span>
          <span className="leaderboard-label">{r.name}</span>
          <span className="leaderboard-value">{r.count} awards</span>
          <span />
        </div>
      ))}
    </div>
  );
}

interface TrophyShowcaseProps {
  summary: AwardsSummary;
  loading?: boolean;
}

export function TrophyShowcase({ summary, loading }: TrophyShowcaseProps) {
  if (loading) {
    return <p style={{ padding: 16 }}>Loading trophy data...</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <TierDistributionBar byTier={summary.by_tier} />
      <CategoryGrid byCategory={summary.by_category} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <h4 style={{ margin: "0 0 8px", fontSize: 13, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Recent Unlocks
          </h4>
          <RecentUnlocks unlocks={summary.recent_unlocks} />
        </div>
        <div>
          <h4 style={{ margin: "0 0 8px", fontSize: 13, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Top Recipients
          </h4>
          <TopRecipients recipients={summary.top_recipients} />
        </div>
      </div>
    </div>
  );
}
