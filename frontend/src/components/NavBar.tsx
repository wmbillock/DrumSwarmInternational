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
        <NavLink to="/corps" className={({ isActive }) => isActive ? "nav-active small" : "small"}>Corps</NavLink>
        <NavLink to="/shows" className={({ isActive }) => isActive ? "nav-active small" : "small"}>Shows</NavLink>
        <NavLink to="/design" className={({ isActive }) => isActive ? "nav-active small" : "small"}>Design Room</NavLink>
        <NavLink to="/seasons" className={({ isActive }) => isActive ? "nav-active small" : "small"}>DCI Office</NavLink>
        <NavLink to="/scoreboards" className={({ isActive }) => isActive ? "nav-active small" : "small"}>Performance Stats</NavLink>
        <NavLink to="/system" className={({ isActive }) => isActive ? "nav-active small" : "small"}>System</NavLink>
        <NavLink to="/messages/inbox" className={({ isActive }) => isActive ? "nav-active small" : "small"}>
          Messages{unreadCount > 0 && <span className="badge">{unreadCount}</span>}
        </NavLink>
        <NavLink to="/" end className={({ isActive }) => isActive ? "nav-active small" : "small"}>Command Center</NavLink>
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
