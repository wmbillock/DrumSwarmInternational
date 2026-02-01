import { NavLink } from "react-router-dom";

const LIFECYCLE_ITEMS = [
  { to: "/design", label: "Design Room", icon: "DSN", color: "var(--stage-design)", tooltip: "Create and iterate on show designs with AI staff" },
  { to: "/shows", label: "Show Library", icon: "LIB", color: "var(--stage-library)", tooltip: "Browse, approve, and publish all shows" },
  { to: "/seasons", label: "Season Workshop", icon: "SZN", color: "var(--stage-season)", tooltip: "Group shows into seasons and manage competitions" },
  { to: "/tour", label: "On Tour", icon: "TUR", color: "var(--stage-tour)", tooltip: "Monitor corps performing shows autonomously" },
  { to: "/finals", label: "Finals", icon: "FIN", color: "var(--stage-finals)", tooltip: "Review scores, rank performances, and crown champions" },
] as const;

const UTILITY_ITEMS = [
  { to: "/corps", label: "Corps Garage", icon: "CRP", tooltip: "Create and manage corps of AI agents" },
  { to: "/scoreboards", label: "Scoreboards", icon: "SCR", tooltip: "Leaderboards and performance metrics" },
  { to: "/messages/inbox", label: "Messages", icon: "MSG", tooltip: "Threaded messaging between agents and staff" },
  { to: "/", label: "Command Center", icon: "CMD", end: true, tooltip: "System overview and health dashboard" },
  { to: "/settings", label: "Settings", icon: "CFG", tooltip: "System configuration" },
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
      <div className="side-nav-section-label">UTILITIES</div>
      {UTILITY_ITEMS.map(s => (
        <NavLink
          key={s.to}
          to={s.to}
          end={"end" in s ? s.end : false}
          className={({ isActive }) => `side-nav-item ${isActive ? "active" : ""}`}
          data-tooltip-id="main"
          data-tooltip-content={s.tooltip}
          data-tooltip-place="right"
        >
          <span className="side-nav-icon">{s.icon}</span>
          <span className="side-nav-label">{s.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
