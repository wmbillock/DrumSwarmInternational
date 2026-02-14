import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// Mock v1 API
vi.mock("../services/v1", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/v1")>();
  return {
    ...actual,
    listThreads: vi.fn(),
    createThread: vi.fn(),
    getMessages: vi.fn(),
    postMessage: vi.fn(),
    getBrief: vi.fn(),
    updateBrief: vi.fn(),
    getPrompt: vi.fn(),
    updatePrompt: vi.fn(),
    lintPrompt: vi.fn(),
    publishThread: vi.fn(),
    listVersions: vi.fn(),
    approveThread: vi.fn(),
  };
});

import * as v1 from "../services/v1";
import { DesignRoom } from "../pages/DesignRoom";

const mockV1 = vi.mocked(v1);

function renderAtRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/design" element={<DesignRoom />} />
        <Route path="/design/:showSlug" element={<DesignRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

function setupDetailMocks(slug: string, status = "draft") {
  mockV1.listThreads.mockResolvedValue([
    { slug, status, has_spec: true },
  ]);
  mockV1.getMessages.mockResolvedValue({ slug, messages: [] });
  mockV1.getBrief.mockResolvedValue({ slug, content: "# Brief" });
  mockV1.getPrompt.mockResolvedValue({ slug, content: "" });
  mockV1.listVersions.mockResolvedValue({ versions: [] });
  mockV1.lintPrompt.mockResolvedValue({ required_fix: [], nice_to_have: [], acceptable_risk: [] });
}

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  vi.resetAllMocks();
});

describe("ThreadList view", () => {
  it("renders thread list from listThreads", async () => {
    mockV1.listThreads.mockResolvedValue([
      { slug: "test-show", status: "draft", has_spec: true },
      { slug: "approved-show", status: "approved", has_spec: true },
    ]);
    renderAtRoute("/design");
    await waitFor(() => {
      expect(screen.getByText("test-show")).toBeInTheDocument();
      expect(screen.getByText("approved-show")).toBeInTheDocument();
    });
  });

  it("create form calls createThread", async () => {
    mockV1.listThreads.mockResolvedValue([]);
    // createThread resolves but we don't need to follow navigation
    mockV1.createThread.mockResolvedValue({ slug: "new-show" });
    // Setup mocks for the destination route
    mockV1.getMessages.mockResolvedValue({ slug: "new-show", messages: [] });
    mockV1.getBrief.mockResolvedValue({ slug: "new-show", content: "" });
    mockV1.getPrompt.mockResolvedValue({ slug: "new-show", content: "" });
    mockV1.listVersions.mockResolvedValue({ versions: [] });

    renderAtRoute("/design");
    await waitFor(() => expect(screen.getByText("New Thread")).toBeInTheDocument());

    const input = screen.getByPlaceholderText("New show title...");
    fireEvent.change(input, { target: { value: "New Show" } });
    fireEvent.click(screen.getByText("New Thread"));
    await waitFor(() => {
      expect(mockV1.createThread).toHaveBeenCalledWith("New Show");
    });
  });
});

