interface Props {
  regularShowCount: number;
  winterCampCount: number;
  onRegularShowCountChange: (value: number) => void;
  onWinterCampCountChange: (value: number) => void;
}

export function SeasonRunSettings({
  regularShowCount,
  winterCampCount,
  onRegularShowCountChange,
  onWinterCampCountChange,
}: Props) {
  return (
    <section className="season-run-settings">
      <label>
        Regular shows
        <input
          type="number"
          min={1}
          value={regularShowCount}
          onChange={(event) => onRegularShowCountChange(Number(event.target.value))}
        />
      </label>
      <label>
        Winter camps
        <input
          type="number"
          min={1}
          max={7}
          value={winterCampCount}
          onChange={(event) => onWinterCampCountChange(Number(event.target.value))}
        />
      </label>
    </section>
  );
}
