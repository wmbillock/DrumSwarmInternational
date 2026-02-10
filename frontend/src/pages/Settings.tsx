import { useEffect, useState } from "react";
import { Panel } from "../ui";
import * as v1 from "../services/v1";

interface SystemConfig {
  [key: string]: unknown;
}

export function Settings() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    v1.getSystemHealth()
      .then(setConfig)
      .catch(() => { setConfig(null); setError(true); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading settings...</div>;

  return (
    <div className="page-content">
      <h2 className="page-title">System Settings</h2>
      <Panel title="Runtime Configuration">
        {error ? (
          <p className="text-muted">Unable to load system health data. Is the backend running?</p>
        ) : config && Object.keys(config).length > 0 ? (
          <table className="styled-table">
            <thead><tr><th>Key</th><th>Value</th></tr></thead>
            <tbody>
              {Object.entries(config).map(([k, val]) => (
                <tr key={k}>
                  <td className="cell-primary">{k}</td>
                  <td className="mono">{typeof val === "object" ? JSON.stringify(val) : String(val ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-muted">No configuration data available.</p>
        )}
      </Panel>
      <Panel title="Environment" className="mt-16">
        <table className="styled-table">
          <tbody>
            <tr>
              <td className="cell-primary">API URL</td>
              <td className="mono">{import.meta.env.VITE_API_URL || "http://localhost:4224"}</td>
            </tr>
            <tr>
              <td className="cell-primary">Frontend Mode</td>
              <td>{import.meta.env.MODE}</td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
