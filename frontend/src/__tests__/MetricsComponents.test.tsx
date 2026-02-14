import { describe, it, expect, vi, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { MetricsCard } from "../components/metrics/MetricsCard";
import { TrendChart } from "../components/metrics/TrendChart";
import { Leaderboard } from "../components/metrics/Leaderboard";
import { AlertPanel } from "../components/metrics/AlertPanel";

describe("Metrics components", () => {
  it("renders MetricsCard title and value", () => {
    const { getByText } = render(<MetricsCard title="Latency" value="120ms" />);
    expect(getByText("Latency")).toBeInTheDocument();
    expect(getByText("120ms")).toBeInTheDocument();
  });

  it("renders MetricsCard sparkline", () => {
    const { container } = render(
      <MetricsCard title="Throughput" value="80" sparkline={[1, 2, 3]} />
    );
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("renders TrendChart with series", () => {
    const { container } = render(
      <TrendChart
        series={[{ id: "s1", label: "S1", points: [{ x: 0, y: 1 }, { x: 1, y: 2 }] }]}
      />
    );
    expect(container.querySelector("path")).toBeTruthy();
  });

  it("renders Leaderboard medals for top 3", () => {
    const { getByText } = render(
      <Leaderboard
        rows={[
          { id: "a", rank: 1, label: "Alpha" },
          { id: "b", rank: 2, label: "Bravo" },
          { id: "c", rank: 3, label: "Charlie" },
        ]}
      />
    );
    expect(getByText("🥇")).toBeInTheDocument();
    expect(getByText("🥈")).toBeInTheDocument();
    expect(getByText("🥉")).toBeInTheDocument();
  });

  it("fires Leaderboard row click", () => {
    const onRowClick = vi.fn();
    const { getAllByText } = render(
      <Leaderboard
        rows={[{ id: "a", rank: 1, label: "Alpha" }]}
        onRowClick={onRowClick}
      />
    );
    fireEvent.click(getAllByText("Alpha")[0]);
    expect(onRowClick).toHaveBeenCalled();
  });

  it("renders AlertPanel alerts", () => {
    const { getByText } = render(
      <AlertPanel
        alerts={[{ id: "1", title: "Latency spike", status: "warning" }]}
      />
    );
    expect(getByText("Latency spike")).toBeInTheDocument();
  });

  it("renders AlertPanel empty state", () => {
    const { getByText } = render(<AlertPanel alerts={[]} />);
    expect(getByText("No alerts.")).toBeInTheDocument();
  });

  it("applies status class on MetricsCard", () => {
    const { container } = render(<MetricsCard title="Errors" value="2" status="critical" />);
    expect(container.querySelector(".metrics-card-critical")).toBeTruthy();
  });
});
