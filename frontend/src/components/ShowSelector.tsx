import { useState } from "react";
import { useShow } from "../contexts/ShowContext";
import * as api from "../services/api";
import type { Show } from "../types";

export function ShowSelector() {
  const { activeShow, setActiveShow, shows, refreshShows } = useShow();
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [open, setOpen] = useState(false);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    const show = (await api.createShow(newTitle.trim())) as Show;
    setNewTitle("");
    setCreating(false);
    await refreshShows();
    setActiveShow(show);
  };

  const handleActivate = async () => {
    if (!activeShow) return;
    const result = (await api.activateShow(activeShow.id)) as { id: string; status: string; corps_id: string };
    await refreshShows();
    // Refresh the active show to get corps_id
    const updated = shows.find((s) => s.id === activeShow.id);
    if (updated) {
      setActiveShow({ ...updated, status: result.status as Show["status"], corps_id: result.corps_id });
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "active": return "var(--success)";
      case "completed": return "var(--info)";
      case "draft": return "var(--text-muted)";
      default: return "var(--text-secondary)";
    }
  };

  return (
    <div className="show-selector" style={{ position: "relative", display: "flex", gap: 8, alignItems: "center" }}>
      <button onClick={() => setOpen(!open)} style={{ minWidth: 180, textAlign: "left" }}>
        {activeShow ? (
          <span>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor(activeShow.status), display: "inline-block", marginRight: 6 }} />
            {activeShow.title}
          </span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>Select Show...</span>
        )}
      </button>

      {activeShow?.status === "draft" && (
        <button className="primary" onClick={handleActivate}>Activate</button>
      )}

      {open && (
        <div style={{
          position: "absolute", top: "100%", left: 0, zIndex: 100,
          background: "var(--bg-card)", border: "1px solid var(--border)",
          borderRadius: 8, padding: 8, minWidth: 240, marginTop: 4,
          boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
        }}>
          {shows.map((s) => (
            <button
              key={s.id}
              onClick={() => { setActiveShow(s); setOpen(false); }}
              style={{
                display: "block", width: "100%", textAlign: "left", padding: "6px 10px",
                background: s.id === activeShow?.id ? "var(--bg-hover)" : "transparent",
                border: "none", borderRadius: 4,
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor(s.status), display: "inline-block", marginRight: 6 }} />
              {s.title}
              <span style={{ color: "var(--text-muted)", fontSize: 11, marginLeft: 8 }}>{s.status}</span>
            </button>
          ))}

          {creating ? (
            <div style={{ display: "flex", gap: 4, marginTop: 8 }}>
              <input
                autoFocus
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                placeholder="Show title..."
                style={{
                  flex: 1, padding: "4px 8px", background: "var(--bg-primary)",
                  border: "1px solid var(--border)", borderRadius: 4,
                  color: "var(--text-primary)", fontSize: 13,
                }}
              />
              <button onClick={handleCreate} style={{ padding: "4px 8px", fontSize: 12 }}>Add</button>
            </div>
          ) : (
            <button
              onClick={() => setCreating(true)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 10px", marginTop: 4, color: "var(--accent)", background: "transparent", border: "none" }}
            >
              + New Show
            </button>
          )}
        </div>
      )}
    </div>
  );
}
