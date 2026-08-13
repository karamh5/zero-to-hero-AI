/** Typography for a metric that is honestly a range, not a number.
 *
 * The two endpoints are set large in the machine face, flanking a 0 to 1 rail
 * on which the interval is drawn to scale. The rail is the point: uncertainty
 * gets a shape, not a footnote. Individual run values appear as ticks so the
 * range visibly comes from real measurements rather than from styling.
 *
 * The same rail renders a floor comparison (value against a required floor),
 * which is how judge-human agreement shows itself failing.
 */

import "./band.css";

interface Tick {
  value: number;
  label: string;
}

export function RangeBand({
  name,
  low,
  high,
  ticks = [],
  caption,
  source,
}: {
  name: string;
  low: number;
  high: number;
  ticks?: Tick[];
  caption: string;
  source: string;
}) {
  const pct = (v: number) => `${Math.max(0, Math.min(1, v)) * 100}%`;
  return (
    <figure className="band">
      <figcaption className="band-name syslabel">{name}</figcaption>
      <div className="band-row">
        <span className="band-endpoint">{low.toFixed(2)}</span>
        <div className="band-rail" role="img" aria-label={`${name}: ${low.toFixed(2)} to ${high.toFixed(2)} on a scale of 0 to 1`}>
          <span
            className="band-interval"
            style={{ left: pct(low), width: `calc(${pct(high)} - ${pct(low)})` }}
          />
          {ticks.map((tick) => (
            <span
              key={tick.label}
              className="band-tick"
              style={{ left: pct(tick.value) }}
              title={`${tick.label}: ${tick.value.toFixed(3)}`}
            />
          ))}
          <span className="band-zero mono" aria-hidden="true">0</span>
          <span className="band-one mono" aria-hidden="true">1</span>
        </div>
        <span className="band-endpoint">{high.toFixed(2)}</span>
      </div>
      <p className="band-caption">{caption}</p>
      <p className="band-source mono">{source}</p>
    </figure>
  );
}

export function FloorBand({
  name,
  value,
  floor,
  meets,
  caption,
  source,
}: {
  name: string;
  value: number;
  floor: number;
  meets: boolean;
  caption: string;
  source: string;
}) {
  const pct = (v: number) => `${Math.max(0, Math.min(1, v)) * 100}%`;
  return (
    <figure className={`band ${meets ? "" : "band-fails"}`}>
      <figcaption className="band-name syslabel">{name}</figcaption>
      <div className="band-row">
        <span className="band-endpoint">{value.toFixed(2)}</span>
        <div
          className="band-rail"
          role="img"
          aria-label={`${name}: ${value.toFixed(3)} against a floor of ${floor.toFixed(2)}. ${meets ? "Meets the floor." : "Fails the floor."}`}
        >
          <span className="band-interval band-solid" style={{ left: 0, width: pct(value) }} />
          <span className="band-floor" style={{ left: pct(floor) }}>
            <span className="band-floor-label mono">floor {floor.toFixed(2)}</span>
          </span>
          <span className="band-zero mono" aria-hidden="true">0</span>
          <span className="band-one mono" aria-hidden="true">1</span>
        </div>
        <span className="band-verdict-word mono">{meets ? "meets" : "FAILS"}</span>
      </div>
      <p className="band-caption">{caption}</p>
      <p className="band-source mono">{source}</p>
    </figure>
  );
}
