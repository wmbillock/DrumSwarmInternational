import { useState, useEffect } from "react";
import { Panel, Badge } from "../ui";
import { TrendChart } from "./metrics";
import type { TrendSeries } from "./metrics/TrendChart";
import * as v1 from "../services/v1";
import type { V1ModelSpec } from "../services/v1";

const COLORS = [
  "var(--accent)",
  "var(--success)",
  "var(--warning)",
  "var(--danger)",
  "#a78bfa",
  "#f472b6",
];

interface SpecComparisonChartProps {
  specs?: V1ModelSpec[];
  maxSpecs?: number;
}

export function SpecComparisonChart({ specs: propSpecs, maxSpecs = 3 }: SpecComparisonChartProps) {
  const [allSpecs, setAllSpecs] = useState<V1ModelSpec[]>(propSpecs || []);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(!propSpecs);

  useEffect(() => {
    if (propSpecs) {
      setAllSpecs(propSpecs);
      return;
    }
    v1.listModelSpecs()
      .then((specs) => {
        const list = Array.isArray(specs) ? specs : [];
        setAllSpecs(list);
        // Auto-select first N active specs
        const active = list.filter((s) => s.is_active).slice(0, maxSpecs);
        setSelected(active.map((s) => s.id));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [propSpecs, maxSpecs]);

  const toggleSpec = (specId: string) => {
    setSelected((prev) => {
      if (prev.includes(specId)) return prev.filter((s) => s !== specId);
      if (prev.length >= maxSpecs) return prev;
      return [...prev, specId];
    });
  };

  // Build comparison data: one series per spec, points = category avg scores
  const categories = Array.from(
    new Set(allSpecs.flatMap((s) => Object.keys(s.performance)))
  ).sort();

  const series: TrendSeries[] = selected.map((specId, idx) => {
    const spec = allSpecs.find((s) => s.id === specId);
    if (!spec) return { id: specId, label: specId, points: [], color: COLORS[idx % COLORS.length] };
    return {
      id: spec.id,
      label: spec.name,
      color: COLORS[idx % COLORS.length],
      points: categories.map((cat, i) => ({
        x: i,
        y: spec.performance[cat]?.avg_score || 0,
      })),
    };
  });

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading specs...</p>;
  if (allSpecs.length === 0) return null;

  return (
    <Panel title="Model Spec Comparison">
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {allSpecs.map((spec) => (
          <button
            key={spec.id}
            className={selected.includes(spec.id) ? "primary small" : "secondary small"}
            onClick={() => toggleSpec(spec.id)}
            style={{ fontSize: 11, padding: "3px 8px" }}
            disabled={!selected.includes(spec.id) && selected.length >= maxSpecs}
          >
            {spec.name}
            {!spec.is_active && " (inactive)"}
          </button>
        ))}
      </div>

      {selected.length > 0 && categories.length > 0 ? (
        <>
          <TrendChart series={series} height={180} />
          <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap" }}>
            {series.map((s) => (
              <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
                <span style={{ width: 12, height: 3, background: s.color, display: "inline-block", borderRadius: 2 }} />
                <span>{s.label}</span>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
            {categories.map((cat, i) => (
              <Badge key={cat} variant="default">
                {i + 1}: {cat}
              </Badge>
            ))}
          </div>
        </>
      ) : (
        <p className="text-muted">Select up to {maxSpecs} specs to compare.</p>
      )}
    </Panel>
  );
}
