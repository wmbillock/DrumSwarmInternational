import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { NavBar } from "../components/NavBar";

export function AppLayout() {
  const [theme, setTheme] = useState<"dark" | "light">(() =>
    (localStorage.getItem("dci-theme") as "dark" | "light") || "dark"
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("dci-theme", theme);
  }, [theme]);

  return (
    <div className="app">
      <NavBar theme={theme} onToggleTheme={() => setTheme(t => t === "dark" ? "light" : "dark")} />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
