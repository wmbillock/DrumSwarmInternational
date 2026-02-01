/**
 * Performance Explorer — Advanced metrics analysis tool.
 */

import { useState } from "react";
import { Panel } from "../ui";

const MetricOptions = [
  "rep_completed",
  "query_latency",
  "agent_session_started",
  "message_sent",
  "task_latency",
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
    try {
      const metricTypes = selectedMetrics.join(",");
      const periodDays = getPeriodDays();
      const response = await fetch(
        `/api/v1/metrics/timeseries?metric_types=${encodeURIComponent(metricTypes)}&period_days=${periodDays}&granularity=${granularity}`
      );
      const data = await response.json();
      setChartData(data.data || []);
    } catch (error) {
      console.error("Failed to fetch metrics:", error);
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
              <option value="30d">Last 30 Days</option>
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
        </div>
      </Panel>

      <Panel title="Metrics Data" style={{ marginTop: 16 }}>
        {loading && <div className="page-loading">Loading metrics...</div>}

        {!loading && chartData.length === 0 && (
          <p className="empty">
            {selectedMetrics.length === 0
              ? "Select metrics to display"
              : "Click 'Update Chart' to load data"}
          </p>
        )}

        {!loading && chartData.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table className="standings-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  {selectedMetrics.map(m => <th key={m}>{m.replace(/_/g, " ")}</th>)}
                </tr>
              </thead>
              <tbody>
                {chartData.slice(0, 100).map((row, i) => (
                  <tr key={i}>
                    <td className="mono" style={{ fontSize: 11 }}>{row.timestamp}</td>
                    {selectedMetrics.map(m => (
                      <td key={m} className="mono">
                        {typeof row[m] === "number" ? (row[m] as number).toFixed(2) : row[m] || "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {chartData.length > 100 && (
              <p className="hint" style={{ marginTop: 8 }}>Showing 100 of {chartData.length} data points. Export for full data.</p>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
};

export default PerformanceExplorer;
