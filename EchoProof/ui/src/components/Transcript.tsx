/** The claim inside its transcript, sliced by stored offsets.
 *
 * char_start/char_end index the exact transcript string in that turn's
 * agent.turn span. This component slices; it never searches, trims or
 * re-normalises whitespace, because any of those silently misaligns every
 * highlight (UI-INTEGRATION.md, "things that will bite you").
 */

import type { Verdict } from "../types";
import { verdictColor } from "../lib/verdicts";
import "./transcript.css";

export function Transcript({
  transcript,
  charStart,
  charEnd,
  verdict,
  settled = true,
}: {
  transcript: string;
  charStart: number;
  charEnd: number;
  verdict: Verdict | null;
  /** false while the claim is in flight: the excerpt sits greyed, un-set */
  settled?: boolean;
}) {
  const start = Math.max(0, Math.min(charStart, transcript.length));
  const end = Math.max(start, Math.min(charEnd, transcript.length));
  const color = verdict ? verdictColor(verdict) : "var(--ink-faint)";

  return (
    <p className={`transcript-block ${settled ? "settled" : "inflight"}`}>
      <span className="transcript-context">{transcript.slice(0, start)}</span>
      <mark
        className="transcript-claim"
        style={{ ["--claim-color" as string]: color }}
        data-offsets={`[${start}:${end})`}
      >
        {transcript.slice(start, end)}
      </mark>
      <span className="transcript-context">{transcript.slice(end)}</span>
    </p>
  );
}
