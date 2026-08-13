/** The verdict, spoken precisely: exact machine string, signal color, and a
 * shape that survives color-blindness. Decisions get a filled square,
 * abstentions a hollow one, and conflicting_sections a dashed hollow square
 * plus an explicit unreliability note, because it agreed 0/3 blind.
 */

import type { Verdict } from "../types";
import { DEWEIGHT_NOTE, VERDICT_META } from "../lib/verdicts";
import "./verdict.css";

export function VerdictMark({
  verdict,
  showKind = true,
}: {
  verdict: Verdict;
  showKind?: boolean;
}) {
  const meta = VERDICT_META[verdict];
  return (
    <span
      className={`verdict-mark ${meta.deweighted ? "deweighted" : ""}`}
      style={{ ["--v" as string]: `var(${meta.cssVar})` }}
    >
      <span className={`verdict-glyph ${meta.kind}`} aria-hidden="true" />
      <span className="verdict-string">{verdict}</span>
      {showKind && <span className="verdict-kind">{meta.kind}</span>}
      {meta.deweighted && (
        <span className="verdict-unreliable" title={DEWEIGHT_NOTE}>
          least reliable state
        </span>
      )}
    </span>
  );
}
