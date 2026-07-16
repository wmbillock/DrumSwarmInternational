import { useState, useEffect, useCallback } from "react";
import * as v1 from "../services/v1";
import type { Show } from "../types";
import { SeasonRunSettings } from "./season/SeasonRunSettings";
import { SeasonRunTimeline } from "./season/SeasonRunTimeline";

export function TheSeason() {
  const [shows, setShows] = useState<Show[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [seasonRunName, setSeasonRunName] = useState("");
  const [regularShowCount, setRegularShowCount] = useState(4);
  const [winterCampCount, setWinterCampCount] = useState(7);
  const [seasonRunCorpsIds, setSeasonRunCorpsIds] = useState("");
  const [seasonRunError, setSeasonRunError] = useState("");
  const [seasonRunSummary, setSeasonRunSummary] = useState<v1.SeasonRunSummary | null>(null);

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

  const handleCreateSeasonRun = async () => {
    setSeasonRunError("");
    const corpsIds = seasonRunCorpsIds
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean);
    if (!seasonRunName.trim()) {
      setSeasonRunError("Season name is required.");
      return;
    }
    if (winterCampCount < 1 || winterCampCount > 7) {
      setSeasonRunError("Winter camps must be between 1 and 7.");
      return;
    }
    if (regularShowCount < 1) {
      setSeasonRunError("Regular shows must be at least 1.");
      return;
    }
    if (corpsIds.length === 0) {
      setSeasonRunError("At least one corps id is required.");
      return;
    }
    const summary = await v1.createSeasonRun({
      name: seasonRunName.trim(),
      regular_show_count: regularShowCount,
      winter_camp_count: winterCampCount,
      corps_ids: corpsIds,
    });
    setSeasonRunSummary(summary);
  };

  return (
    <div className="screen">
      <h2>The Season</h2>
      <p className="subtitle">Show management, corps lifecycle, tour toggle</p>

      <div className="create-form">
        <input
          placeholder="Season run name"
          value={seasonRunName}
          onChange={(e) => setSeasonRunName(e.target.value)}
        />
        <input
          placeholder="Corps ids, comma separated"
          value={seasonRunCorpsIds}
          onChange={(e) => setSeasonRunCorpsIds(e.target.value)}
        />
        <SeasonRunSettings
          regularShowCount={regularShowCount}
          winterCampCount={winterCampCount}
          onRegularShowCountChange={setRegularShowCount}
          onWinterCampCountChange={setWinterCampCount}
        />
        <button onClick={handleCreateSeasonRun}>Create Season Run</button>
      </div>

      {seasonRunError && <p className="error">{seasonRunError}</p>}
      {seasonRunSummary && <SeasonRunTimeline summary={seasonRunSummary} />}

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
