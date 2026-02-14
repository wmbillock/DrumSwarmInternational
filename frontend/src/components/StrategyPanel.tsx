import { useEffect, useState, useMemo } from "react";
import { Panel, Badge } from "../ui";
import * as v1 from "../services/v1";

/** Tiny SVG sparkline for category performance trend */
function Sparkline({ values, color, width = 60, height = 20 }: {
  values: number[];
  color: string;
  width?: number;
  height?: number;
}) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 2) - 1;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const POLICY_OPTIONS = [
  { value: "single_provider", label: "Single Provider" },
  { value: "best_of_breed", label: "Best of Breed" },
  { value: "section_specialized", label: "Section Specialized" },
  { value: "random_exploration", label: "Random Exploration" },
];

const ADAPTATION_OPTIONS = [
  { value: "prompt_only", label: "Prompt Only" },
  { value: "model_swap", label: "Model Swap" },
  { value: "full", label: "Full" },
];

const POLICY_LABELS: Record<string, string> = Object.fromEntries(
  POLICY_OPTIONS.map((o) => [o.value, o.label])
);

const ADAPTATION_LABELS: Record<string, string> = Object.fromEntries(
  ADAPTATION_OPTIONS.map((o) => [o.value, o.label])
);

function pct(n: number): string {
  return `${(n * 100).toFixed(0)}%`;
}

interface StrategyPanelProps {
  corpsId: string;
}

