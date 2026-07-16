import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { SeasonRunTimeline } from "../SeasonRunTimeline";

test("renders season status, corps phase, next action, and blocker", () => {
  render(
    <SeasonRunTimeline
      summary={{
        season_run_id: "season-1",
        status: "blocked",
        regular_show_count: 4,
        winter_camp_count: 7,
        current_event_index: 1,
        blocker_reason: "Corps show has segments without captions.",
        corps: [
          {
            corps_id: "corps-1",
            phase: "blocked",
            blocker_reason: "Corps show has segments without captions.",
            next_action: "Fix unroutable segments.",
          },
        ],
      }}
    />
  );

  expect(screen.getAllByText("blocked")).toHaveLength(2);
  expect(screen.getByText("4 regular shows, finals, 7 winter camps")).toBeInTheDocument();
  expect(screen.getByText("corps-1")).toBeInTheDocument();
  expect(screen.getByText("Fix unroutable segments.")).toBeInTheDocument();
  expect(screen.getAllByText("Corps show has segments without captions.")).toHaveLength(2);
});
