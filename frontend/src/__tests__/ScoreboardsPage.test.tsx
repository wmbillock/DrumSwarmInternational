import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../services/v1", () => ({
  getCorpsScoreboard: vi.fn().mockResolvedValue({
    scoreboard: [
      { corps_id: "c1", corps_name: "Alpha", corps_status: "on_tour", completion_score: 80, efficiency_score: 70, completed_sessions: 5, total_sessions: 6, completed_reps: 2, total_reps: 3, composite_score: 88, rank: 1 },
      { corps_id: "c2", corps_name: "Bravo", corps_status: "winter_camps", completion_score: 60, efficiency_score: 55, completed_sessions: 3, total_sessions: 5, completed_reps: 1, total_reps: 2, composite_score: 70, rank: 2 },
    ],
  }),
  getAgentLeaderboard: vi.fn().mockResolvedValue({
    leaderboard: [
      { role: "designer", nickname: "Nova", corps_id: "c1", total_sessions: 3, completed_sessions: 3, failed_sessions: 0, success_rate: 100, rank: 1 },
      { role: "tech", nickname: "Bolt", corps_id: "c2", total_sessions: 2, completed_sessions: 1, failed_sessions: 1, success_rate: 50, rank: 2 },
    ],
  }),
}));

import * as v1 from "../services/v1";
import { ScoreboardsPage } from "../pages/ScoreboardsPage";

describe("ScoreboardsPage", () => {
  it("renders page title", async () => {
    render(
      <MemoryRouter>
        <ScoreboardsPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Scoreboards")).toBeInTheDocument());
  });

  it("renders medals for top corps", async () => {
    render(
      <MemoryRouter>
        <ScoreboardsPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("🥇")).toBeInTheDocument());
  });

  it("shows corps rows", async () => {
    render(
      <MemoryRouter>
        <ScoreboardsPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Alpha")).toBeInTheDocument());
  });

  it("switches to agents tab", async () => {
    render(
      <MemoryRouter>
        <ScoreboardsPage />
      </MemoryRouter>
    );
    const tab = await screen.findByText(/Agents/);
    fireEvent.click(tab);
    await waitFor(() => expect(screen.getByText("Nova")).toBeInTheDocument());
  });

  it("renders medals for agents", async () => {
    render(
      <MemoryRouter>
        <ScoreboardsPage />
      </MemoryRouter>
    );
    const tab = await screen.findByText(/Agents/);
    fireEvent.click(tab);
    await waitFor(() => expect(screen.getByText("🥇")).toBeInTheDocument());
  });

  it("renders success rate", async () => {
    render(
      <MemoryRouter>
        <ScoreboardsPage />
      </MemoryRouter>
    );
    const tab = await screen.findByText(/Agents/);
    fireEvent.click(tab);
    await waitFor(() => expect(screen.getByText("100%")).toBeInTheDocument());
  });

  it("shows error banner on load failure", async () => {
    vi.mocked(v1.getCorpsScoreboard).mockRejectedValueOnce(new Error("fail"));
    render(
      <MemoryRouter>
        <ScoreboardsPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Failed to fetch scoreboards")).toBeInTheDocument());
  });

  it("renders refresh button", async () => {
    render(
      <MemoryRouter>
        <ScoreboardsPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Refresh")).toBeInTheDocument());
  });
});
