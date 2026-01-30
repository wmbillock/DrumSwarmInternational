import { useState } from "react";
import { ThemeProvider, useTheme } from "./contexts/ThemeContext";
import { CorpsThemeProvider } from "./contexts/CorpsThemeContext";
import { CorpsThemePicker } from "./components/CorpsThemePicker";
import { TheSeason } from "./components/TheSeason";
import { TheRoster } from "./components/TheRoster";
import { TheField } from "./components/TheField";
import { TheReps } from "./components/TheReps";
import { TheChart } from "./components/TheChart";
import { TheTape } from "./components/TheTape";
import { TheMet } from "./components/TheMet";
import { TheSheets } from "./components/TheSheets";
import { TheBooks } from "./components/TheBooks";
import { TheStand } from "./components/TheStand";
import { TheLot } from "./components/TheLot";
import { Basics } from "./components/Basics";
import { Critique } from "./components/Critique";
import { TheBanquet } from "./components/TheBanquet";
import "./App.css";

type Screen =
  | "season" | "roster" | "field" | "reps" | "chart"
  | "tape" | "met" | "sheets" | "books" | "stand"
  | "lot" | "basics" | "critique" | "banquet";

const NAV_ITEMS: { id: Screen; label: string; shortLabel: string }[] = [
  { id: "season", label: "The Season", shortLabel: "Season" },
  { id: "roster", label: "The Roster", shortLabel: "Roster" },
  { id: "field", label: "The Field", shortLabel: "Field" },
  { id: "reps", label: "The Reps", shortLabel: "Reps" },
  { id: "chart", label: "The Chart", shortLabel: "Chart" },
  { id: "tape", label: "The Tape", shortLabel: "Tape" },
  { id: "met", label: "The Met", shortLabel: "Met" },
  { id: "sheets", label: "The Sheets", shortLabel: "Sheets" },
  { id: "books", label: "The Books", shortLabel: "Books" },
  { id: "stand", label: "The Stand", shortLabel: "Stand" },
  { id: "lot", label: "The Lot", shortLabel: "Lot" },
  { id: "basics", label: "Basics", shortLabel: "Basics" },
  { id: "critique", label: "Critique", shortLabel: "Critique" },
  { id: "banquet", label: "The Banquet", shortLabel: "Banquet" },
];

function AppContent() {
  const { theme, toggleTheme } = useTheme();
  const [screen, setScreen] = useState<Screen>("season");
  const [corpsId, setCorpsId] = useState<string | null>(null);
  const [rootCoordId, setRootCoordId] = useState<string | null>(null);

  const renderScreen = () => {
    switch (screen) {
      case "season": return <TheSeason />;
      case "roster": return <TheRoster corpsId={corpsId} />;
      case "field": return <TheField rootCoordinateId={rootCoordId} />;
      case "reps": return <TheReps corpsId={corpsId} />;
      case "chart": return <TheChart corpsId={corpsId} />;
      case "tape": return <TheTape corpsId={corpsId} />;
      case "met": return <TheMet corpsId={corpsId} />;
      case "sheets": return <TheSheets corpsId={corpsId} />;
      case "books": return <TheBooks corpsId={corpsId} />;
      case "stand": return <TheStand corpsId={corpsId} />;
      case "lot": return <TheLot corpsId={corpsId} />;
      case "basics": return <Basics corpsId={corpsId} />;
      case "critique": return <Critique corpsId={corpsId} />;
      case "banquet": return <TheBanquet corpsId={corpsId} />;
    }
  };

  return (
    <div className={`app ${theme}`}>
      <header className="app-header">
        <h1 className="app-title">DCI Swarm</h1>
        <div className="header-controls">
          <input
            className="corps-input"
            placeholder="Corps ID"
            value={corpsId || ""}
            onChange={(e) => setCorpsId(e.target.value || null)}
          />
          <input
            className="corps-input"
            placeholder="Root Coordinate ID"
            value={rootCoordId || ""}
            onChange={(e) => setRootCoordId(e.target.value || null)}
          />
          <CorpsThemePicker />
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>
      <div className="app-layout">
        <nav className="sidebar">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${screen === item.id ? "active" : ""}`}
              onClick={() => setScreen(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <main className="main-content">{renderScreen()}</main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <CorpsThemeProvider>
        <AppContent />
      </CorpsThemeProvider>
    </ThemeProvider>
  );
}
