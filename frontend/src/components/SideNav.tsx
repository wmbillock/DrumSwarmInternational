import { NavLink } from "react-router-dom";

const NAV_SECTIONS = [
  { to: "/", label: "Command Center", icon: "CMD", end: true },
  { to: "/shows", label: "Shows", icon: "SHW" },
  { to: "/corps", label: "Corps", icon: "CRP" },
  { to: "/runs", label: "Runs & Rehearsals", icon: "RUN" },
  { to: "/evolution", label: "Evolution & Talent", icon: "EVO" },
  { to: "/judging", label: "Judging & Critique", icon: "JDG" },
  { to: "/templates", label: "Templates", icon: "TPL" },
  { to: "/design", label: "Design Room", icon: "DSN" },
  { to: "/messages/inbox", label: "Messages", icon: "MSG" },
  { to: "/history", label: "Corps History", icon: "HST" },
  { to: "/seance", label: "Seance (Legacy)", icon: "QRY" },
  { to: "/competitions", label: "Competitions", icon: "CMP" },
  { to: "/seasons", label: "Seasons", icon: "SZN" },
  { to: "/system", label: "System Health", icon: "SYS" },
  { to: "/settings", label: "Settings", icon: "CFG" },
] as const;

export function SideNav() {
  return (
    <nav className="side-nav">
      {NAV_SECTIONS.map(s => (
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
