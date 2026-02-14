import { useState, useEffect, useCallback } from "react";
import { NavLink } from "react-router-dom";
import { CorpsThemePicker } from "./CorpsThemePicker";
import { SystemHealth } from "./SystemHealth";
import * as v1 from "../services/v1";

const NAV_LINKS = [
  { to: "/corps", label: "Corps" },
  { to: "/shows", label: "Shows" },
  { to: "/design", label: "Design Room" },
  { to: "/seasons", label: "DCI Office" },
  { to: "/scoreboards", label: "Performance Stats" },
  { to: "/system", label: "System" },
] as const;

export function NavBar({
  theme,
  onToggleTheme,
}: {
  theme: "dark" | "light";
  onToggleTheme: () => void;
}) {
  const [unreadCount, setUnreadCount] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);

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
    const interval = setInterval(loadUnreadCount, 30000);

    return () => clearInterval(interval);
  }, []);

  // Close mobile nav on route change
  const closeMobile = useCallback(() => setMobileOpen(false), []);

  // Lock body scroll when mobile nav open
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  return (
    <header className="app-header">
      <NavLink to="/" className="app-title-link">
        <h1 className="app-title">DCI Swarm</h1>
      </NavLink>
      <nav className="header-nav">
        {NAV_LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} className={({ isActive }) => isActive ? "nav-active small" : "small"}>
            {l.label}
          </NavLink>
        ))}
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

      {/* Hamburger button — visible only on mobile via CSS */}
      <button
        className="hamburger-btn"
        onClick={() => setMobileOpen(true)}
        aria-label="Open navigation menu"
      >
        &#9776;
      </button>

      {/* Mobile nav drawer */}
      <div
        className={`mobile-nav-overlay${mobileOpen ? " open" : ""}`}
        onClick={closeMobile}
      >
        <div className="mobile-nav-drawer" onClick={(e) => e.stopPropagation()}>
          <div className="mobile-nav-header">
            <span style={{ fontWeight: 600, fontSize: 16 }}>DCI Swarm</span>
            <button className="mobile-nav-close" onClick={closeMobile} aria-label="Close menu">
              &times;
            </button>
          </div>
          <div className="mobile-nav-links">
            <NavLink to="/" end onClick={closeMobile} className={({ isActive }) => isActive ? "nav-active" : ""}>
              Command Center
            </NavLink>
            {NAV_LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} onClick={closeMobile} className={({ isActive }) => isActive ? "nav-active" : ""}>
                {l.label}
              </NavLink>
            ))}
            <NavLink to="/tour" onClick={closeMobile} className={({ isActive }) => isActive ? "nav-active" : ""}>
              On Tour
            </NavLink>
            <NavLink to="/finals" onClick={closeMobile} className={({ isActive }) => isActive ? "nav-active" : ""}>
              Finals
            </NavLink>
            <NavLink to="/swarm-health" onClick={closeMobile} className={({ isActive }) => isActive ? "nav-active" : ""}>
              Swarm Health
            </NavLink>
            <NavLink to="/messages/inbox" onClick={closeMobile} className={({ isActive }) => isActive ? "nav-active" : ""}>
              Messages{unreadCount > 0 && <span className="badge" style={{ marginLeft: 6 }}>{unreadCount}</span>}
            </NavLink>
          </div>
          <div className="mobile-nav-controls">
            <CorpsThemePicker />
            <button className="theme-toggle" onClick={onToggleTheme} style={{ width: "100%" }}>
              {theme === "dark" ? "\u2600 Light" : "\u263D Dark"}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
