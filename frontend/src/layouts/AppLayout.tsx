import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { Tooltip } from "react-tooltip";
import { NavBar } from "../components/NavBar";
import { SideNav } from "../components/SideNav";
import { TelemetryPanel } from "../components/TelemetryPanel";
import { CorpsThemeProvider } from "../contexts/CorpsThemeContext";
import { useCorpsContext } from "../hooks/useCorpsContext";

function AppLayoutInner() {
  const [theme, setTheme] = useState<"dark" | "light">(() =>
    (localStorage.getItem("dci-theme") as "dark" | "light") || "dark"
  );

  // Automatically manage corps theme based on route context
  useCorpsContext();

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("dci-theme", theme);
  }, [theme]);

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
