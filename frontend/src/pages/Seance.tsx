import { useState } from "react";
import * as api from "../services/api";

export function Seance() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleQuery = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await api.querySeance(query);
      setResult(res);
    } catch (e: any) {
      setResult({ error: e.message });
    }
    setLoading(false);
  };

  return (
    <div className="page-content">
      <h2>Seance</h2>
      <p className="dim">Ask questions about the swarm's history and state.</p>
      <div className="seance-input-row">
        <input
          value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleQuery()}
          placeholder="Ask the swarm..."
        />
        <button className="primary" onClick={handleQuery} disabled={loading}>
          {loading ? "..." : "Ask"}
        </button>
      </div>
      {result && (
        <div className="detail-panel">
          {result.error
            ? <p className="hint warning">{result.error}</p>
            : <pre className="code-block">{JSON.stringify(result, null, 2)}</pre>
          }
        </div>
      )}
    </div>
  );
}
