import { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { CorpsThemePicker } from "./CorpsThemePicker";
import { SystemHealth } from "./SystemHealth";
import * as v1 from "../services/v1";

export function NavBar({
  theme,
  onToggleTheme,
}: {
  theme: "dark" | "light";
  onToggleTheme: () => void;
}) {
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const loadUnreadCount = async () => {
      try {
        const result = await v1.getUnreadMessageCount();
        setUnreadCount(result.unread_count || 0);
      } catch (err) {
        // Silently fail if API not available
      }
    };

    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, []);

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
        <NavLink
          to="/messages/inbox"
          className={({ isActive }) => isActive ? "nav-active small" : "small"}
        >
          Messages {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
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
