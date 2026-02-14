import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import * as v1 from "../services/v1";

interface PerformanceChartProps {
  specId: string;
  accentColor?: string;
  secondaryColor?: string;
}

interface ChartEntry {
  category: string;
  global: number;
  corps: number | null;
}

export function PerformanceChart({ specId, accentColor, secondaryColor }: PerformanceChartProps) {
  const [data, setData] = useState<ChartEntry[]>([]);
  const [specName, setSpecName] = useState("");
  const [loading, setLoading] = useState(true);

  const primary = accentColor || "var(--accent)";
  const secondary = secondaryColor || "var(--warning)";

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    v1.getSpecPerformance(specId, ac.signal)
      .then((perf) => {
        setSpecName(perf.name);
        // Build chart data: one entry per category with global + corps scores
        const categoryMap = new Map<string, ChartEntry>();

        for (const g of perf.global) {
          categoryMap.set(g.task_category, {
            category: g.task_category,
            global: g.avg_score,
            corps: null,
          });
        }
        for (const c of perf.by_corps) {
          const existing = categoryMap.get(c.task_category);
          if (existing) {
            existing.corps = c.avg_score;
          } else {
            categoryMap.set(c.task_category, {
              category: c.task_category,
              global: 0,
              corps: c.avg_score,
            });
          }
        }
        setData(Array.from(categoryMap.values()));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [specId]);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading chart...</p>;
  if (data.length === 0) return <p style={{ color: "var(--text-muted)" }}>No performance data</p>;

  const hasCorpsData = data.some((d) => d.corps !== null);

  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
        {specName && <span style={{ fontWeight: 600 }}>{specName}</span>}
        <span style={{ marginLeft: 12, color: primary }}>
          &#9632; Global
        </span>
        {hasCorpsData && (
          <span style={{ marginLeft: 8, color: secondary }}>
            &#9632; Corps
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="category"
            tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
            axisLine={{ stroke: "var(--border)" }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--border)" }}
          />
          <Tooltip
            contentStyle={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 4,
              fontSize: 12,
            }}
            labelStyle={{ color: "var(--text-primary)" }}
          />
          <Bar dataKey="global" name="Global" fill={primary} radius={[3, 3, 0, 0]} />
          {hasCorpsData && (
            <Bar dataKey="corps" name="Corps" fill={secondary} radius={[3, 3, 0, 0]} />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
