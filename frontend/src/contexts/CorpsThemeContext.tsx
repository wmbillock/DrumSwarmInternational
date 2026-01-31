import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

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

// Real DCI corps color schemes
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
    primary: "#003DA5",
    secondary: "#FFD100",
    accent: "#FFD100",
    background: "#001233",
    surface: "#001845",
    text: "#E8E8E8",
    textSecondary: "#A0B4D0",
    border: "#003060",
    success: "#4CAF50",
    warning: "#FFD100",
    danger: "#EF5350",
  },
  carolina_crown: {
    id: "carolina_crown",
    name: "Carolina Crown",
    location: "Fort Mill, SC",
    primary: "#006D6F",
    secondary: "#000000",
    accent: "#00BCD4",
    background: "#001A1A",
    surface: "#002626",
    text: "#E0F2F1",
    textSecondary: "#80CBC4",
    border: "#004D40",
    success: "#00E676",
    warning: "#FFD740",
    danger: "#FF5252",
  },
  phantom_regiment: {
    id: "phantom_regiment",
    name: "Phantom Regiment",
    location: "Rockford, IL",
    primary: "#800020",
    secondary: "#1A1A1A",
    accent: "#C41E3A",
    background: "#0D0000",
    surface: "#1A0A0A",
    text: "#F5E6E8",
    textSecondary: "#C4A0A8",
    border: "#3D1A22",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#C41E3A",
  },
  santa_clara_vanguard: {
    id: "santa_clara_vanguard",
    name: "Santa Clara Vanguard",
    location: "Santa Clara, CA",
    primary: "#006341",
    secondary: "#8B6914",
    accent: "#D4AF37",
    background: "#001A0E",
    surface: "#002618",
    text: "#E8F5E9",
    textSecondary: "#A5D6A7",
    border: "#1B5E20",
    success: "#66BB6A",
    warning: "#D4AF37",
    danger: "#EF5350",
  },
  the_cadets: {
    id: "the_cadets",
    name: "The Cadets",
    location: "Allentown, PA",
    primary: "#B22234",
    secondary: "#FFFFFF",
    accent: "#3C3B6E",
    background: "#0A0A14",
    surface: "#14142A",
    text: "#EAEAF0",
    textSecondary: "#9E9EBE",
    border: "#2A2A50",
    success: "#4CAF50",
    warning: "#FF9800",
    danger: "#B22234",
  },
  bluecoats: {
    id: "bluecoats",
    name: "Bluecoats",
    location: "Canton, OH",
    primary: "#1E3A5F",
    secondary: "#C0C0C0",
    accent: "#4A90D9",
    background: "#0A1628",
    surface: "#122240",
    text: "#D6E4F0",
    textSecondary: "#8AAED0",
    border: "#1E3A5F",
    success: "#4CAF50",
    warning: "#FFB300",
    danger: "#EF5350",
  },
  blue_stars: {
    id: "blue_stars",
    name: "Blue Stars",
    location: "La Crosse, WI",
    primary: "#0047AB",
    secondary: "#FFFFFF",
    accent: "#4169E1",
    background: "#000A1A",
    surface: "#001333",
    text: "#D6E4F8",
    textSecondary: "#8AAED0",
    border: "#002266",
    success: "#43A047",
    warning: "#FFC107",
    danger: "#E53935",
  },
  boston_crusaders: {
    id: "boston_crusaders",
    name: "Boston Crusaders",
    location: "Boston, MA",
    primary: "#8B0000",
    secondary: "#000000",
    accent: "#DC143C",
    background: "#0D0000",
    surface: "#1A0808",
    text: "#F0E0E0",
    textSecondary: "#C09090",
    border: "#3A1010",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#DC143C",
  },
  mandarins: {
    id: "mandarins",
    name: "Mandarins",
    location: "Sacramento, CA",
    primary: "#FF6600",
    secondary: "#000000",
    accent: "#FF8C00",
    background: "#1A0A00",
    surface: "#261400",
    text: "#FFF3E0",
    textSecondary: "#FFAB60",
    border: "#4D2600",
    success: "#66BB6A",
    warning: "#FF6600",
    danger: "#D32F2F",
  },
  crossmen: {
    id: "crossmen",
    name: "Crossmen",
    location: "San Antonio, TX",
    primary: "#4B0082",
    secondary: "#FFD700",
    accent: "#9370DB",
    background: "#0D0018",
    surface: "#180030",
    text: "#E8D8F8",
    textSecondary: "#B090D0",
    border: "#2E0054",
    success: "#66BB6A",
    warning: "#FFD700",
    danger: "#EF5350",
  },
  colts: {
    id: "colts",
    name: "Colts",
    location: "Dubuque, IA",
    primary: "#006400",
    secondary: "#FFFFFF",
    accent: "#32CD32",
    background: "#001A00",
    surface: "#002600",
    text: "#E8F5E9",
    textSecondary: "#A5D6A7",
    border: "#1B5E20",
    success: "#32CD32",
    warning: "#FFD740",
    danger: "#EF5350",
  },
  troopers: {
    id: "troopers",
    name: "Troopers",
    location: "Casper, WY",
    primary: "#DAA520",
    secondary: "#000000",
    accent: "#FFD700",
    background: "#1A1400",
    surface: "#261E00",
    text: "#FFF8E1",
    textSecondary: "#D4C090",
    border: "#4D3D00",
    success: "#66BB6A",
    warning: "#DAA520",
    danger: "#EF5350",
  },
  pioneer: {
    id: "pioneer",
    name: "Pioneer",
    location: "Milwaukee, WI",
    primary: "#2E7D32",
    secondary: "#C8A415",
    accent: "#D4AF37",
    background: "#0A1A0A",
    surface: "#142814",
    text: "#E8F5E9",
    textSecondary: "#A5D6A7",
    border: "#1B5E20",
    success: "#43A047",
    warning: "#D4AF37",
    danger: "#E53935",
  },
  glassmen: {
    id: "glassmen",
    name: "The Glassmen",
    location: "Toledo, OH",
    primary: "#1A1A1A",
    secondary: "#CFB53B",
    accent: "#CFB53B",
    background: "#0A0A00",
    surface: "#14140A",
    text: "#F5F5DC",
    textSecondary: "#CFBF90",
    border: "#3D3D1A",
    success: "#66BB6A",
    warning: "#CFB53B",
    danger: "#EF5350",
  },
  kilties: {
    id: "kilties",
    name: "The Kilties",
    location: "Racine, WI",
    // Buchanan Modern tartan: bright yellow, red, orange, black
    primary: "#FFD700",
    secondary: "#CC2200",
    accent: "#E87A00",
    background: "#0A0A0A",
    surface: "#1A1A1A",
    text: "#F5F0E0",
    textSecondary: "#B0A080",
    border: "#3A2A10",
    success: "#E87A00",
    warning: "#FFD700",
    danger: "#CC2200",
  },
  sacramento_freelancers: {
    id: "sacramento_freelancers",
    name: "Sacramento Freelancers",
    location: "Sacramento, CA",
    primary: "#B71C1C",
    secondary: "#C0C0C0",
    accent: "#E53935",
    background: "#0D0808",
    surface: "#1A1010",
    text: "#F0E0E0",
    textSecondary: "#C0A0A0",
    border: "#3A1818",
    success: "#66BB6A",
    warning: "#FFA726",
    danger: "#B71C1C",
  },
};

interface CorpsThemeContextValue {
  corpsTheme: CorpsTheme;
  setCorpsTheme: (id: string) => void;
  availableThemes: CorpsTheme[];
}

const CorpsThemeContext = createContext<CorpsThemeContextValue>({
  corpsTheme: CORPS_THEMES.default,
  setCorpsTheme: () => {},
  availableThemes: Object.values(CORPS_THEMES),
});

export function CorpsThemeProvider({ children }: { children: ReactNode }) {
  const [themeId, setThemeId] = useState(() => {
    return localStorage.getItem("dci-corps-theme") || "default";
  });

  const corpsTheme = CORPS_THEMES[themeId] || CORPS_THEMES.default;

  useEffect(() => {
    localStorage.setItem("dci-corps-theme", themeId);

    // Apply theme to CSS custom properties
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
  }, [themeId, corpsTheme]);

  return (
    <CorpsThemeContext.Provider
      value={{
        corpsTheme,
        setCorpsTheme: setThemeId,
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
