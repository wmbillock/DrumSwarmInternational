import { useState } from "react";
import { ThemeProvider, useTheme } from "./contexts/ThemeContext";
import { CorpsThemeProvider } from "./contexts/CorpsThemeContext";
import { ShowProvider, useShow } from "./contexts/ShowContext";
import { CorpsThemePicker } from "./components/CorpsThemePicker";
import { ShowSelector } from "./components/ShowSelector";
import { ChatRoom } from "./components/ChatRoom";
import { ProjectState } from "./components/ProjectState";
import { CorpsDetail } from "./components/CorpsDetail";
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

type DetailView =
  | { type: "corps" }
  | { type: "roster" }
  | { type: "field" }
  | { type: "reps" }
  | { type: "chart" }
  | { type: "tape" }
  | { type: "met" }
  | { type: "sheets" }
  | { type: "books" }
  | { type: "stand" }
  | { type: "lot" }
  | { type: "basics" }
  | { type: "critique" }
  | { type: "banquet" }
  | { type: "coordinate"; id: string }
  | { type: "session"; id: string }
  | null;

const DETAIL_ITEMS: { id: string; label: string }[] = [
  { id: "corps", label: "Corps Detail" },
  { id: "roster", label: "Roster" },
  { id: "field", label: "Field" },
  { id: "reps", label: "Reps" },
  { id: "sheets", label: "Sheets" },
  { id: "chart", label: "Chart" },
  { id: "tape", label: "Tape" },
  { id: "met", label: "Met" },
  { id: "books", label: "Books" },
  { id: "stand", label: "Stand" },
  { id: "lot", label: "Lot" },
  { id: "basics", label: "Basics" },
  { id: "critique", label: "Critique" },
  { id: "banquet", label: "Banquet" },
];

function AppContent() {
  const { theme, toggleTheme } = useTheme();
  const { corpsId, rootCoordId } = useShow();
  const [detailView, setDetailView] = useState<DetailView>({ type: "corps" });
  const [detailOpen, setDetailOpen] = useState(true);

  const handleSelectItem = (itemType: string, id: string) => {
    if (itemType === "coordinate") {
      setDetailView({ type: "coordinate", id });
    } else if (itemType === "session") {
      setDetailView({ type: "session", id });
    }
    setDetailOpen(true);
  };

  const renderDetail = () => {
    if (!detailView) return null;

    switch (detailView.type) {
      case "corps": return <CorpsDetail />;
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
      case "coordinate": return <TheField rootCoordinateId={detailView.id} />;
      case "session": return <CorpsDetail />;
      default: return null;
    }
  };

  return (
    <div className={`app ${theme}`}>
      {/* Header */}
      <header className="app-header">
        <h1 className="app-title">DCI Swarm</h1>
        <div className="header-controls">
          <ShowSelector />
          <CorpsThemePicker />
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      {/* Three-panel layout */}
      <div className="app-layout-3">
        {/* Left: Project State */}
        <aside className="panel-left">
          <ProjectState onSelectItem={handleSelectItem} />
        </aside>

        {/* Center: Chat Room */}
        <main className="panel-center">
          <ChatRoom />
        </main>

        {/* Right: Detail Panel */}
        {detailOpen && (
          <aside className="panel-right">
            <div className="detail-header">
              <div className="detail-tabs">
                {DETAIL_ITEMS.map((item) => (
                  <button
                    key={item.id}
                    className={`detail-tab ${detailView?.type === item.id ? "active" : ""}`}
                    onClick={() => setDetailView({ type: item.id } as DetailView)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <button
                className="detail-close"
                onClick={() => setDetailOpen(false)}
                title="Close detail panel"
              >
                &times;
              </button>
            </div>
            <div className="detail-content">
              {renderDetail()}
            </div>
          </aside>
        )}

        {!detailOpen && (
          <button
            className="panel-open-btn"
            onClick={() => setDetailOpen(true)}
            title="Open detail panel"
          >
            &laquo;
          </button>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <CorpsThemeProvider>
        <ShowProvider>
          <AppContent />
        </ShowProvider>
      </CorpsThemeProvider>
    </ThemeProvider>
  );
}
