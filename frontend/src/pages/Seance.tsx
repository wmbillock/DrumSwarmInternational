import { useState, useEffect } from "react";
import * as v1 from "../services/v1";

export function Seance() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [corps, setCorps] = useState<{ id: string; name: string }[]>([]);
  const [selectedCorps, setSelectedCorps] = useState("");

  useEffect(() => {
    v1.listCorps(undefined, true)
      .then((list) => {
        const items = list
          .filter((c: any) => c.corps_type !== "system")
          .map((c: any) => ({ id: c.corps_id || c.id, name: c.display_name || c.name }));
        setCorps(items);
        if (items.length > 0) setSelectedCorps(items[0].id);
      })
      .catch(() => {});
  }, []);

  const handleQuery = async () => {
    if (!query.trim() || !selectedCorps) return;
    setLoading(true);
    try {
      const res = await v1.seanceQuery(selectedCorps, query);
      setResult(res);
    } catch (e: any) {
      setResult({ error: e.message });
    }
    setLoading(false);
  };

  return (
    <div className="page-content">
      <h2>Seance — Ask the ED</h2>
      <p className="text-muted" style={{ marginBottom: 16 }}>
        Ask questions about a corps' history and state. The Executive Director will respond in character.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <select
          value={selectedCorps}
          onChange={(e) => setSelectedCorps(e.target.value)}
          style={{ minWidth: 200 }}
        >
          {corps.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleQuery()}
          placeholder="Ask the Executive Director..."
          style={{ flex: 1 }}
        />
        <button className="primary" onClick={handleQuery} disabled={loading || !selectedCorps}>
          {loading ? "Thinking..." : "Ask"}
        </button>
      </div>

      {result && (
        <div style={{ marginTop: 16 }}>
          {result.error ? (
            <div className="error-banner">{result.error}</div>
          ) : (
            <div style={{
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: 16,
              background: "var(--bg-elevated, rgba(255,255,255,0.03))",
            }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
                Executive Director responds:
              </div>
              <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                {result.message}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
