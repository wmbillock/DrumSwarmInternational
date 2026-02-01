import { NavLink } from "react-router-dom";
import { CorpsThemePicker } from "./CorpsThemePicker";
import { SystemHealth } from "./SystemHealth";

export function NavBar({
  theme,
  onToggleTheme,
}: {
  theme: "dark" | "light";
  onToggleTheme: () => void;
}) {
  return (
    <header className="app-header">
      <NavLink to="/" className="app-title-link">
        <h1 className="app-title">DCI Swarm</h1>
      </NavLink>
      <nav className="header-nav">
        <NavLink to="/" end className={({ isActive }) => isActive ? "nav-active small" : "small"}>
          Dashboard
        </NavLink>
        <NavLink to="/admin" className={({ isActive }) => isActive ? "nav-active small" : "small"}>
          Critique
        </NavLink>
        <NavLink to="/templates" className={({ isActive }) => isActive ? "nav-active small" : "small"}>
          Templates
        </NavLink>
        <NavLink to="/performers" className={({ isActive }) => isActive ? "nav-active small" : "small"}>
          Performers
        </NavLink>
        <NavLink to="/seance" className={({ isActive }) => isActive ? "nav-active small" : "small"}>
          Seance
        </NavLink>
      </nav>
      <SystemHealth />
      <div className="header-controls">
        <CorpsThemePicker />
        <button className="theme-toggle" onClick={onToggleTheme}>
          {theme === "dark" ? "\u2600 Light" : "\u263D Dark"}
        </button>
      </div>
    </header>
  );
}
