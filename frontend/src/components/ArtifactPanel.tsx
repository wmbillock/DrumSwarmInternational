import { useState } from "react";
import { SpecViewer } from "./SpecViewer";
import { PromptEditor } from "./PromptEditor";
import { VersionList } from "./VersionList";

type Tab = "brief" | "prompt" | "versions";

interface Props {
  showSlug: string;
  specContent: string;
  onRefresh: () => void;
  refreshKey?: number;
}

export function ArtifactPanel({ showSlug, specContent, onRefresh, refreshKey }: Props) {
  const [tab, setTab] = useState<Tab>("brief");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{
        display: "flex", gap: 0, borderBottom: "1px solid var(--border)",
        background: "var(--bg-secondary)",
      }}>
        {(["brief", "prompt", "versions"] as Tab[]).map(t => (
          <button
            key={t}
            className={`small ${tab === t ? "primary" : ""}`}
            onClick={() => setTab(t)}
            style={{
              borderRadius: 0,
              borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
              padding: "8px 16px",
            }}
          >
            {t === "brief" ? "Brief" : t === "prompt" ? "Prompt" : "Versions"}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflow: "hidden" }}>
        {tab === "brief" && <SpecViewer showSlug={showSlug} content={specContent} onRefresh={onRefresh} />}
        {tab === "prompt" && <PromptEditor showSlug={showSlug} refreshKey={refreshKey} />}
        {tab === "versions" && <VersionList showSlug={showSlug} />}
      </div>
    </div>
  );
}
