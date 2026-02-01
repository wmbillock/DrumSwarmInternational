import { useState, useEffect, useCallback } from "react";
import * as v1 from "../services/v1";
import type { Show } from "../types";

export function TheSeason() {
  const [shows, setShows] = useState<Show[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const loadShows = useCallback(async () => {
    const data = await v1.listDBShows();
    setShows(data as Show[]);
  }, []);

  useEffect(() => { loadShows(); }, [loadShows]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    await v1.createShow({ title: newTitle, description: newDesc || undefined });
    setNewTitle("");
    setNewDesc("");
    loadShows();
  };

  const handleActivate = async (id: string) => {
    await v1.activateShow(id);
    loadShows();
  };

  const handleTour = async (id: string, enable: boolean) => {
    await v1.toggleTour(id, enable);
    loadShows();
  };

  const handleComplete = async (id: string) => {
    await v1.completeShow(id);
    loadShows();
  };

  return (
    <div className="screen">
      <h2>The Season</h2>
      <p className="subtitle">Show management, corps lifecycle, tour toggle</p>

      <div className="create-form">
        <input
          placeholder="Show title"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
        />
        <input
          placeholder="Description (optional)"
          value={newDesc}
          onChange={(e) => setNewDesc(e.target.value)}
        />
        <button onClick={handleCreate}>Create Show</button>
      </div>

      <div className="card-list">
        {shows.map((show) => (
          <div key={show.id} className={`card status-${show.status}`}>
            <h3>{show.title}</h3>
            <span className="badge">{show.status}</span>
            {show.corps_id && <span className="badge secondary">Corps active</span>}
            <div className="card-actions">
              {show.status === "draft" && (
                <button onClick={() => handleActivate(show.id)}>Activate</button>
              )}
              {show.status === "active" && (
                <>
                  <button onClick={() => handleTour(show.id, true)}>Start Tour</button>
                  <button onClick={() => handleComplete(show.id)}>Complete</button>
                </>
              )}
            </div>
          </div>
        ))}
        {shows.length === 0 && <p className="empty">No shows yet. Create one above.</p>}
      </div>
    </div>
  );
}
