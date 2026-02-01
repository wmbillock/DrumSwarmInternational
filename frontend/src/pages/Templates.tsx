import { useState, useEffect } from "react";
import * as v1 from "../services/v1";

function formatRole(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

export function Templates() {
  const [templates, setTemplates] = useState<string[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    v1.listTemplates().then((data: any) => {
      setTemplates(Array.isArray(data) ? data : data?.templates || []);
    }).catch(() => setTemplates([]));
  }, []);

  const handleInstantiate = async (name: string) => {
    try {
      await v1.instantiateTemplate(name, {});
      setMsg(`Created show from template "${name}"`);
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
  };

  const handleSelect = async (name: string) => {
    try {
      const detail = await v1.getTemplate(name);
      setSelected(detail);
    } catch { setSelected(null); }
  };

  return (
    <div className="page-content">
      <h2>Show Templates</h2>
      {msg && <p className="info-msg">{msg}</p>}
      <div className="card-grid">
        {templates.map(name => (
          <div key={name} className="card" onClick={() => handleSelect(name)}>
            <h3>{formatRole(name)}</h3>
            <button className="small primary" onClick={e => { e.stopPropagation(); handleInstantiate(name); }}>
              Create Show
            </button>
          </div>
        ))}
        {templates.length === 0 && <p className="dim">No templates available.</p>}
      </div>
      {selected && (
        <div className="detail-panel">
          <h3>{selected.name}</h3>
          <pre className="code-block">{JSON.stringify(selected, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
