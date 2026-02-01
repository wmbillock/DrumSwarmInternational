import { describe, it, expect, vi, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../services/v1", () => ({
  getCorps: vi.fn().mockResolvedValue({
    corps_id: "cavaliers",
    display_name: "The Cavaliers",
    philosophy: "Regal brass excellence",
    state: "on_tour",
    roster_size: 12,
    history_count: 3,
    history: [],
  }),
  listRuns: vi.fn().mockResolvedValue([]),
  getCorpsHistory: vi.fn().mockResolvedValue({ corps_id: "cavaliers", generated_at: "", entries: [] }),
  ApiError: class extends Error { status: number; constructor(s: number, m: string) { super(m); this.status = s; } },
}));

import { CorpsDetailV2 } from "../pages/CorpsDetailV2";

function renderCorpsDetail(tab?: string) {
  const path = tab ? `/corps/cavaliers/${tab}` : "/corps/cavaliers";
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/corps/:corpsId" element={<CorpsDetailV2 />} />
        <Route path="/corps/:corpsId/:tab" element={<CorpsDetailV2 />} />
      </Routes>
    </MemoryRouter>
  );
}

afterEach(() => cleanup());

describe("CorpsDetailV2", () => {
  it("renders corps name and state", async () => {
    renderCorpsDetail();
    expect(await screen.findByRole("heading", { name: "The Cavaliers" })).toBeInTheDocument();
    expect(screen.getAllByText("on_tour").length).toBeGreaterThan(0);
  });

  it("renders Overview tab by default", async () => {
    renderCorpsDetail();
    expect(await screen.findByText("Corps Info")).toBeInTheDocument();
  });

  it("switches tabs on click", async () => {
    renderCorpsDetail();
    await screen.findByRole("heading", { name: "The Cavaliers" });
    fireEvent.click(screen.getByText("Runs"));
    expect(await screen.findByText("Run History")).toBeInTheDocument();
  });
});
