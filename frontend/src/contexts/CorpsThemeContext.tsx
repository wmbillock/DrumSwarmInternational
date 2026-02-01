import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

export interface CorpsTheme {
  id: string;
  name: string;
  location: string;
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  surface: string;
  text: string;
  textSecondary: string;
  border: string;
  success: string;
  warning: string;
  danger: string;
}

// Real DCI corps color schemes — colors match the canonical dci-colors.css spec
export const CORPS_THEMES: Record<string, CorpsTheme> = {
  default: {
    id: "default",
    name: "DCI Default",
    location: "",
    primary: "#58a6ff",
    secondary: "#8b949e",
    accent: "#58a6ff",
    background: "#0d1117",
    surface: "#161b22",
    text: "#e6edf3",
    textSecondary: "#8b949e",
    border: "#30363d",
    success: "#3fb950",
    warning: "#d29922",
    danger: "#f85149",
  },
  blue_devils: {
    id: "blue_devils",
    name: "Blue Devils",
    location: "Concord, CA",
    primary: "#0047AB",
    secondary: "#000000",
    accent: "#B7B9BC",
    background: "#001233",
    surface: "#001845",
    text: "#E8E8E8",
    textSecondary: "#A0B4D0",
    border: "#003060",
    success: "#4CAF50",
    warning: "#FFA726",
    danger: "#EF5350",
  },
  cavaliers: {
    id: "cavaliers",
    name: "The Cavaliers",
    location: "Rosemont, IL",
    primary: "#0B3D2E",
    secondary: "#000000",
    accent: "#FFFFFF",
    background: "#020F0A",
    surface: "#061A12",
    text: "#E0F0E8",
    textSecondary: "#90B8A0",
    border: "#0B3D2E",
    success: "#4CAF50",
    warning: "#FFA726",
    danger: "#EF5350",
  },
  the_cadets: {
    id: "the_cadets",
    name: "The Cadets",
    location: "Allentown, PA",
    primary: "#6E1F2B",
    secondary: "#F3E6CF",
    accent: "#F3E6CF",
    background: "#120810",
    surface: "#1E0E16",
    text: "#F3E6CF",
    textSecondary: "#C0A890",
    border: "#3A1520",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#6E1F2B",
  },
  santa_clara_vanguard: {
    id: "santa_clara_vanguard",
    name: "Santa Clara Vanguard",
    location: "Santa Clara, CA",
    primary: "#9E1B32",
    secondary: "#006341",
    accent: "#FFFFFF",
    background: "#0D0608",
    surface: "#1A0C10",
    text: "#F0E8EA",
    textSecondary: "#C0A0A8",
    border: "#3A1520",
    success: "#006341",
    warning: "#FFA726",
    danger: "#9E1B32",
  },
  phantom_regiment: {
    id: "phantom_regiment",
    name: "Phantom Regiment",
    location: "Rockford, IL",
    primary: "#000000",
    secondary: "#B1B3B3",
    accent: "#B1B3B3",
    background: "#0A0A0A",
    surface: "#151515",
    text: "#E8E8E8",
    textSecondary: "#B1B3B3",
    border: "#303030",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#EF5350",
  },
  bluecoats: {
    id: "bluecoats",
    name: "Bluecoats",
    location: "Canton, OH",
    primary: "#4F83C2",
    secondary: "#FFFFFF",
    accent: "#FFFFFF",
    background: "#0C1A2C",
    surface: "#142840",
    text: "#E8F0F8",
    textSecondary: "#90B8D8",
    border: "#2A4A6A",
    success: "#4CAF50",
    warning: "#FFB300",
    danger: "#EF5350",
  },
  carolina_crown: {
    id: "carolina_crown",
    name: "Carolina Crown",
    location: "Fort Mill, SC",
    primary: "#4B2E83",
    secondary: "#C5C7C9",
    accent: "#C5C7C9",
    background: "#0D0818",
    surface: "#180E30",
    text: "#E8E0F0",
    textSecondary: "#A090C0",
    border: "#2E1A54",
    success: "#66BB6A",
    warning: "#FFD740",
    danger: "#EF5350",
  },
  madison_scouts: {
    id: "madison_scouts",
    name: "Madison Scouts",
    location: "Madison, WI",
    primary: "#006A3F",
    secondary: "#C8102E",
    accent: "#FFFFFF",
    background: "#001A0E",
    surface: "#002618",
    text: "#E8F5E9",
    textSecondary: "#A5D6A7",
    border: "#004D2E",
    success: "#006A3F",
    warning: "#FFA726",
    danger: "#C8102E",
  },
  blue_stars: {
    id: "blue_stars",
    name: "Blue Stars",
    location: "La Crosse, WI",
    primary: "#0A1F44",
    secondary: "#FFFFFF",
    accent: "#C0C5C9",
    background: "#040C1A",
    surface: "#0A1530",
    text: "#D6E4F8",
    textSecondary: "#8AAED0",
    border: "#0A1F44",
    success: "#43A047",
    warning: "#FFC107",
    danger: "#E53935",
  },
  boston_crusaders: {
    id: "boston_crusaders",
    name: "Boston Crusaders",
    location: "Boston, MA",
    primary: "#B11226",
    secondary: "#000000",
    accent: "#B7B9BC",
    background: "#0D0000",
    surface: "#1A0808",
    text: "#F0E0E0",
    textSecondary: "#C09090",
    border: "#3A1010",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#B11226",
  },
  glassmen: {
    id: "glassmen",
    name: "The Glassmen",
    location: "Toledo, OH",
    primary: "#000000",
    secondary: "#C9A227",
    accent: "#B7B9BC",
    background: "#0A0A00",
    surface: "#14140A",
    text: "#F5F5DC",
    textSecondary: "#CFBF90",
    border: "#3D3D1A",
    success: "#66BB6A",
    warning: "#C9A227",
    danger: "#EF5350",
  },
  crossmen: {
    id: "crossmen",
    name: "Crossmen",
    location: "San Antonio, TX",
    primary: "#9E1B32",
    secondary: "#000000",
    accent: "#B7B9BC",
    background: "#0D0608",
    surface: "#1A0C10",
    text: "#F0E0E4",
    textSecondary: "#C0A0A8",
    border: "#3A1520",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#9E1B32",
  },
  colts: {
    id: "colts",
    name: "Colts",
    location: "Dubuque, IA",
    primary: "#B11226",
    secondary: "#000000",
    accent: "#EFE2C6",
    background: "#0D0000",
    surface: "#1A0808",
    text: "#EFE2C6",
    textSecondary: "#C0A890",
    border: "#3A1010",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#B11226",
  },
  pioneer: {
    id: "pioneer",
    name: "Pioneer",
    location: "Milwaukee, WI",
    primary: "#009A44",
    secondary: "#FFFFFF",
    accent: "#FF7A00",
    background: "#001A0A",
    surface: "#002814",
    text: "#E8F5E9",
    textSecondary: "#A5D6A7",
    border: "#1B5E20",
    success: "#009A44",
    warning: "#FF7A00",
    danger: "#E53935",
  },
  kilties: {
    id: "kilties",
    name: "Racine Kilties",
    location: "Racine, WI",
    // Buchanan Modern tartan: yellow, orange, red, black
    primary: "#FFD100",
    secondary: "#FF8C00",
    accent: "#C8102E",
    background: "#0A0A00",
    surface: "#1A1A08",
    text: "#F5F0E0",
    textSecondary: "#B0A080",
    border: "#3A2A10",
    success: "#FF8C00",
    warning: "#FFD100",
    danger: "#C8102E",
  },
  sacramento_freelancers: {
    id: "sacramento_freelancers",
    name: "Sacramento Freelancers",
    location: "Sacramento, CA",
    primary: "#000000",
    secondary: "#C8102E",
    accent: "#B7B9BC",
    background: "#0A0A0A",
    surface: "#151515",
    text: "#F0E0E0",
    textSecondary: "#C0A0A0",
    border: "#303030",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#C8102E",
  },
};

