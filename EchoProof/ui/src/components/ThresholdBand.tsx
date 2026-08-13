/** The score axis: position IS the verdict.
 *
 * Candidates sit at their recorded rerank scores on a vertical axis crossed
 * by the two threshold lines from the retrieve.rule span. Below the floor is
 * no_governing_rule territory; between floor and ceiling is
 * retrieval_below_confidence; above the ceiling proceeds to the judge; two
 * plausible candidates inside the conflict margin become
 * conflicting_sections.
 *
 * The thresholds are draggable for inspection: moving one visibly
 * reclassifies the candidates between the three regions, which is how a
 * stranger learns the epistemics in seconds. Inspection never touches the
 * record; the recorded values are printed beside the axis and one click
 * restores them.
 */

import { useMemo, useRef, useState } from "react";
import type { Candidate } from "../types";
import "./thresholdband.css";

const HEIGHT = 360;
const TOP_PAD = 14;
const BOTTOM_PAD = 14;

function y(score: number): number {
  const clamped = Math.max(0, Math.min(1, score));
  return TOP_PAD + (1 - clamped) * (HEIGHT - TOP_PAD - BOTTOM_PAD);
}

function scoreAt(py: number): number {
  return Math.max(0, Math.min(1, 1 - (py - TOP_PAD) / (HEIGHT - TOP_PAD - BOTTOM_PAD)));
}

interface Props {
  candidates: Candidate[];
  floor: number;
  ceiling: number;
  conflictMargin: number;
  selectedSection: string | null;
  selectedScore: number | null;
}

