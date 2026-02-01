import { useEffect, useState } from "react";
import { Panel } from "../ui";

interface SystemConfig {
  [key: string]: unknown;
}

export function Settings() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
    fetch(`${base}/api/system-health`)
      .then((r) => r.json())
      .then(setConfig)
      .catch(() => setConfig({}))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">Loading settings...</div>;

  return (
    <div className="page-content">
      <h2 className="page-title">System Settings</h2>
      <Panel title="Runtime Configuration">
        <div className="code-block">
          <pre>{JSON.stringify(config, null, 2)}</pre>
        </div>
      </Panel>
      <Panel title="Environment" className="mt-16">
        <table className="styled-table">
          <tbody>
            <tr>
              <td className="cell-primary">API URL</td>
              <td className="mono">{import.meta.env.VITE_API_URL || "http://localhost:8000"}</td>
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
