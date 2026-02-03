import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

vi.mock("../services/v1", () => ({
  getCorpsScoreboard: vi.fn().mockResolvedValue({ scoreboard: [{ corps_id: "c1", corps_name: "Alpha", completion_score: 80, composite_score: 75, rank: 1 }] }),
  getAgentLeaderboard: vi.fn().mockResolvedValue({ leaderboard: [{ role: "designer", nickname: "N", success_rate: 90, corps_id: "c1", rank: 1 }] }),
  getMetricsTrends: vi.fn().mockResolvedValue({ trends: [] }),
  getBottlenecks: vi.fn().mockResolvedValue({ role_bottlenecks: [] }),
}));

import MetricsDashboard from "../pages/MetricsDashboard";
import * as v1 from "../services/v1";

class FakeWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  constructor(url: string) {
    this.url = url;
    setTimeout(() => this.onopen && this.onopen(), 0);
  }
  close() {
    this.onclose && this.onclose();
  }
}

describe("MetricsDashboard", () => {
  beforeEach(() => {
    // @ts-expect-error test override
    global.WebSocket = FakeWebSocket;
  });

  it("renders dashboard title", async () => {
    render(<MetricsDashboard />);
    await waitFor(() => expect(screen.getByText("Metrics Dashboard")).toBeInTheDocument());
  });

  it("shows time range selector", async () => {
    render(<MetricsDashboard />);
    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
  });

  it("renders metrics cards", async () => {
    render(<MetricsDashboard />);
    await waitFor(() => expect(screen.getByText("Corps Completion")).toBeInTheDocument());
  });

  it("updates on refresh click", async () => {
    render(<MetricsDashboard />);
    const button = await screen.findByRole("button", { name: /refresh/i });
    fireEvent.click(button);
    expect(button).toBeInTheDocument();
  });

  it("renders top corps leaderboard", async () => {
    render(<MetricsDashboard />);
    await waitFor(() => expect(screen.getByText("Top Corps")).toBeInTheDocument());
  });

  it("renders alert panel", async () => {
    render(<MetricsDashboard />);
    await waitFor(() => expect(screen.getByText("Alerts")).toBeInTheDocument());
  });

  it("shows live or polling indicator", async () => {
    render(<MetricsDashboard />);
    await waitFor(() => expect(screen.getByText(/Live|Polling/)).toBeInTheDocument());
  });

  it("shows error banner on refresh failure", async () => {
    vi.mocked(v1.getCorpsScoreboard).mockRejectedValueOnce(new Error("boom"));
    render(<MetricsDashboard />);
    await waitFor(() => expect(screen.getByText("Failed to load metrics")).toBeInTheDocument());
  });
});