export function ThresholdBand({
  candidates,
  floor,
  ceiling,
  conflictMargin,
  selectedSection,
  selectedScore,
}: Props) {
  const [inspect, setInspect] = useState<{ floor: number; ceiling: number }>({
    floor,
    ceiling,
  });
  const dragging = useRef<"floor" | "ceiling" | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const touched = inspect.floor !== floor || inspect.ceiling !== ceiling;

  // One mark per section, best score first: the same dedup rule the judge's
  // shortlist uses.
  const marks = useMemo(() => {
    const seen = new Set<string>();
    const out: Candidate[] = [];
    for (const candidate of candidates) {
      if (seen.has(candidate.section_id)) continue;
      seen.add(candidate.section_id);
      out.push(candidate);
    }
    return out;
  }, [candidates]);

  const counts = useMemo(() => {
    let below = 0;
    let band = 0;
    let above = 0;
    for (const mark of marks) {
      if (mark.score < inspect.floor) below += 1;
      else if (mark.score < inspect.ceiling) band += 1;
      else above += 1;
    }
    return { below, band, above };
  }, [marks, inspect]);

  const top = marks[0];

  const onPointerMove = (event: React.PointerEvent) => {
    if (!dragging.current || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const value = Math.round(scoreAt(event.clientY - rect.top) * 1000) / 1000;
    setInspect((previous) => {
      if (dragging.current === "floor")
        return { ...previous, floor: Math.min(value, previous.ceiling - 0.005) };
      return { ...previous, ceiling: Math.max(value, previous.floor + 0.005) };
    });
  };

  const grab = (which: "floor" | "ceiling") => (event: React.PointerEvent) => {
    dragging.current = which;
    (event.target as Element).setPointerCapture(event.pointerId);
  };

  const release = () => {
    dragging.current = null;
  };

  const nudge = (which: "floor" | "ceiling") => (event: React.KeyboardEvent) => {
    const step =
      event.key === "ArrowUp" ? 0.005 : event.key === "ArrowDown" ? -0.005 : 0;
    if (!step) return;
    event.preventDefault();
    setInspect((previous) =>
      which === "floor"
        ? { ...previous, floor: Math.min(previous.ceiling - 0.005, Math.max(0, previous.floor + step)) }
        : { ...previous, ceiling: Math.max(previous.floor + 0.005, Math.min(1, previous.ceiling + step)) },
    );
  };

  return (
    <div className="tband">
      <svg
        ref={svgRef}
        viewBox={`0 0 300 ${HEIGHT}`}
        className="tband-svg"
        onPointerMove={onPointerMove}
        onPointerUp={release}
        role="img"
        aria-label={`Score axis. ${counts.above} candidate section(s) above the ceiling, ${counts.band} in the low-confidence band, ${counts.below} below the floor.`}
      >
        {/* regions */}
        <rect x="70" y={TOP_PAD} width="150" height={y(inspect.ceiling) - TOP_PAD} className="tband-region above" />
        <rect x="70" y={y(inspect.ceiling)} width="150" height={y(inspect.floor) - y(inspect.ceiling)} className="tband-region band" />
        <rect x="70" y={y(inspect.floor)} width="150" height={HEIGHT - BOTTOM_PAD - y(inspect.floor)} className="tband-region below" />

        {/* axis */}
        <line x1="70" y1={TOP_PAD} x2="70" y2={HEIGHT - BOTTOM_PAD} className="tband-axis" />
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
          <g key={tick}>
            <line x1="64" x2="70" y1={y(tick)} y2={y(tick)} className="tband-axis" />
            <text x="58" y={y(tick) + 4} className="tband-ticklabel" textAnchor="end">
              {tick.toFixed(2)}
            </text>
          </g>
        ))}

        {/* conflict margin under the top candidate */}
        {top && (
          <rect
            x="70"
            y={y(top.score)}
            width="150"
            height={Math.max(0, y(top.score - conflictMargin) - y(top.score))}
            className="tband-conflict"
          >
            <title>
              conflict margin {conflictMargin}: a second section scoring within
              this band of the top candidate makes the retrieval conflicting
            </title>
          </rect>
        )}

        {/* threshold lines, draggable */}
        {(["ceiling", "floor"] as const).map((which) => (
          <g key={which}>
            <line
              x1="70"
              x2="220"
              y1={y(inspect[which])}
              y2={y(inspect[which])}
              className={`tband-threshold ${which}`}
            />
            <rect
              x="70"
              y={y(inspect[which]) - 7}
              width="150"
              height="14"
              className="tband-grab"
              tabIndex={0}
              role="slider"
              aria-label={`${which} threshold, inspection only`}
              aria-valuenow={inspect[which]}
              aria-valuemin={0}
              aria-valuemax={1}
              onPointerDown={grab(which)}
              onKeyDown={nudge(which)}
            />
            <text x="224" y={y(inspect[which]) + 4} className="tband-thlabel">
              {which} {inspect[which].toFixed(3)}
            </text>
          </g>
        ))}

        {/* candidate marks */}
        {marks.map((mark) => {
          const isSelected = mark.section_id === selectedSection;
          return (
            <g key={mark.section_id}>
              <circle
                cx="145"
                cy={y(mark.score)}
                r={isSelected ? 6 : 3.5}
                className={isSelected ? "tband-mark selected" : "tband-mark"}
              >
                <title>
                  {mark.section_id} score {mark.score.toFixed(3)}
                  {mark.bm25_rank !== null ? ` bm25#${mark.bm25_rank}` : ""}
                  {mark.dense_rank !== null ? ` dense#${mark.dense_rank}` : ""}
                </title>
              </circle>
              {isSelected && (
                <text x="158" y={y(mark.score) + 4} className="tband-marklabel selected">
                  {mark.section_id}
                </text>
              )}
            </g>
          );
        })}
        {/* the judge's selection when it carries its own recorded score */}
        {selectedScore !== null && selectedSection && (
          <line
            x1="139"
            x2="151"
            y1={y(selectedScore)}
            y2={y(selectedScore)}
            className="tband-selectedscore"
          />
        )}

        {/* region labels */}
        <text x="228" y={(TOP_PAD + y(inspect.ceiling)) / 2} className="tband-region-label">
          to the judge
        </text>
        <text x="228" y={(y(inspect.ceiling) + y(inspect.floor)) / 2} className="tband-region-label">
          retrieval_below_confidence
        </text>
        <text x="228" y={(y(inspect.floor) + HEIGHT - BOTTOM_PAD) / 2} className="tband-region-label">
          no_governing_rule
        </text>
      </svg>

      <div className="tband-side">
        <dl className="tband-counts mono">
          <div><dt>above ceiling</dt><dd>{counts.above}</dd></div>
          <div><dt>in the band</dt><dd>{counts.band}</dd></div>
          <div><dt>below floor</dt><dd>{counts.below}</dd></div>
        </dl>
        {touched ? (
          <p className="tband-note">
            <span className="syslabel">inspection only</span> The record was
            adjudicated at floor {floor.toFixed(3)}, ceiling {ceiling.toFixed(3)}.{" "}
            <button className="tband-reset mono" onClick={() => setInspect({ floor, ceiling })}>
              restore recorded thresholds
            </button>
          </p>
        ) : (
          <p className="tband-note muted">
            Drag a threshold to see how the candidates reclassify. The recorded
            verdict does not change; this is how the abstention states read.
          </p>
        )}
      </div>
    </div>
  );
}
