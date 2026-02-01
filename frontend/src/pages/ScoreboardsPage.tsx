/**
 * Scoreboards Page — Rankings and leaderboards for corps and agents.
 *
 * Displays:
 * - Corps leaderboard by composite score
 * - Agent roles leaderboard by performance
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
  Progress,
  Spin,
  Empty,
  Modal,
} from "antd";
import { EyeOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  getCorpsScoreboard,
  getAgentLeaderboard,
  CorpsScore,
  AgentLeaderEntry,
} from "../services/v1";

const ScoreboardsPage: React.FC = () => {
  const [corpsList, setCorpsList] = useState<CorpsScore[]>([]);
  const [agentsList, setAgentsList] = useState<AgentLeaderEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState(7);
  const [selectedCorps, setSelectedCorps] = useState<CorpsScore | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [corpsRes, agentsRes] = await Promise.all([
        getCorpsScoreboard(periodDays),
        getAgentLeaderboard(undefined, periodDays),
      ]);
      setCorpsList(corpsRes.scoreboard || []);
      setAgentsList(agentsRes.leaderboard || []);
    } catch (error) {
      console.error("Failed to fetch scoreboards:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [periodDays]);

  const corpsColumns: ColumnsType<CorpsScore> = [
    {
      title: "Rank",
      dataIndex: "rank",
      key: "rank",
      width: 60,
      render: (text) => (
        <span style={{ fontWeight: "bold", fontSize: "16px" }}>#{text}</span>
      ),
    },
    {
      title: "Corps Name",
      dataIndex: "corps_name",
      key: "corps_name",
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: "Status",
      dataIndex: "corps_status",
      key: "corps_status",
      render: (text) => <span>{text.replace(/_/g, " ")}</span>,
    },
    {
      title: "Completion",
      dataIndex: "completion_score",
      key: "completion",
      render: (text) => (
        <Progress percent={Math.round(text)} strokeColor="#52c41a" size="small" />
      ),
    },
    {
      title: "Efficiency",
      dataIndex: "efficiency_score",
      key: "efficiency",
      render: (text) => <span>{text.toFixed(1)}%</span>,
    },
    {
      title: "Sessions",
      key: "sessions",
      render: (_, record) => (
        <span>
          {record.completed_sessions}/{record.total_sessions}
        </span>
      ),
    },
    {
      title: "Reps",
      key: "reps",
      render: (_, record) => (
        <span>
          {record.completed_reps}/{record.total_reps}
        </span>
      ),
    },
    {
      title: "Score",
      dataIndex: "composite_score",
      key: "composite",
      render: (text) => <strong>{text.toFixed(1)}</strong>,
      sorter: (a, b) => b.composite_score - a.composite_score,
      defaultSortOrder: "descend",
    },
    {
      title: "",
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

  const agentColumns: ColumnsType<AgentLeaderEntry> = [
    {
      title: "Rank",
      dataIndex: "rank",
      key: "rank",
      width: 60,
      render: (text) => (
        <span style={{ fontWeight: "bold", fontSize: "16px" }}>#{text}</span>
      ),
    },
    {
      title: "Role",
      dataIndex: "role",
      key: "role",
      render: (text) => <strong>{text.replace(/_/g, " ")}</strong>,
    },
    {
      title: "Nickname",
      dataIndex: "nickname",
      key: "nickname",
    },
    {
      title: "Sessions",
      dataIndex: "total_sessions",
      key: "total_sessions",
    },
    {
      title: "Completed",
      dataIndex: "completed_sessions",
      key: "completed_sessions",
    },
    {
      title: "Failed",
      dataIndex: "failed_sessions",
      key: "failed_sessions",
      render: (text) => (
        <span style={{ color: text > 0 ? "#f5222d" : undefined }}>{text}</span>
      ),
    },
    {
      title: "Success Rate",
      dataIndex: "success_rate",
      key: "success_rate",
      render: (text) => (
        <Progress
          percent={Math.round(text)}
          strokeColor={text >= 80 ? "#52c41a" : text >= 50 ? "#faad14" : "#f5222d"}
          size="small"
        />
      ),
      sorter: (a, b) => b.success_rate - a.success_rate,
    },
  ];

  return (
    <div style={{ padding: "24px" }}>
      <div style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>Scoreboards & Leaderboards</h1>
        <Space>
          <Select
            value={periodDays}
            onChange={setPeriodDays}
            options={[
              { label: "Last 7 Days", value: 7 },
              { label: "Last 14 Days", value: 14 },
              { label: "Last 30 Days", value: 30 },
            ]}
            style={{ width: "150px" }}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>
            Refresh
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Tabs
          defaultActiveKey="corps"
          items={[
            {
              key: "corps",
              label: `Corps Leaderboard (${corpsList.length})`,
              children: (
                <Card>
                  <Table
                    columns={corpsColumns}
                    dataSource={corpsList}
                    rowKey="corps_id"
                    pagination={{ pageSize: 20 }}
                    locale={{
                      emptyText: <Empty description="No corps data available" />,
                    }}
                  />
                </Card>
              ),
            },
            {
              key: "agents",
              label: `Agent Leaderboard (${agentsList.length})`,
              children: (
                <Card>
                  <Table
                    columns={agentColumns}
                    dataSource={agentsList}
                    rowKey={(r) => `${r.role}-${r.corps_id}`}
                    pagination={{ pageSize: 20 }}
                    locale={{
                      emptyText: <Empty description="No agent data available" />,
                    }}
                  />
                </Card>
              ),
            },
          ]}
        />
      </Spin>

      <Modal
        title={
          selectedCorps
            ? `${selectedCorps.corps_name} — Performance Breakdown`
            : ""
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedCorps && (
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card type="inner" size="small" title="Rank">
                <div style={{ fontSize: "24px", fontWeight: "bold" }}>
                  #{selectedCorps.rank}
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card type="inner" size="small" title="Composite Score">
                <div style={{ fontSize: "24px", fontWeight: "bold", color: "#1890ff" }}>
                  {selectedCorps.composite_score.toFixed(1)}
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card type="inner" size="small" title="Completion">
                <Progress
                  type="circle"
                  percent={Math.round(selectedCorps.completion_score)}
                  width={80}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card type="inner" size="small" title="Efficiency">
                <Progress
                  type="circle"
                  percent={Math.round(selectedCorps.efficiency_score)}
                  width={80}
                  strokeColor="#52c41a"
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card type="inner" size="small" title="Sessions">
                <div>
                  {selectedCorps.completed_sessions} completed / {selectedCorps.total_sessions} total
                </div>
                <div style={{ color: "#f5222d" }}>
                  {selectedCorps.failed_sessions} failed
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card type="inner" size="small" title="Reps">
                <div>
                  {selectedCorps.completed_reps} completed / {selectedCorps.total_reps} total
                </div>
                <div style={{ color: "#f5222d" }}>
                  {selectedCorps.failed_reps} failed
                </div>
              </Card>
            </Col>
          </Row>
        )}
      </Modal>
    </div>
  );
};

export default ScoreboardsPage;
