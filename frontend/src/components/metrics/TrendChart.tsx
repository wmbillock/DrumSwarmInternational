import type { ReactNode } from "react";

export interface TrendPoint {
  x: number;
  y: number;
}

export interface TrendSeries {
  id: string;
  label: string;
  color?: string;
  points: TrendPoint[];
}

interface TrendChartProps {
  title?: ReactNode;
  series: TrendSeries[];
  height?: number;
}

export function TrendChart({ title, series, height = 160 }: TrendChartProps) {
  const allPoints = series.flatMap(s => s.points);
  const xs = allPoints.map(p => p.x);
  const ys = allPoints.map(p => p.y);
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 1);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 1);

  const scaleX = (x: number) => ((x - minX) / Math.max(1, maxX - minX)) * 100;
  const scaleY = (y: number) => 100 - ((y - minY) / Math.max(1, maxY - minY)) * 100;

  return (
    <div className="trend-chart">
      {title && <div className="metrics-label" style={{ marginBottom: 8 }}>{title}</div>}
      <svg viewBox={`0 0 100 100`} style={{ width: "100%", height }}>
        {series.map(s => {
          const path = s.points.map((p, idx) => {
            const x = scaleX(p.x);
            const y = scaleY(p.y);
            return `${idx === 0 ? "M" : "L"} ${x} ${y}`;
          }).join(" ");
          return (
            <path
              key={s.id}
              d={path}
              fill="none"
              stroke={s.color || "currentColor"}
              strokeWidth={2}
            />
          );
        })}
      </svg>
    </div>
  );
}
