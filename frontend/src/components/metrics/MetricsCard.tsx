import type { ReactNode } from "react";

type MetricsCardStatus = "good" | "warning" | "critical" | "neutral";

interface MetricsCardProps {
  title: string;
  value: ReactNode;
  status?: MetricsCardStatus;
  subtitle?: string;
  trend?: string;
  sparkline?: number[];
}

export function MetricsCard({
  title,
  value,
  status = "neutral",
  subtitle,
  trend,
  sparkline = [],
}: MetricsCardProps) {
  const max = Math.max(...sparkline, 1);
  const min = Math.min(...sparkline, 0);
  const points = sparkline.map((v, i) => {
    const x = (i / Math.max(1, sparkline.length - 1)) * 100;
    const y = 24 - ((v - min) / Math.max(1, max - min)) * 24;
    return `${x},${y}`;
  }).join(" ");

  return (
    <div className={`metrics-card metrics-card-${status}`}>
      <div className="metrics-card-header">
        <span className="metrics-label">{title}</span>
        {trend && <span className="metrics-trend">{trend}</span>}
      </div>
      <div className="metrics-value">{value}</div>
      {subtitle && <div className="metrics-subtitle">{subtitle}</div>}
      {sparkline.length > 1 && (
        <svg viewBox="0 0 100 24" className="metrics-sparkline">
          <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" />
        </svg>
      )}
    </div>
  );
}

export type { MetricsCardStatus };
