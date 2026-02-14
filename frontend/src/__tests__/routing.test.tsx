import { describe, it, expect, vi, beforeAll } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";

// Mock fetch globally so pages that fetch on mount don't fail
beforeAll(() => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve([]),
  }));
});

// Use lazy imports to avoid AbortSignal mismatch with data router
import { CommandCenter } from "../pages/CommandCenter";
import { CorpsList } from "../pages/CorpsList";
import { Settings } from "../pages/Settings";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/corps" element={<CorpsList />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
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

  it("renders at /settings without crashing", () => {
    const { container } = renderAt("/settings");
    expect(container.querySelector(".app")).toBeTruthy();
  });
});
