import { useCorpsTheme } from "../contexts/CorpsThemeContext";

export function CorpsThemePicker() {
  const { corpsTheme, setCorpsTheme, availableThemes } = useCorpsTheme();

  return (
    <div className="theme-picker">
      <select
        value={corpsTheme.id}
        onChange={(e) => setCorpsTheme(e.target.value)}
        className="theme-select"
      >
        {availableThemes.map((theme) => (
          <option key={theme.id} value={theme.id}>
            {theme.name}
            {theme.location ? ` — ${theme.location}` : ""}
          </option>
        ))}
      </select>
      <div
        className="theme-preview"
        style={{
          display: "flex",
          gap: 4,
          marginLeft: 8,
        }}
      >
        <div
          className="swatch"
          style={{ background: corpsTheme.primary, width: 16, height: 16, borderRadius: 3 }}
          title="Primary"
        />
        <div
          className="swatch"
          style={{ background: corpsTheme.secondary, width: 16, height: 16, borderRadius: 3 }}
          title="Secondary"
        />
        <div
          className="swatch"
          style={{ background: corpsTheme.accent, width: 16, height: 16, borderRadius: 3 }}
          title="Accent"
        />
      </div>
    </div>
  );
}
