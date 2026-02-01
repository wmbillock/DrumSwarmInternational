import { useEffect, useState } from "react";
import * as v1 from "../services/v1";

interface CompetitionFormProps {
  onCreated: (comp: v1.V1Competition) => void;
  onCancel: () => void;
}

export function CompetitionForm({ onCreated, onCancel }: CompetitionFormProps) {
  const [threads, setThreads] = useState<v1.V1Thread[]>([]);
  const [corps, setCorps] = useState<v1.V1Corps[]>([]);
  const [seasons, setSeasons] = useState<v1.V1Season[]>([]);
  const [seasonId, setSeasonId] = useState("");
  const [showSlug, setShowSlug] = useState("");
  const [selectedCorps, setSelectedCorps] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const ac = new AbortController();
    v1.listThreads(ac.signal)
      .then((t) => setThreads(t.filter((th) => th.status === "approved" || th.status === "published")))
      .catch(() => {});
    v1.listCorps(ac.signal)
      .then(setCorps)
      .catch(() => {});
    v1.listSeasons(ac.signal)
      .then(setSeasons)
      .catch(() => {});
    return () => ac.abort();
  }, []);

  const toggleCorps = (id: string) => {
    setSelectedCorps((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    if (!seasonId || !showSlug || selectedCorps.length === 0) {
      setError("Season, show, and at least one corps are required.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const comp = await v1.createCompetition({
        season_id: seasonId,
        show_slug: showSlug,
        corps_ids: selectedCorps,
      });
      onCreated(comp);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create competition");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="competition-form">
      <h3>Create Competition</h3>
      {error && <div className="error-banner">{error}</div>}

      <label className="form-label">
        Season
        <select className="form-input" value={seasonId} onChange={(e) => setSeasonId(e.target.value)}>
          <option value="">Select a season...</option>
          {seasons.map((s) => (
            <option key={s.season_id} value={s.season_id}>
              {s.season_id}
            </option>
          ))}
        </select>
      </label>

      <label className="form-label">
        Show
        <select className="form-input" value={showSlug} onChange={(e) => setShowSlug(e.target.value)}>
          <option value="">Select a show...</option>
          {threads.map((t) => (
            <option key={t.slug} value={t.slug}>
              {t.slug} ({t.status})
            </option>
          ))}
        </select>
      </label>

      <fieldset className="form-fieldset">
        <legend>Corps</legend>
        {corps.length === 0 && <span className="text-muted">No corps available</span>}
        {corps.map((c) => (
          <label key={c.corps_id} className="form-checkbox">
            <input
              type="checkbox"
              checked={selectedCorps.includes(c.corps_id)}
              onChange={() => toggleCorps(c.corps_id)}
            />
            {c.display_name}
          </label>
        ))}
      </fieldset>

      <div className="form-actions">
        <button className="primary" onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Creating..." : "Create"}
        </button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}
