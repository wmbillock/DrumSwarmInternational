/**
 * Metrics Dashboard — Live visualization of swarm performance metrics.
 *
 * Displays:
 * - Real-time metrics summary cards
 * - Performance trend sparklines
 * - System health indicators
 * - Live event feed
 *
 * Updates via WebSocket or polling (configurable).
 */

import React, { useState, useEffect, useCallback } from "react";
import { Card, Row, Col, Spin, Alert, Button, Space, Select, DatePicker } from "antd";
import { LineChart, Line, AreaChart, Area, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import dayjs, { Dayjs } from "dayjs";

interface MetricsData {
  timestamp: string;
  reps_completed: number;
  reps_total: number;
  avg_rep_duration: number;
  success_rate: number;
  query_latency_p95: number;
  agent_utilization: number;
  message_throughput: number;
}

interface TrendPoint {
  timestamp: string;
  value: number;
}

interface DashboardState {
  metrics: MetricsData | null;
  trends: {
    completion_rate: TrendPoint[];
    latency: TrendPoint[];
    throughput: TrendPoint[];
  };
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

const MetricCard: React.FC<{
  title: string;
  value: string | number;
  unit?: string;
  trend?: string;
  status: "good" | "warning" | "critical";
}> = ({ title, value, unit, trend, status }) => {
  const statusColors = {
    good: "#52c41a",
    warning: "#faad14",
    critical: "#f5222d",
  };

  return (
    <Card
      style={{
        borderLeft: `4px solid ${statusColors[status]}`,
      }}
    >
      <div style={{ marginBottom: "8px", fontSize: "12px", color: "#888" }}>
        {title}
      </div>
      <div style={{ fontSize: "24px", fontWeight: "bold", marginBottom: "4px" }}>
        {value}{unit ? ` ${unit}` : ""}
      </div>
      {trend && <div style={{ fontSize: "12px", color: statusColors[status] }}>{trend}</div>}
    </Card>
  );
};

const MetricsDashboard: React.FC = () => {
  const [state, setState] = useState<DashboardState>({
    metrics: null,
    trends: {
      completion_rate: [],
      latency: [],
      throughput: [],
    },
    loading: true,
    error: null,
    lastUpdated: null,
  });

  const [timeRange, setTimeRange] = useState<"1h" | "6h" | "24h" | "7d">("6h");
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);

  // Fetch metrics from API
  const fetchMetrics = useCallback(async () => {
    try {
      // TODO: Implement actual API call
      // const response = await fetch(`/api/v1/metrics/dashboard?range=${timeRange}`);
      // const data = await response.json();

      // Placeholder data
      setState((prev) => ({
        ...prev,
        metrics: {
          timestamp: new Date().toISOString(),
          reps_completed: 245,
          reps_total: 300,
          avg_rep_duration: 45.2,
          success_rate: 0.95,
          query_latency_p95: 125.5,
          agent_utilization: 0.78,
          message_throughput: 1250,
        },
        loading: false,
        error: null,
        lastUpdated: new Date().toLocaleTimeString(),
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: `Failed to fetch metrics: ${error}`,
      }));
    }
  }, [timeRange]);

  // Fetch trends from API
  const fetchTrends = useCallback(async () => {
    try {
      // TODO: Implement actual API call
      // const response = await fetch(`/api/v1/metrics/trends?metric_type=rep_completed&period=${timeRange}`);
      // const data = await response.json();

      // Placeholder data
      const now = new Date();
      const trends = [];
      for (let i = 24; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 60 * 60 * 1000);
        trends.push({
          timestamp: time.toLocaleTimeString(),
          value: Math.random() * 100 + 50,
        });
      }

      setState((prev) => ({
        ...prev,
        trends: {
          completion_rate: trends,
          latency: trends.map((t) => ({ ...t, value: Math.random() * 200 + 50 })),
          throughput: trends.map((t) => ({ ...t, value: Math.random() * 500 + 1000 })),
        },
      }));
    } catch (error) {
      console.error("Failed to fetch trends:", error);
    }
  }, [timeRange]);

  // Set up polling
  useEffect(() => {
    fetchMetrics();
    fetchTrends();

    const interval = setInterval(() => {
      fetchMetrics();
      fetchTrends();
    }, 30000); // Poll every 30 seconds

    return () => clearInterval(interval);
  }, [fetchMetrics, fetchTrends]);

  const metrics = state.metrics;

  return (
    <div style={{ padding: "24px" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ marginBottom: "16px" }}>Metrics Dashboard</h1>

        <Space>
          <Select
            value={timeRange}
            onChange={setTimeRange}
            options={[
              { label: "Last Hour", value: "1h" },
              { label: "Last 6 Hours", value: "6h" },
              { label: "Last 24 Hours", value: "24h" },
              { label: "Last 7 Days", value: "7d" },
            ]}
            style={{ width: "150px" }}
          />
          <Button type="primary" onClick={() => { fetchMetrics(); fetchTrends(); }}>
            Refresh
          </Button>
          {state.lastUpdated && (
            <span style={{ color: "#888", fontSize: "12px" }}>
              Last updated: {state.lastUpdated}
            </span>
          )}
        </Space>

        {state.error && (
          <Alert
            message="Error"
            description={state.error}
            type="error"
            showIcon
            closable
            style={{ marginTop: "16px" }}
          />
        )}
      </div>

      <Spin spinning={state.loading}>
        {/* Summary Cards */}
        <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
          <Col xs={24} sm={12} md={8}>
            <MetricCard
              title="Show Completion Rate"
              value={metrics ? ((metrics.reps_completed / metrics.reps_total) * 100).toFixed(1) : "-"}
              unit="%"
              trend={metrics ? `${metrics.reps_completed}/${metrics.reps_total}` : ""}
              status="good"
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <MetricCard
              title="Avg Rep Duration"
              value={metrics?.avg_rep_duration.toFixed(1) || "-"}
              unit="min"
              trend="↓ improving"
              status="good"
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <MetricCard
              title="Success Rate"
              value={metrics ? (metrics.success_rate * 100).toFixed(1) : "-"}
              unit="%"
              trend="↑ improving"
              status="good"
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <MetricCard
              title="Query Latency (p95)"
              value={metrics?.query_latency_p95.toFixed(1) || "-"}
              unit="ms"
              trend={metrics && metrics.query_latency_p95 > 300 ? "⚠ warning" : ""}
              status={metrics && metrics.query_latency_p95 > 300 ? "warning" : "good"}
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <MetricCard
              title="Agent Utilization"
              value={metrics ? (metrics.agent_utilization * 100).toFixed(0) : "-"}
              unit="%"
              trend="optimal"
              status="good"
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <MetricCard
              title="Message Throughput"
              value={metrics?.message_throughput || "-"}
              unit="msg/min"
              trend="stable"
              status="good"
            />
          </Col>
        </Row>

        {/* Trend Charts */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card title="Rep Completion Trend">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={state.trends.completion_rate}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#1890ff"
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Query Latency Trend">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={state.trends.latency}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="value"
                    fill="#faad14"
                    stroke="#faad14"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24}>
            <Card title="Message Throughput Trend">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={state.trends.throughput}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="value"
                    fill="#52c41a"
                    stroke="#52c41a"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default MetricsDashboard;
