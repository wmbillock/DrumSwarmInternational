/**
 * Performance Explorer — Advanced metrics analysis tool.
 *
 * Features:
 * - Custom time range selection
 * - Multiple metric comparison
 * - Advanced filtering
 * - Export capabilities
 */

import React, { useState, useEffect } from "react";
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Space,
  Checkbox,
  Empty,
  Spin,
  message,
} from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

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

const PerformanceExplorer: React.FC = () => {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(["rep_completed"]);
  const [timeRange, setTimeRange] = useState<string>("24h");
  const [granularity, setGranularity] = useState<"1m" | "5m" | "1h" | "1d">("1h");
  const [chartData, setChartData] = useState<MetricDataPoint[]>([]);
  const [loading, setLoading] = useState(false);

  const handleMetricToggle = (metric: string) => {
    if (selectedMetrics.includes(metric)) {
      setSelectedMetrics(selectedMetrics.filter((m) => m !== metric));
    } else {
      setSelectedMetrics([...selectedMetrics, metric]);
    }
  };

  const getPeriodDays = () => {
    const map: { [key: string]: number } = { "1h": 0, "6h": 0, "24h": 1, "7d": 7, "30d": 30 };
    return map[timeRange] || 7;
  };

  const fetchMetricsData = async () => {
    if (selectedMetrics.length === 0) {
      setChartData([]);
      return;
    }

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
      message.error("Failed to load metrics data");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    if (chartData.length === 0) {
      message.warning("No data to export");
      return;
    }

    const csv = [
      ["Timestamp", ...selectedMetrics].join(","),
      ...chartData.map((row) =>
        [row.timestamp, ...selectedMetrics.map((m) => row[m] || "")].join(",")
      ),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `metrics-${Date.now()}.csv`;
    a.click();
    message.success("Metrics exported successfully");
  };

  return (
    <div style={{ padding: "24px" }}>
      <h1 style={{ marginBottom: "24px" }}>Performance Explorer</h1>

      <Card style={{ marginBottom: "24px" }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
              Time Range
            </label>
            <Select
              value={timeRange}
              onChange={setTimeRange}
              options={[
                { label: "Last Hour", value: "1h" },
                { label: "Last 6 Hours", value: "6h" },
                { label: "Last 24 Hours", value: "24h" },
                { label: "Last 7 Days", value: "7d" },
                { label: "Last 30 Days", value: "30d" },
              ]}
              style={{ width: "100%" }}
            />
          </Col>

          <Col xs={24} sm={12} md={6}>
            <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
              Granularity
            </label>
            <Select
              value={granularity}
              onChange={setGranularity as any}
              options={[
                { label: "1 Minute", value: "1m" },
                { label: "5 Minutes", value: "5m" },
                { label: "1 Hour", value: "1h" },
                { label: "1 Day", value: "1d" },
              ]}
              style={{ width: "100%" }}
            />
          </Col>

          <Col xs={24} sm={24} md={12}>
            <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
              Metrics
            </label>
            <Space wrap>
              {MetricOptions.map((metric) => (
                <Checkbox
                  key={metric}
                  checked={selectedMetrics.includes(metric)}
                  onChange={() => handleMetricToggle(metric)}
                >
                  {metric.replace(/_/g, " ")}
                </Checkbox>
              ))}
            </Space>
          </Col>

          <Col xs={24}>
            <Space>
              <Button type="primary" onClick={fetchMetricsData} loading={loading}>
                Update Chart
              </Button>
              <Button icon={<DownloadOutlined />} onClick={handleExport} disabled={chartData.length === 0}>
                Export
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading}>
        {selectedMetrics.length > 0 ? (
          <Card title="Performance Metrics">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {selectedMetrics.map((metric, index) => (
                    <Line
                      key={metric}
                      type="monotone"
                      dataKey={metric}
                      stroke={`hsl(${(index * 60) % 360}, 70%, 50%)`}
                      dot={false}
                      isAnimationActive={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Click 'Update Chart' to load data" />
            )}
          </Card>
        ) : (
          <Card>
            <Empty description="Select metrics to display" />
          </Card>
        )}
      </Spin>
    </div>
  );
};

export default PerformanceExplorer;
