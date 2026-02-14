import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CompetitionDetail } from "../pages/CompetitionDetail";

const { mockStandings } = vi.hoisted(() => {
  const mockStandings = {
  competition_id: "s1-test-show",
  season_id: "s1",
  show_slug: "test-show",
  generated_at: "2025-01-01T00:00:00Z",
  results: [
    {
      corps_id: "alpha",
      rank: 1,
      final_score: 85.5,
      raw_score: 86.0,
      caption_scores: { brass: 88, percussion: 82, guard: 85, visual: 80, general_effect: 90 },
    },
    {
      corps_id: "bravo",
      rank: 2,
      final_score: 78.3,
      raw_score: 79.0,
      caption_scores: { brass: 75, percussion: 80, guard: 77, visual: 78, general_effect: 82 },
    },
  ],
};
  return { mockStandings };
});

vi.mock("../services/v1", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/v1")>();
  return {
    ...actual,
    getScores: vi.fn().mockResolvedValue(mockStandings),
    runCompetition: vi.fn().mockResolvedValue({ standings: mockStandings.results }),
    getCorpsBreakdown: vi.fn().mockResolvedValue({
      corps_id: "alpha",
      caption_scores: {
        brass: { score: 88, weight: 0.2, weighted: 17.6 },
        percussion: { score: 82, weight: 0.2, weighted: 16.4 },
        guard: { score: 85, weight: 0.2, weighted: 17.0 },
        visual: { score: 80, weight: 0.15, weighted: 12.0 },
        general_effect: { score: 90, weight: 0.25, weighted: 22.5 },
      },
      penalties_total: 0,
      final_score: 85.5,
      commentary: { brass: "Excellent brass performance" },
    }),
  };
});

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={["/competitions/s1-test-show"]}>
      <Routes>
        <Route path="/competitions/:competitionId" element={<CompetitionDetail />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("CompetitionDetail", () => {
  it("renders standings table with scores", async () => {
    renderDetail();
    await waitFor(() => {
      // Corps without display_name renders as "Corps • <id prefix>"
      expect(screen.getByText(/Corps.*alpha/)).toBeInTheDocument();
      expect(screen.getByText(/Corps.*bravo/)).toBeInTheDocument();
      expect(screen.getByText("85.50")).toBeInTheDocument();
    });
  });

  it("shows caption breakdown tab", async () => {
    renderDetail();
    await waitFor(() => expect(screen.getAllByText("Caption Breakdown").length).toBeGreaterThan(0));
    fireEvent.click(screen.getAllByText("Caption Breakdown")[0]);
    await waitFor(() => {
      expect(screen.getByText("Brass")).toBeInTheDocument();
    });
  });

  it("shows compare tab with two corps", async () => {
    renderDetail();
    await waitFor(() => expect(screen.getAllByText("Compare").length).toBeGreaterThan(0));
    fireEvent.click(screen.getAllByText("Compare")[0]);
    await waitFor(() => {
      expect(screen.getByText("vs")).toBeInTheDocument();
    });
  });

  it("has all three tab buttons", async () => {
    renderDetail();
    await waitFor(() => {
      expect(screen.getAllByText("Standings").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Caption Breakdown").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Compare").length).toBeGreaterThan(0);
    });
  });
});