describe("Thread Detail view", () => {
  it("loads message history on mount", async () => {
    setupDetailMocks("test-show");
    mockV1.getMessages.mockResolvedValue({
      slug: "test-show",
      messages: [
        { role: "user", content: "hello", tags: [] },
        { role: "music_writer", content: "noted", tags: ["music"] },
      ],
    });
    renderAtRoute("/design/test-show");
    await waitFor(() => {
      expect(screen.getByText("hello")).toBeInTheDocument();
      expect(screen.getByText("noted")).toBeInTheDocument();
    });
  });

  it("sends message with optimistic update", async () => {
    setupDetailMocks("test-show");
    mockV1.postMessage.mockResolvedValue({
      role: "music_writer",
      tags: ["music"],
      response: "Great idea!",
    });
    renderAtRoute("/design/test-show");
    await waitFor(() => expect(mockV1.getMessages).toHaveBeenCalled());

    const inputs = screen.getAllByPlaceholderText("Share your vision with the design team...");
    fireEvent.change(inputs[0], { target: { value: "Add brass" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("Add brass")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("Great idea!")).toBeInTheDocument());
  });

  it("shows Brief tab by default", async () => {
    setupDetailMocks("test-show");
    renderAtRoute("/design/test-show");
    await waitFor(() => {
      expect(screen.getByText("Show Spec")).toBeInTheDocument();
    });
  });

  it("switches to Prompt tab", async () => {
    setupDetailMocks("test-show");
    renderAtRoute("/design/test-show");
    await waitFor(() => expect(screen.getByText("Brief")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Prompt"));
    await waitFor(() => {
      expect(screen.getByText("Show Prompt")).toBeInTheDocument();
    });
  });

  it("switches to Versions tab", async () => {
    setupDetailMocks("test-show");
    mockV1.listVersions.mockResolvedValue({ versions: [1, 2] });
    renderAtRoute("/design/test-show");
    await waitFor(() => expect(screen.getByText("Brief")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Versions"));
    await waitFor(() => {
      expect(screen.getByText("v1")).toBeInTheDocument();
      expect(screen.getByText("v2")).toBeInTheDocument();
    });
  });

  it("brief edit + save calls updateBrief", async () => {
    setupDetailMocks("test-show");
    mockV1.updateBrief.mockResolvedValue({ status: "updated" });
    renderAtRoute("/design/test-show");
    await waitFor(() => expect(screen.getByText("Show Spec")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Edit"));
    // Find the textarea (not the chat input) — it's the multiline one
    const textareas = await waitFor(() => screen.getAllByRole("textbox"));
    const textarea = textareas.find(el => el.tagName === "TEXTAREA") || textareas[textareas.length - 1];
    fireEvent.change(textarea, { target: { value: "# Updated" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(mockV1.updateBrief).toHaveBeenCalledWith("test-show", "# Updated");
    });
  });

  it("prompt edit + save calls updatePrompt", async () => {
    setupDetailMocks("test-show");
    mockV1.updatePrompt.mockResolvedValue({ status: "updated" });
    renderAtRoute("/design/test-show");
    await waitFor(() => expect(screen.getByText("Brief")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Prompt"));
    await waitFor(() => expect(screen.getByText("Show Prompt")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Edit"));
    const textareas = await waitFor(() => screen.getAllByRole("textbox"));
    const textarea = textareas.find(el => el.tagName === "TEXTAREA") || textareas[textareas.length - 1];
    fireEvent.change(textarea, { target: { value: "# New Prompt" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(mockV1.updatePrompt).toHaveBeenCalledWith("test-show", "# New Prompt");
    });
  });

  it("lint button shows findings", async () => {
    setupDetailMocks("test-show");
    renderAtRoute("/design/test-show");
    await waitFor(() => expect(screen.getByText("Brief")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Prompt"));
    await waitFor(() => expect(screen.getByText("Lint")).toBeInTheDocument());
    // Override lint mock for this specific call
    mockV1.lintPrompt.mockResolvedValue({
      required_fix: [{ section: "Deliverables", message: "No bullets" }],
      nice_to_have: [],
      acceptable_risk: [],
    });
    fireEvent.click(screen.getByText("Lint"));
    await waitFor(() => {
      expect(screen.getByText(/No bullets/)).toBeInTheDocument();
    });
  });
});

describe("Devil's Advocate gate", () => {
  it("publish disabled when required_fix > 0", async () => {
    setupDetailMocks("approved-show", "approved");
    mockV1.lintPrompt.mockResolvedValue({
      required_fix: [{ section: "Constraints", message: "Missing" }],
      nice_to_have: [],
      acceptable_risk: [],
    });

    renderAtRoute("/design/approved-show");
    await waitFor(() => expect(screen.getByText("Publish")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Publish"));
    await waitFor(() => {
      expect(screen.getByText("Confirm Publish")).toBeDisabled();
    });
  });

  it("publish enabled when lint clean and all checkboxes checked", async () => {
    setupDetailMocks("approved-show", "approved");
    mockV1.publishThread.mockResolvedValue({ status: "published" });

    renderAtRoute("/design/approved-show");
    await waitFor(() => expect(screen.getByText("Publish")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Publish"));

    await waitFor(() => expect(screen.getByText("Confirm Publish")).toBeInTheDocument());

    const checkboxes = screen.getAllByRole("checkbox");
    checkboxes.forEach(cb => fireEvent.click(cb));

    await waitFor(() => {
      expect(screen.getByText("Confirm Publish")).not.toBeDisabled();
    });
  });

  it("publish calls publishThread", async () => {
    setupDetailMocks("approved-show", "approved");
    mockV1.publishThread.mockResolvedValue({ status: "published" });

    renderAtRoute("/design/approved-show");
    await waitFor(() => expect(screen.getByText("Publish")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Publish"));

    await waitFor(() => expect(screen.getByText("Confirm Publish")).toBeInTheDocument());
    const checkboxes = screen.getAllByRole("checkbox");
    checkboxes.forEach(cb => fireEvent.click(cb));

    fireEvent.click(screen.getByText("Confirm Publish"));
    await waitFor(() => {
      expect(mockV1.publishThread).toHaveBeenCalledWith("approved-show");
    });
  });
});
