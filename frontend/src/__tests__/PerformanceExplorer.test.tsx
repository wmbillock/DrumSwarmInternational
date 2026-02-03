import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("../services/v1", () => ({
  getMetricsSeries: vi.fn().mockResolvedValue({ data: [{ timestamp: "t1", rep_completed: 1 }] }),
}));

import PerformanceExplorer from "../pages/PerformanceExplorer";
import * as v1 from "../services/v1";

describe("PerformanceExplorer", () => {

  it("renders page title", () => {
    render(<PerformanceExplorer />);
    expect(screen.getByText("Performance Explorer")).toBeInTheDocument();
  });

  it("shows update chart button", () => {
    render(<PerformanceExplorer />);
    expect(screen.getByText("Update Chart")).toBeInTheDocument();
  });

  it("renders time range selector", () => {
    render(<PerformanceExplorer />);
    expect(screen.getByText("Last 24 Hours")).toBeInTheDocument();
  });

  it("fetches metrics on update", async () => {
    render(<PerformanceExplorer />);
    fireEvent.click(screen.getByText("Update Chart"));
    await waitFor(() => expect(v1.getMetricsSeries).toHaveBeenCalled());
  });

  it("renders trend chart when data is loaded", async () => {
    render(<PerformanceExplorer />);
    fireEvent.click(screen.getByText("Update Chart"));
    await waitFor(() => expect(document.querySelector("svg")).toBeTruthy());
  });

  it("shows export buttons", () => {
    render(<PerformanceExplorer />);
    expect(screen.getByText("Export CSV")).toBeInTheDocument();
    expect(screen.getByText("Export JSON")).toBeInTheDocument();
  });

  it("enables export buttons when data is available", async () => {
    render(<PerformanceExplorer />);
    fireEvent.click(screen.getByText("Update Chart"));
    await waitFor(() => expect(screen.getByText("Export CSV")).toBeEnabled());
    expect(screen.getByText("Export JSON")).toBeEnabled();
  });

  it("shows error banner on fetch failure", async () => {
    vi.mocked(v1.getMetricsSeries).mockRejectedValueOnce(new Error("fail"));
    render(<PerformanceExplorer />);
    fireEvent.click(screen.getByText("Update Chart"));
    await waitFor(() => expect(screen.getByText("Failed to fetch metrics")).toBeInTheDocument());
  });
});
