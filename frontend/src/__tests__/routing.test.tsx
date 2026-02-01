import { describe, it, expect, vi, beforeAll } from "vitest";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

// Mock fetch globally so pages that fetch on mount don't fail
beforeAll(() => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve([]),
  }));
});

import { router } from "../router";

function renderAt(path: string) {
  const routes = router.routes;
  const memRouter = createMemoryRouter(routes, { initialEntries: [path] });
  return render(<RouterProvider router={memRouter} />);
}

describe("routing", () => {
  it("renders at / without crashing", () => {
    const { container } = renderAt("/");
    expect(container.querySelector(".app")).toBeTruthy();
  });

  it("renders at /corps without crashing", () => {
    const { container } = renderAt("/corps");
    expect(container.querySelector(".app")).toBeTruthy();
  });

  it("renders at /competitions without crashing", () => {
    const { container } = renderAt("/competitions");
    expect(container.querySelector(".app")).toBeTruthy();
  });

  it("renders at /settings without crashing", () => {
    const { container } = renderAt("/settings");
    expect(container.querySelector(".app")).toBeTruthy();
  });
});
