import { NavLink } from "react-router-dom";

const LIFECYCLE_ITEMS = [
  { to: "/design", label: "Design Room", icon: "DSN", color: "var(--stage-design)" },
  { to: "/shows", label: "Show Library", icon: "LIB", color: "var(--stage-library)" },
  { to: "/seasons", label: "Season Workshop", icon: "SZN", color: "var(--stage-season)" },
  { to: "/tour", label: "On Tour", icon: "TUR", color: "var(--stage-tour)" },
  { to: "/finals", label: "Finals", icon: "FIN", color: "var(--stage-finals)" },
] as const;

const UTILITY_ITEMS = [
  { to: "/corps", label: "Corps Garage", icon: "CRP" },
  { to: "/", label: "Command Center", icon: "CMD", end: true },
  { to: "/settings", label: "Settings", icon: "CFG" },
] as const;

export function SideNav() {
  return (
    <nav className="side-nav">
      <div className="side-nav-section-label">LIFECYCLE</div>
      {LIFECYCLE_ITEMS.map((s, i) => (
        <NavLink
          key={s.to}
          to={s.to}
          className={({ isActive }) => `side-nav-item ${isActive ? "active" : ""}`}
          style={{ "--stage-color": s.color } as React.CSSProperties}
        >
          <span className="side-nav-stage-num">{i + 1}</span>
          <span className="side-nav-icon" style={{ color: s.color }}>{s.icon}</span>
          <span className="side-nav-label">{s.label}</span>
        </NavLink>
      ))}
      <div className="side-nav-divider" />
      <div className="side-nav-section-label">UTILITIES</div>
      {UTILITY_ITEMS.map(s => (
        <NavLink
          key={s.to}
          to={s.to}
          end={"end" in s ? s.end : false}
          className={({ isActive }) => `side-nav-item ${isActive ? "active" : ""}`}
        >
          <span className="side-nav-icon">{s.icon}</span>
          <span className="side-nav-label">{s.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
