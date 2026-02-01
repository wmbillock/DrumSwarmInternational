/**
 * Scoreboards Page — Rankings and leaderboards for corps and agents.
 *
 * Displays:
 * - Corps leaderboard by composite score
 * - Agent roles leaderboard by performance
 * - Drill-down into individual performance
 * - Filter and sort controls
 */

import React, { useState, useEffect } from "react";
import {
  Tabs,
  Table,
  Card,
  Row,
  Col,
  Select,
  Space,
  Button,
  Badge,
  Progress,
  Spin,
  Empty,
  Modal,
} from "antd";
import { EyeOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";

interface CorpsScore {
  rank: number;
  corps_id: string;
  corps_name: string;
  shows_completed: number;
  shows_total: number;
  show_completion_rate: number;
  avg_task_duration: number;
  task_success_rate: number;
  query_latency_p95: number;
  composite_score: number;
}

interface AgentScore {
  rank: number;
  agent_role: string;
  agent_count: number;
  avg_session_duration: number;
  sessions_completed: number;
  task_success_rate: number;
  avg_task_throughput: number;
  composite_score: number;
}

const ScoreboardsPage: React.FC = () => {
  const [corpsList, setCorpsList] = useState<CorpsScore[]>([]);
  const [agentsList, setAgentsList] = useState<AgentScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"composite" | "completion" | "latency">("composite");
  const [selectedCorps, setSelectedCorps] = useState<CorpsScore | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  // Fetch corps scoreboard
  useEffect(() => {
    const fetchCorpsScores = async () => {
      try {
        const response = await fetch(`/api/v1/metrics/scoreboard/corps?limit=100`);
        const data = await response.json();

        // Transform API response to component format
        const transformed: CorpsScore[] = (data.scoreboard || []).map((item: any) => ({
          rank: item.rank,
          corps_id: item.corps_id,
          corps_name: item.corps_name,
          shows_completed: item.completed_reps,
          shows_total: item.total_reps,
          show_completion_rate: item.completed_reps / Math.max(item.total_reps, 1),
          avg_task_duration: 0,
          task_success_rate: item.efficiency_score / 100,
          query_latency_p95: 0,
          composite_score: item.composite_score,
        }));

        setCorpsList(transformed);
        setLoading(false);
      } catch (error) {
        console.error("Failed to fetch corps scores:", error);
        setLoading(false);
      }
    };

    const fetchAgentScores = async () => {
      try {
        const response = await fetch(`/api/v1/metrics/scoreboard/agents?limit=100`);
        const data = await response.json();

        // Transform API response to component format
        const transformed: AgentScore[] = (data.leaderboard || []).map((item: any) => ({
          rank: item.rank,
          agent_role: item.role,
          agent_count: 1,
          avg_session_duration: 0,
          sessions_completed: item.completed_sessions,
          task_success_rate: (item.success_rate || 0) / 100,
          avg_task_throughput: 0,
          composite_score: item.success_rate || 0,
        }));

        setAgentsList(transformed);
      } catch (error) {
        console.error("Failed to fetch agent scores:", error);
      }
    };

    fetchCorpsScores();
    fetchAgentScores();
  }, []);

  // Corps columns
  const corpsColumns: ColumnsType<CorpsScore> = [
    {
      title: "Rank",
      dataIndex: "rank",
      key: "rank",
      width: 60,
      render: (text) => (
        <span style={{ fontWeight: "bold", fontSize: "16px" }}>
          #{text}
        </span>
      ),
    },
    {
      title: "Corps Name",
      dataIndex: "corps_name",
      key: "corps_name",
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: "Shows",
      dataIndex: "shows_completed",
      key: "shows",
      render: (_, record) => (
        <span>
          {record.shows_completed}/{record.shows_total} ({Math.round(record.show_completion_rate * 100)}%)
        </span>
      ),
    },
    {
      title: "Avg Duration",
      dataIndex: "avg_task_duration",
      key: "duration",
      render: (text) => <span>{text.toFixed(1)} min</span>,
    },
    {
      title: "Success Rate",
      dataIndex: "task_success_rate",
      key: "success",
      render: (text) => (
        <Progress percent={Math.round(text * 100)} strokeColor="#52c41a" size="small" />
      ),
    },
    {
      title: "Latency (p95)",
      dataIndex: "query_latency_p95",
      key: "latency",
      render: (text) => (
        <Badge
          count={`${text.toFixed(1)}ms`}
          color={text > 300 ? "#f5222d" : text > 150 ? "#faad14" : "#52c41a"}
        />
      ),
    },
    {
      title: "Score",
      dataIndex: "composite_score",
      key: "composite",
      render: (text) => <strong>{text.toFixed(1)}</strong>,
      sorter: (a, b) => b.composite_score - a.composite_score,
    },
    {
      title: "Action",
      key: "action",
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => {
            setSelectedCorps(record);
            setDetailModalVisible(true);
          }}
        >
          Details
        </Button>
      ),
    },
  ];

  // Agent columns
  const agentColumns: ColumnsType<AgentScore> = [
    {
      title: "Rank",
      dataIndex: "rank",
      key: "rank",
      width: 60,
      render: (text) => <span style={{ fontWeight: "bold", fontSize: "16px" }}>#{text}</span>,
    },
    {
      title: "Agent Role",
      dataIndex: "agent_role",
      key: "agent_role",
      render: (text) => <strong>{text.replace(/_/g, " ")}</strong>,
    },
    {
      title: "Agents",
      dataIndex: "agent_count",
      key: "agent_count",
      render: (text) => <span>{text}</span>,
    },
    {
      title: "Sessions Completed",
      dataIndex: "sessions_completed",
      key: "sessions",
      render: (text) => <span>{text}</span>,
    },
    {
      title: "Avg Duration",
      dataIndex: "avg_session_duration",
      key: "duration",
      render: (text) => <span>{(text / 60).toFixed(1)} min</span>,
    },
    {
      title: "Success Rate",
      dataIndex: "task_success_rate",
      key: "success",
      render: (text) => (
        <Progress percent={Math.round(text * 100)} strokeColor="#52c41a" size="small" />
      ),
    },
    {
      title: "Throughput",
      dataIndex: "avg_task_throughput",
      key: "throughput",
      render: (text) => <span>{text.toFixed(1)} tasks/hr</span>,
    },
    {
      title: "Score",
      dataIndex: "composite_score",
      key: "composite",
      render: (text) => <strong>{text.toFixed(1)}</strong>,
      sorter: (a, b) => b.composite_score - a.composite_score,
    },
  ];

  return (
    <div style={{ padding: "24px" }}>
      <h1 style={{ marginBottom: "24px" }}>Scoreboards & Leaderboards</h1>

      <Spin spinning={loading}>
        <Tabs
          defaultActiveKey="corps"
          items={[
            {
              key: "corps",
              label: "Corps Leaderboard",
              children: (
                <Card>
                  <Row style={{ marginBottom: "16px" }}>
                    <Col>
                      <Space>
                        <span>Sort by:</span>
                        <Select
                          value={sortBy}
                          onChange={setSortBy}
                          options={[
                            { label: "Composite Score", value: "composite" },
                            { label: "Completion Rate", value: "completion" },
                            { label: "Latency", value: "latency" },
                          ]}
                          style={{ width: "150px" }}
                        />
                      </Space>
                    </Col>
                  </Row>
                  <Table
                    columns={corpsColumns}
                    dataSource={corpsList}
                    rowKey="corps_id"
                    pagination={{ pageSize: 20 }}
                    locale={{ emptyText: <Empty description="No corps data available" /> }}
                  />
                </Card>
              ),
            },
            {
              key: "agents",
              label: "Agent Leaderboard",
              children: (
                <Card>
                  <Table
                    columns={agentColumns}
                    dataSource={agentsList}
                    rowKey="agent_role"
                    pagination={{ pageSize: 20 }}
                    locale={{ emptyText: <Empty description="No agent data available" /> }}
                  />
                </Card>
              ),
            },
          ]}
        />
      </Spin>

      {/* Detail Modal */}
      <Modal
        title={selectedCorps ? `${selectedCorps.corps_name} — Detailed Performance` : ""}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={700}
      >
        {selectedCorps && (
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card type="inner" title="Summary">
                <Row gutter={16}>
                  <Col xs={12}>
                    <div style={{ marginBottom: "8px", color: "#888", fontSize: "12px" }}>
                      Rank
                    </div>
                    <div style={{ fontSize: "20px", fontWeight: "bold" }}>
                      #{selectedCorps.rank}
                    </div>
                  </Col>
                  <Col xs={12}>
                    <div style={{ marginBottom: "8px", color: "#888", fontSize: "12px" }}>
                      Composite Score
                    </div>
                    <div style={{ fontSize: "20px", fontWeight: "bold", color: "#1890ff" }}>
                      {selectedCorps.composite_score.toFixed(1)}
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
            <Col span={24}>
              <Card type="inner" title="Performance Metrics">
                <Row gutter={16}>
                  <Col xs={12} sm={6}>
                    <div style={{ marginBottom: "8px", color: "#888", fontSize: "12px" }}>
                      Show Completion
                    </div>
                    <Progress
                      type="circle"
                      percent={Math.round(selectedCorps.show_completion_rate * 100)}
                      width={80}
                    />
                  </Col>
                  <Col xs={12} sm={6}>
                    <div style={{ marginBottom: "8px", color: "#888", fontSize: "12px" }}>
                      Success Rate
                    </div>
                    <Progress
                      type="circle"
                      percent={Math.round(selectedCorps.task_success_rate * 100)}
                      width={80}
                      strokeColor="#52c41a"
                    />
                  </Col>
                  <Col xs={12} sm={6}>
                    <div style={{ marginBottom: "8px", color: "#888", fontSize: "12px" }}>
                      Avg Duration
                    </div>
                    <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                      {selectedCorps.avg_task_duration.toFixed(1)} min
                    </div>
                  </Col>
                  <Col xs={12} sm={6}>
                    <div style={{ marginBottom: "8px", color: "#888", fontSize: "12px" }}>
                      Latency (p95)
                    </div>
                    <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                      {selectedCorps.query_latency_p95.toFixed(1)} ms
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        )}
      </Modal>
    </div>
  );
};

export default ScoreboardsPage;
