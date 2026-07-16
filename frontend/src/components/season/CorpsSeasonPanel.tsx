import type { CorpsSeasonSummary } from "../../services/v1";

interface Props {
  corps: CorpsSeasonSummary;
}

export function CorpsSeasonPanel({ corps }: Props) {
  return (
    <article className="corps-season-panel">
      <header>
        <h3>{corps.corps_id}</h3>
        <span>{corps.phase}</span>
      </header>
      <p>{corps.next_action}</p>
      {corps.blocker_reason ? <p className="blocker">{corps.blocker_reason}</p> : null}
    </article>
  );
}
