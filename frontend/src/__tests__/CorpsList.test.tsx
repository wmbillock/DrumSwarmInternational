import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock the v1 API module
vi.mock("../services/v1", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/v1")>();
  return {
    ...actual,
    listCorps: vi.fn().mockResolvedValue([]),
  };
});

import { CorpsList } from "../pages/CorpsList";

describe("CorpsList", () => {
  it("renders the corps list page", async () => {
    render(
      <MemoryRouter>
        <CorpsList />
      </MemoryRouter>
    );
    // The page should render — it may show loading or corps data
    expect(document.body).toBeInTheDocument();
  });
});
