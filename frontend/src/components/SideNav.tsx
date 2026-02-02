import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import * as v1 from "../services/v1";
import { DSILogo } from "./DSILogo";

const LIFECYCLE_ITEMS = [
  { to: "/design", label: "Design Room", icon: "DSN", color: "var(--stage-design)", tooltip: "Create and iterate on show designs with AI staff" },
  { to: "/shows", label: "Show Library", icon: "LIB", color: "var(--stage-library)", tooltip: "Browse, approve, and publish all shows" },
  { to: "/seasons", label: "Season Workshop", icon: "SZN", color: "var(--stage-season)", tooltip: "Group shows into seasons and manage competitions" },
  { to: "/tour", label: "On Tour", icon: "TUR", color: "var(--stage-tour)", tooltip: "Monitor corps performing shows autonomously" },
  { to: "/finals", label: "Finals", icon: "FIN", color: "var(--stage-finals)", tooltip: "Review scores, rank performances, and crown champions" },
] as const;

export function SideNav() {
  const navigate = useNavigate();
  const [corps, setCorps] = useState<v1.V1Corps[]>([]);
  const [selectedCorps, setSelectedCorps] = useState("");

  useEffect(() => {
    v1.listCorps(undefined, true)
      .then(setCorps)
      .catch(() => {});
  }, []);

  const handleCorpsChange = (corpsId: string) => {
    setSelectedCorps(corpsId);
    if (corpsId) {
      navigate(`/corps/${corpsId}`);
    }
  };

  return (
    <nav className="side-nav">
      <DSILogo />
      <div className="side-nav-section-label">LIFECYCLE</div>
      {LIFECYCLE_ITEMS.map((s, i) => (
        <NavLink
          key={s.to}
          to={s.to}
          className={({ isActive }) => `side-nav-item ${isActive ? "active" : ""}`}
          style={{ "--stage-color": s.color } as React.CSSProperties}
          data-tooltip-id="main"
          data-tooltip-content={s.tooltip}
          data-tooltip-place="right"
        >
          <span className="side-nav-stage-num">{i + 1}</span>
          <span className="side-nav-icon" style={{ color: s.color }}>{s.icon}</span>
          <span className="side-nav-label">{s.label}</span>
        </NavLink>
      ))}
      <div className="side-nav-divider" />
      <div className="side-nav-section-label">CORPS</div>
      <div style={{ padding: "4px 12px" }}>
        <select
          className="corps-selector"
          value={selectedCorps}
          onChange={e => handleCorpsChange(e.target.value)}
          style={{
            width: "100%",
            padding: "6px 8px",
            background: "var(--bg-secondary, #1a1a2e)",
            color: "var(--text-primary, #e0e0e0)",
            border: "1px solid var(--border, #333)",
            borderRadius: 4,
            fontSize: "0.85rem",
          }}
        >
          <option value="">Select corps...</option>
          {corps.filter(c => c.corps_type !== "system").map(c => (
            <option key={c.corps_id} value={c.corps_id}>{c.display_name}</option>
          ))}
          {corps.filter(c => c.corps_type === "system").length > 0 && (
            <optgroup label="System">
              {corps.filter(c => c.corps_type === "system").map(c => (
                <option key={c.corps_id} value={c.corps_id}>{c.display_name}</option>
              ))}
            </optgroup>
          )}
        </select>
      </div>
    </nav>
  );
}
