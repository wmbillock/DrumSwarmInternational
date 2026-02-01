/**
 * Performance Explorer — Advanced metrics analysis tool.
 *
 * Features:
 * - Custom time range selection
 * - Multiple metric comparison
 * - Advanced filtering
 * - Export capabilities
 */

import React, { useState } from "react";
import {
  Card,
  Row,
  Col,
  DatePicker,
  Select,
  Button,
  Space,
  LineChart as RechartLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Checkbox,
  Empty,
} from "antd";
import { DownloadOutlined } from "@ant-design/icons";

const MetricOptions = [
  "rep_completed",
  "query_latency",
  "agent_session_started",
  "message_sent",
  "task_latency",
];

const PerformanceExplorer: React.FC = () => {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(["rep_completed"]);
  const [timeRange, setTimeRange] = useState<string>("24h");
  const [granularity, setGranularity] = useState<"1m" | "5m" | "1h" | "1d">("1h");

  const handleMetricToggle = (metric: string) => {
    if (selectedMetrics.includes(metric)) {
      setSelectedMetrics(selectedMetrics.filter((m) => m !== metric));
    } else {
      setSelectedMetrics([...selectedMetrics, metric]);
    }
  };

  const handleExport = () => {
    // TODO: Implement export to CSV/JSON
    console.log("Exporting metrics...");
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
              <Button type="primary">Update Chart</Button>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>
                Export
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {selectedMetrics.length > 0 ? (
        <Card title="Performance Metrics">
          <ResponsiveContainer width="100%" height={400}>
            <RechartLineChart data={[]}>
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
            </RechartLineChart>
          </ResponsiveContainer>
        </Card>
      ) : (
        <Card>
          <Empty description="Select metrics to display" />
        </Card>
      )}
    </div>
  );
};

export default PerformanceExplorer;
