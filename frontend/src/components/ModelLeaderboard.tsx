import { useEffect, useState } from "react";
import { Panel, Badge, DataTable } from "../ui";
import type { Column } from "../ui/DataTable";
import * as v1 from "../services/v1";

interface LeaderboardProps {
  taskCategory: string;
  limit?: number;
  accentColor?: string;
}

type LeaderboardRow = v1.V1LeaderboardEntry & Record<string, unknown>;

const PROVIDER_VARIANTS: Record<string, "success" | "info" | "warning" | "default"> = {
  anthropic: "info",
  openai: "success",
  ollama: "warning",
};

export function ModelLeaderboard({ taskCategory, limit = 10, accentColor }: LeaderboardProps) {
  const [entries, setEntries] = useState<v1.V1LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    v1.getLeaderboard(taskCategory, limit, ac.signal)
      .then((r) => setEntries(r.entries))
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [taskCategory, limit]);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading leaderboard...</p>;

  const columns: Column<LeaderboardRow>[] = [
    {
      key: "name",
      label: "Model",
      sortable: true,
      render: (_v, row) => (
        <span style={{ fontWeight: 600 }}>{row.name}</span>
      ),
    },
    {
      key: "provider",
      label: "Provider",
      sortable: true,
      render: (v) => (
        <Badge variant={PROVIDER_VARIANTS[v as string] || "default"}>
          {v as string}
        </Badge>
      ),
    },
    {
      key: "avg_score",
      label: "Avg Score",
      sortable: true,
      render: (v) => (
        <span className="mono" style={{ color: accentColor || "var(--accent)" }}>
          {(v as number).toFixed(1)}
        </span>
      ),
    },
    {
      key: "total_attempts",
      label: "Attempts",
      sortable: true,
    },
    {
      key: "success_rate",
      label: "Success",
      sortable: true,
      render: (v) => `${((v as number) * 100).toFixed(0)}%`,
    },
  ];

  return (
    <DataTable<LeaderboardRow>
      columns={columns}
      data={entries as LeaderboardRow[]}
      emptyMessage={`No data for "${taskCategory}"`}
      defaultSortKey="avg_score"
      defaultSortDir="desc"
    />
  );
}