interface CorpsThemeContextValue {
  corpsTheme: CorpsTheme;
  setCorpsTheme: (id: string) => void;
  setCorpsThemeForContext: (id: string) => void;
  availableThemes: CorpsTheme[];
}

const CorpsThemeContext = createContext<CorpsThemeContextValue>({
  corpsTheme: CORPS_THEMES.default,
  setCorpsTheme: () => {},
  setCorpsThemeForContext: () => {},
  availableThemes: Object.values(CORPS_THEMES),
});

export function CorpsThemeProvider({ children }: { children: ReactNode }) {
  const location = useLocation();

  // User's preferred theme (set via theme picker in DCI overview mode)
  const [userThemeId, setUserThemeId] = useState(() => {
    return localStorage.getItem("dci-corps-theme") || "default";
  });

  // Currently active theme (may be overridden by context)
  const [activeThemeId, setActiveThemeId] = useState(userThemeId);

  // Track if we're in a corps-specific context
  const isCorpsContext = useRef(false);

  const corpsTheme = CORPS_THEMES[activeThemeId] || CORPS_THEMES.default;

  // Apply theme to CSS custom properties
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--bg-primary", corpsTheme.background);
    root.style.setProperty("--bg-secondary", corpsTheme.surface);
    root.style.setProperty("--bg-card", corpsTheme.surface);
    root.style.setProperty("--bg-hover", adjustBrightness(corpsTheme.surface, 15));
    root.style.setProperty("--text-primary", corpsTheme.text);
    root.style.setProperty("--text-secondary", corpsTheme.textSecondary);
    root.style.setProperty("--text-muted", adjustBrightness(corpsTheme.textSecondary, -20));
    root.style.setProperty("--border", corpsTheme.border);
    root.style.setProperty("--accent", corpsTheme.accent);
    root.style.setProperty("--accent-hover", adjustBrightness(corpsTheme.accent, 20));
    root.style.setProperty("--success", corpsTheme.success);
    root.style.setProperty("--warning", corpsTheme.warning);
    root.style.setProperty("--danger", corpsTheme.danger);
  }, [corpsTheme]);

  // Persist user theme preference
  useEffect(() => {
    localStorage.setItem("dci-corps-theme", userThemeId);
  }, [userThemeId]);

  // Auto-restore default theme when leaving corps context
  useEffect(() => {
    const wasInCorpsContext = isCorpsContext.current;
    const isInCorpsRoute = location.pathname.startsWith("/corps/") &&
                          location.pathname.split("/")[2]; // has corps id

    // Leaving corps context -> restore user's preferred theme
    if (wasInCorpsContext && !isInCorpsRoute) {
      setActiveThemeId(userThemeId);
      isCorpsContext.current = false;
    }

    // Update corps context flag
    if (isInCorpsRoute && !wasInCorpsContext) {
      isCorpsContext.current = true;
    }
  }, [location.pathname, userThemeId]);

  // Set user's persistent theme (from theme picker in DCI overview)
  const setCorpsTheme = (id: string) => {
    setUserThemeId(id);
    // Only apply immediately if not in a corps context
    if (!isCorpsContext.current) {
      setActiveThemeId(id);
    }
  };

  // Set theme for current context (used by corps pages)
  const setCorpsThemeForContext = (id: string) => {
    setActiveThemeId(id);
    isCorpsContext.current = true;
  };

  return (
    <CorpsThemeContext.Provider
      value={{
        corpsTheme,
        setCorpsTheme,
        setCorpsThemeForContext,
        availableThemes: Object.values(CORPS_THEMES),
      }}
    >
      {children}
    </CorpsThemeContext.Provider>
  );
}

export const useCorpsTheme = () => useContext(CorpsThemeContext);

// Utility: adjust hex color brightness
function adjustBrightness(hex: string, percent: number): string {
  const num = parseInt(hex.replace("#", ""), 16);
  const r = Math.min(255, Math.max(0, (num >> 16) + Math.round(2.55 * percent)));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00ff) + Math.round(2.55 * percent)));
  const b = Math.min(255, Math.max(0, (num & 0x0000ff) + Math.round(2.55 * percent)));
  return `#${(0x1000000 + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}
