import type { SeasonRunSummary } from "../../services/v1";

interface Props {
  summary: SeasonRunSummary;
}

export function SeasonRunTimeline({ summary }: Props) {
  return (
    <section className="season-run-timeline">
      <header>
        <h2>Season Run</h2>
        <span>{summary.status}</span>
      </header>
      <p>
        {summary.regular_show_count} regular shows, finals, {summary.winter_camp_count} winter camps
      </p>
      {summary.blocker_reason ? (
        <p className="season-blocker">{summary.blocker_reason}</p>
      ) : null}
      <ol>
        {summary.corps.map((corps) => (
          <li key={corps.corps_id}>
            <strong>{corps.corps_id}</strong>
            <span>{corps.phase}</span>
            <span>{corps.next_action}</span>
            {corps.blocker_reason ? <span>{corps.blocker_reason}</span> : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
