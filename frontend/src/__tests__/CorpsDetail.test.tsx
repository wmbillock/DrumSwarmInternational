import { describe, it, expect, vi, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../services/v1", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/v1")>();
  return {
    ...actual,
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
    listAwards: vi.fn().mockResolvedValue([]),
    getStaffingStatus: vi.fn().mockResolvedValue({ corps_id: "cavaliers", roles: [] }),
    executeCorpsCommand: vi.fn().mockResolvedValue({ result: "ok" }),
    generateCorpsLogo: vi.fn().mockResolvedValue({ url: "" }),
    sendCorpsFeedback: vi.fn().mockResolvedValue({}),
    startEDChat: vi.fn().mockResolvedValue({ session_id: "s1" }),
    fetchV1: vi.fn().mockResolvedValue([]),
  };
});

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
    expect(screen.getAllByText("On Tour").length).toBeGreaterThan(0);
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
