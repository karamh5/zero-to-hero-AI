/** A ticker of the system's own language.
 *
 * Every string on it is real: span type names, verdict states, section
 * identifiers, chain hashes taken from runs on disk. That is the whole point
 * of borrowing this device. A ticker of invented technical-looking strings
 * would be set dressing; a ticker of the actual vocabulary is the product
 * telling you what it is made of.
 *
 * Paused on hover and under prefers-reduced-motion, where it becomes a
 * static, horizontally scrollable strip.
 */

import "./marquee.css";

export function Marquee({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  // Two identical tracks so the loop has no seam.
  const track = (key: string) => (
    <div className="marquee-track" key={key} aria-hidden={key === "b"}>
      {items.map((item, index) => (
        <span className="marquee-item mono" key={item + index}>
          {item}
          <span className="marquee-sep">/</span>
        </span>
      ))}
    </div>
  );
  return (
    <div className="marquee">
      {track("a")}
      {track("b")}
    </div>
  );
}
