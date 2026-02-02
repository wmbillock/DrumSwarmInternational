import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchV1 } from "../services/v1";

const originalFetch = global.fetch;

describe("v1 request handling", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("returns undefined for 204 responses", async () => {
    const json = vi.fn();
    const text = vi.fn();
    const headers = { get: () => null };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 204,
      headers,
      json,
      text,
    });

    const result = await fetchV1("/noop");

    expect(result).toBeUndefined();
    expect(json).not.toHaveBeenCalled();
    expect(text).not.toHaveBeenCalled();
  });
});