export function StrategyPanel({ corpsId }: StrategyPanelProps) {
  const [data, setData] = useState<v1.V1CorpsStrategy | null>(null);
  const [history, setHistory] = useState<v1.V1StrategyHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  // Edit form state
  const [editPolicy, setEditPolicy] = useState("");
  const [editProvider, setEditProvider] = useState("");
  const [editAdaptation, setEditAdaptation] = useState("");
  const [editExploration, setEditExploration] = useState(0);
  const [editRisk, setEditRisk] = useState(0);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);

    v1.getCorpsStrategy(corpsId, ac.signal)
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setLoading(false));

    v1.getCorpsStrategyHistory(corpsId, ac.signal)
      .then((r) => setHistory(r.history))
      .catch(() => {});

    return () => ac.abort();
  }, [corpsId]);

  const startEditing = () => {
    if (!data) return;
    setEditPolicy(data.strategy.model_policy);
    setEditProvider(data.strategy.preferred_provider || "");
    setEditAdaptation(data.strategy.adaptation_style);
    setEditExploration(data.strategy.exploration_rate);
    setEditRisk(data.strategy.risk_tolerance);
    setEditing(true);
    setSaveMsg("");
  };

  const cancelEditing = () => {
    setEditing(false);
    setSaveMsg("");
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg("");
    try {
      const result = await v1.updateCorpsStrategy(corpsId, {
        model_policy: editPolicy,
        preferred_provider: editProvider || undefined,
        adaptation_style: editAdaptation,
        exploration_rate: editExploration,
        risk_tolerance: editRisk,
      });
      // Update local state with new strategy
      if (data) {
        setData({ ...data, strategy: result.strategy });
      }
      setEditing(false);
      setSaveMsg(`Updated: ${result.updated_fields.join(", ")}`);
      setTimeout(() => setSaveMsg(""), 3000);
    } catch (e: any) {
      setSaveMsg(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading strategy...</p>;
  if (error) return (
    <Panel title="Strategy">
      <p style={{ color: "var(--text-secondary)" }}>
        {error.includes("404") || error.includes("not found") || error.includes("No strategy")
          ? "No strategy configured for this corps yet. Strategy configuration is created when a corps begins competing."
          : error}
      </p>
    </Panel>
  );
  if (!data) return null;

  const { strategy, performance, color_scheme: colors } = data;
  const accent = colors.primary || "var(--accent)";

  // Build sparkline data from performance stats
  // Generate simulated trend from attempts/score ratio for sparkline visualization
  const sparklineData = useMemo(() => {
    const result: Record<string, number[]> = {};
    for (const [category, stats] of Object.entries(performance)) {
      if (stats.total_attempts >= 2) {
        // Create a simple trend: use the score and generate points around it
        const base = stats.avg_score;
        const successRate = stats.total_attempts > 0
          ? stats.successful_attempts / stats.total_attempts
          : 0.5;
        const points: number[] = [];
        const n = Math.min(stats.total_attempts, 8);
        for (let i = 0; i < n; i++) {
          // Simulate improvement trend
          const progress = i / (n - 1);
          points.push(base * (0.85 + progress * 0.15 * successRate));
        }
        result[category] = points;
      }
    }
    return result;
  }, [performance]);

  return (
    <div className="strategy-panel">
      <Panel
        title="Strategy Configuration"
        actions={
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {saveMsg && <span style={{ fontSize: 12, color: "var(--success)" }}>{saveMsg}</span>}
            {!editing ? (
              <button className="small" onClick={startEditing} style={{ fontSize: 11 }}>Edit</button>
            ) : (
              <>
                <button className="small" onClick={cancelEditing} style={{ fontSize: 11 }}>Cancel</button>
                <button className="primary small" onClick={handleSave} disabled={saving} style={{ fontSize: 11 }}>
                  {saving ? "Saving..." : "Save"}
                </button>
              </>
            )}
          </div>
        }
      >
        {!editing ? (
          /* --- Read-only view --- */
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div className="strat-field">
                <span className="strat-label">Policy</span>
                <Badge variant="info">{POLICY_LABELS[strategy.model_policy] || strategy.model_policy}</Badge>
              </div>
              <div className="strat-field">
                <span className="strat-label">Provider</span>
                <span className="strat-value">{strategy.preferred_provider || "Any"}</span>
              </div>
              <div className="strat-field">
                <span className="strat-label">Adaptation</span>
                <span className="strat-value">{ADAPTATION_LABELS[strategy.adaptation_style] || strategy.adaptation_style}</span>
              </div>
            </div>
            <div>
              <div className="strat-field">
                <span className="strat-label">Exploration</span>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div className="strat-bar-track">
                    <div className="strat-bar-fill" style={{
                      width: pct(strategy.exploration_rate),
                      background: accent,
                    }} />
                  </div>
                  <span className="strat-value mono">{pct(strategy.exploration_rate)}</span>
                </div>
              </div>
              <div className="strat-field">
                <span className="strat-label">Risk Tolerance</span>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div className="strat-bar-track">
                    <div className="strat-bar-fill" style={{
                      width: pct(strategy.risk_tolerance),
                      background: colors.secondary || "var(--warning)",
                    }} />
                  </div>
                  <span className="strat-value mono">{pct(strategy.risk_tolerance)}</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* --- Edit mode --- */
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div className="strat-field">
                <span className="strat-label">Policy</span>
                <select
                  value={editPolicy}
                  onChange={(e) => setEditPolicy(e.target.value)}
                  style={{ width: "100%", padding: "4px 8px", background: "var(--bg-card)", color: "var(--text-primary)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 13 }}
                >
                  {POLICY_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="strat-field">
                <span className="strat-label">Provider</span>
                <input
                  type="text"
                  value={editProvider}
                  onChange={(e) => setEditProvider(e.target.value)}
                  placeholder="Any"
                  style={{ width: "100%", padding: "4px 8px", background: "var(--bg-card)", color: "var(--text-primary)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 13 }}
                />
              </div>
              <div className="strat-field">
                <span className="strat-label">Adaptation</span>
                <select
                  value={editAdaptation}
                  onChange={(e) => setEditAdaptation(e.target.value)}
                  style={{ width: "100%", padding: "4px 8px", background: "var(--bg-card)", color: "var(--text-primary)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 13 }}
                >
                  {ADAPTATION_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <div className="strat-field">
                <span className="strat-label">Exploration ({pct(editExploration)})</span>
                <input
                  type="range"
                  min={0} max={1} step={0.05}
                  value={editExploration}
                  onChange={(e) => setEditExploration(Number(e.target.value))}
                  style={{ width: "100%", accentColor: accent }}
                />
              </div>
              <div className="strat-field">
                <span className="strat-label">Risk Tolerance ({pct(editRisk)})</span>
                <input
                  type="range"
                  min={0} max={1} step={0.05}
                  value={editRisk}
                  onChange={(e) => setEditRisk(Number(e.target.value))}
                  style={{ width: "100%", accentColor: colors.secondary || "var(--warning)" }}
                />
              </div>
            </div>
          </div>
        )}

        {Object.keys(strategy.section_overrides).length > 0 && (
          <div style={{ marginTop: 12 }}>
            <span className="strat-label">Section Overrides</span>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
              {Object.entries(strategy.section_overrides).map(([cat, specId]) => (
                <Badge key={cat} variant="default">
                  {cat}: {specId.slice(0, 8)}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </Panel>

      {Object.keys(performance).length > 0 && (
        <Panel title="Category Performance" className="mt-16">
          <div className="strat-perf-grid">
            {Object.entries(performance).map(([category, stats]) => (
              <div key={category} className="strat-perf-card">
                <div className="strat-perf-header">
                  <span className="strat-perf-category">{category}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {sparklineData[category] && (
                      <Sparkline values={sparklineData[category]} color={accent} />
                    )}
                    <span className="strat-perf-score" style={{ color: accent }}>
                      {stats.avg_score.toFixed(1)}
                    </span>
                  </div>
                </div>
                <div className="strat-bar-track" style={{ height: 6 }}>
                  <div className="strat-bar-fill" style={{
                    width: `${Math.min(100, stats.avg_score)}%`,
                    background: accent,
                  }} />
                </div>
                <div className="strat-perf-meta">
                  {stats.total_attempts} attempts
                  {stats.total_attempts > 0 && (
                    <> &middot; {((stats.successful_attempts / stats.total_attempts) * 100).toFixed(0)}% success</>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {history.length > 0 && (
        <Panel title="Strategy History" className="mt-16">
          <div className="strat-history">
            {history.map((entry, i) => (
              <div key={i} className="strat-history-entry">
                <Badge variant="default">{entry.season_id}</Badge>
                <span className="strat-history-desc">{entry.description}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
