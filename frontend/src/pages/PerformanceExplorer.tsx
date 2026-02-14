/**
 * Performance Explorer — Advanced metrics analysis tool.
 */

import { useMemo, useState } from "react";
import { Panel, DataTable } from "../ui";
import { TrendChart } from "../components/metrics";
import "../styles/Metrics.css";
import * as v1 from "../services/v1";

const MetricOptions = [
  "rep_completed",
  "query_latency",
  "agent_session_started",
  "message_sent",
  "task_latency",
  "model_performance",
];

interface MetricDataPoint {
  timestamp: string;
  [key: string]: string | number;
}

const PerformanceExplorer = () => {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(["rep_completed"]);
  const [timeRange, setTimeRange] = useState("24h");
  const [granularity, setGranularity] = useState("1h");
  const [chartData, setChartData] = useState<MetricDataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetched, setFetched] = useState(false);

  const handleMetricToggle = (metric: string) => {
    if (selectedMetrics.includes(metric)) {
      setSelectedMetrics(selectedMetrics.filter(m => m !== metric));
    } else {
      setSelectedMetrics([...selectedMetrics, metric]);
    }
  };

  const getPeriodDays = () => {
    const map: Record<string, number> = { "1h": 0, "6h": 0, "24h": 1, "7d": 7, "30d": 30 };
    return map[timeRange] || 7;
  };

  const fetchMetricsData = async () => {
    if (selectedMetrics.length === 0) { setChartData([]); return; }
    setLoading(true);
    setError(null);
    try {
      const periodDays = getPeriodDays();
      const data = await v1.getMetricsSeries(selectedMetrics, periodDays, granularity);
      setChartData(data.data || []);
      setFetched(true);
    } catch (error) {
      setError("Failed to fetch metrics");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    if (chartData.length === 0) return;
    const csv = [
      ["Timestamp", ...selectedMetrics].join(","),
      ...chartData.map(row =>
        [row.timestamp, ...selectedMetrics.map(m => row[m] || "")].join(",")
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `metrics-${Date.now()}.csv`;
    a.click();
  };

  const handleExportJson = () => {
    if (chartData.length === 0) return;
    const blob = new Blob([JSON.stringify(chartData, null, 2)], { type: "application/json" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `metrics-${Date.now()}.json`;
    a.click();
  };

  const series = useMemo(() => {
    return selectedMetrics.map(metric => ({
      id: metric,
      label: metric,
      points: chartData.map((row, idx) => ({
        x: idx,
        y: Number(row[metric] || 0),
      })),
    }));
  }, [chartData, selectedMetrics]);

  return (
    <div className="page-content">
      <h2 className="page-title">Performance Explorer</h2>

      <Panel title="Controls">
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
          <div>
            <label className="form-label" style={{ display: "block", marginBottom: 4, fontSize: 12, color: "var(--text-secondary)" }}>
              Time Range
            </label>
            <select className="library-filter" value={timeRange} onChange={e => setTimeRange(e.target.value)}>
              <option value="1h">Last Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ display: "block", marginBottom: 4, fontSize: 12, color: "var(--text-secondary)" }}>
              Granularity
            </label>
            <select className="library-filter" value={granularity} onChange={e => setGranularity(e.target.value)}>
              <option value="1m">1 Minute</option>
              <option value="5m">5 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="1d">1 Day</option>
            </select>
          </div>

          <div style={{ flex: 1 }}>
            <label className="form-label" style={{ display: "block", marginBottom: 4, fontSize: 12, color: "var(--text-secondary)" }}>
              Metrics
            </label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {MetricOptions.map(metric => (
                <label key={metric} style={{ display: "flex", gap: 4, alignItems: "center", fontSize: 12, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={selectedMetrics.includes(metric)}
                    onChange={() => handleMetricToggle(metric)}
                  />
                  {metric.replace(/_/g, " ")}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button className="primary" onClick={fetchMetricsData} disabled={loading}>
            {loading ? "Loading..." : "Update Chart"}
          </button>
          <button className="small" onClick={handleExport} disabled={chartData.length === 0}>
            Export CSV
          </button>
          <button className="small" onClick={handleExportJson} disabled={chartData.length === 0}>
            Export JSON
          </button>
        </div>
      </Panel>

      {error && <div className="error-banner">{error}</div>}

      {chartData.length > 0 && (
        <Panel title="Trend Chart" style={{ marginTop: 16 }}>
          <TrendChart series={series} />
        </Panel>
      )}

      <Panel title="Metrics Data" style={{ marginTop: 16 }}>
        {loading && <div className="page-loading">Loading metrics...</div>}

        {!loading && chartData.length === 0 && (
          <p className="empty">
            {selectedMetrics.length === 0
              ? "Select metrics to display"
              : fetched
              ? "No metrics data recorded for the selected time range. Run some agent sessions to generate metrics."
              : "Click 'Update Chart' to load data"}
          </p>
        )}

        {!loading && chartData.length > 0 && (
          <>
            <DataTable<Record<string, unknown>>
              columns={[
                { key: "timestamp", label: "Timestamp", render: (v) => <span className="mono" style={{ fontSize: 11 }}>{String(v)}</span> },
                ...selectedMetrics.map((m) => ({
                  key: m,
                  label: m.replace(/_/g, " "),
                  render: (v: unknown) => (
                    <span className="mono">
                      {typeof v === "number" ? v.toFixed(2) : (v as string) || "—"}
                    </span>
                  ),
                })),
              ]}
              data={chartData.slice(0, 100) as Record<string, unknown>[]}
              emptyMessage="No metrics data."
            />
            {chartData.length > 100 && (
              <p className="hint" style={{ marginTop: 8 }}>Showing 100 of {chartData.length} data points. Export for full data.</p>
            )}
          </>
        )}
      </Panel>
    </div>
  );
};

export default PerformanceExplorer;
