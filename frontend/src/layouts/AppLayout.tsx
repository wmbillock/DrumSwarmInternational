import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Tooltip } from "react-tooltip";
import { NavBar } from "../components/NavBar";
import { SideNav } from "../components/SideNav";
import { TelemetryPanel } from "../components/TelemetryPanel";
import { CorpsThemeProvider } from "../contexts/CorpsThemeContext";
import { useCorpsContext } from "../hooks/useCorpsContext";

function AppLayoutInner() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    try {
      return (localStorage.getItem("dci-theme") as "dark" | "light") || "dark";
    } catch {
      return "dark";
    }
  });

  const location = useLocation();

  // Automatically manage corps theme based on route context
  useCorpsContext();

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("dci-theme", theme);
    } catch {
      // localStorage unavailable
    }
  }, [theme]);

  // Set document title based on route
  useEffect(() => {
    const titles: Record<string, string> = {
      "/": "Command Center",
      "/design": "Design Room",
      "/shows": "Show Library",
      "/seasons": "Season Workshop",
      "/tour": "On Tour",
      "/finals": "Finals",
      "/corps": "Corps",
      "/swarm-health": "Swarm Health",
      "/system": "System Health",
      "/settings": "Settings",
      "/scoreboards": "Scoreboards",
      "/messages/inbox": "Messages",
      "/messages/archive": "Message Archive",
      "/messages/admin": "Message Admin",
      "/metrics/explorer": "Performance Explorer",
      "/judging": "Judging & Critique",
      "/evolution": "Evolution",
      "/staff": "Staff Marketplace",
      "/performers": "Performers",
      "/admin": "Admin",
    };
    const path = location.pathname;
    const exact = titles[path];
    if (exact) {
      document.title = `${exact} — DCI Swarm`;
    } else if (path.startsWith("/corps/")) {
      document.title = "Corps Detail — DCI Swarm";
    } else if (path.startsWith("/design/")) {
      document.title = "Design Room — DCI Swarm";
    } else if (path.startsWith("/tour/")) {
      document.title = "Competition — DCI Swarm";
    } else if (path.startsWith("/finals/")) {
      document.title = "Finals — DCI Swarm";
    } else if (path.startsWith("/seasons/")) {
      document.title = "Season Detail — DCI Swarm";
    } else {
      document.title = "DCI Swarm";
    }
  }, [location.pathname]);

  return (
    <div className="app">
      <NavBar theme={theme} onToggleTheme={() => setTheme(t => t === "dark" ? "light" : "dark")} />
      <div className="app-body app-body--3col">
        <SideNav />
        <main className="app-main">
          <Outlet />
        </main>
        <TelemetryPanel />
      </div>
      <Tooltip
        id="main"
        place="top"
        className="dci-tooltip"
        classNameArrow="dci-tooltip-arrow"
      />
    </div>
  );
}

export function AppLayout() {
  return (
    <CorpsThemeProvider>
      <AppLayoutInner />
    </CorpsThemeProvider>
  );
}
