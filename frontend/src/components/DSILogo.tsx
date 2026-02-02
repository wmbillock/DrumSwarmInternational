import { Link } from "react-router-dom";

export function DSILogo() {
  return (
    <Link to="/" className="dsi-logo-link" style={{ display: "block", padding: "16px 12px 8px", textDecoration: "none" }}>
      <svg viewBox="0 0 120 48" width="100%" height="48" xmlns="http://www.w3.org/2000/svg">
        {/* Diamond shield shape */}
        <path
          d="M24 4 L44 24 L24 44 L4 24 Z"
          fill="none"
          stroke="var(--accent, #00d4ff)"
          strokeWidth="2.5"
        />
        <path
          d="M24 10 L38 24 L24 38 L10 24 Z"
          fill="var(--accent, #00d4ff)"
          opacity="0.15"
        />
        {/* DSI text */}
        <text
          x="56"
          y="22"
          fontFamily="var(--font-display, 'JetBrains Mono', monospace)"
          fontSize="18"
          fontWeight="800"
          fill="var(--text-primary, #e0e0e0)"
          letterSpacing="2"
        >
          DSI
        </text>
        <text
          x="56"
          y="38"
          fontFamily="var(--font-display, 'JetBrains Mono', monospace)"
          fontSize="7"
          fill="var(--text-secondary, #888)"
          letterSpacing="0.5"
        >
          DRUM SWARM INTL
        </text>
      </svg>
    </Link>
  );
}
