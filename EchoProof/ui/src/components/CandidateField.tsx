/** The retrieval field: what the judge was offered, and how strongly.
 *
 * Every candidate sits at its recorded rerank score along a low-to-high axis,
 * sized by rank, with the section the judge selected drawn largest and
 * outlined. This replaces an earlier panel that reported "10 above ceiling,
 * 0 in the band, 0 below floor", which was accurate and told a reader
 * nothing: three counts with no sense of which rules were in play or how
 * close the contest was.
 *
 * The thresholds are drawn as fixed marks on the same axis. They are not
 * draggable here. An exploration that lets someone move a threshold belongs
 * behind a clearly labelled what-if, not on the page where a recorded verdict
 * is being read, because the recorded verdict never changes no matter what
 * the reader drags.
 */

import { useState } from "react";
import type { Candidate } from "../types";
import "./candidatefield.css";

interface Props {
  candidates: Candidate[];
  floor: number;
  ceiling: number;
  selectedSection: string | null;
  selectedScore: number | null;
}

export function CandidateField({
  candidates,
  floor,
  ceiling,
  selectedSection,
  selectedScore,
}: Props) {
  const [hovered, setHovered] = useState<string | null>(null);

  // One row per section, best score first: the same dedup the shortlist uses.
  const seen = new Set<string>();
  const rows = candidates
    .filter((candidate) => {
      if (seen.has(candidate.section_id)) return false;
      seen.add(candidate.section_id);
      return true;
    })
    .map((candidate, index) => ({ ...candidate, rank: index + 1 }));

  if (rows.length === 0) {
    return (
      <p className="muted cf-empty">
        No retrieval candidates were recorded for this claim.
      </p>
    );
  }

  const scores = rows.map((row) => row.score);
  const low = Math.min(...scores, floor) - 0.03;
  const high = Math.max(...scores, ceiling) + 0.03;
  const place = (score: number) =>
    `${((score - low) / (high - low)) * 100}%`;

  const active = rows.find((row) => row.section_id === hovered) ?? null;

  return (
    <div className="cf">
      <div className="cf-head">
        <span className="syslabel">retrieval field</span>
        <span className="mono cf-axislabels">
          <span>lower confidence</span>
          <span>higher</span>
        </span>
      </div>

      <div className="cf-plot">
        <div className="cf-axis" aria-hidden="true" />
        <span className="cf-threshold cf-floor" style={{ left: place(floor) }}>
          <span className="mono">floor {floor.toFixed(3)}</span>
        </span>
        <span className="cf-threshold cf-ceiling" style={{ left: place(ceiling) }}>
          <span className="mono">ceiling {ceiling.toFixed(3)}</span>
        </span>

        {rows.map((row, index) => {
          const isSelected = row.section_id === selectedSection;
          const size = Math.max(8, 26 - row.rank * 2.4);
          return (
            <button
              key={row.chunk_id ?? row.section_id}
              className={`cf-candidate ${isSelected ? "selected" : ""}`}
              style={{
                left: place(row.score),
                top: `${12 + (index % 6) * 15.5}%`,
                ["--size" as string]: `${isSelected ? Math.max(size, 26) : size}px`,
              }}
              onPointerEnter={() => setHovered(row.section_id)}
              onPointerLeave={() => setHovered(null)}
              onFocus={() => setHovered(row.section_id)}
              onBlur={() => setHovered(null)}
              aria-label={`${row.section_id}, retrieval score ${row.score.toFixed(3)}, rank ${row.rank}${isSelected ? ", selected by the judge" : ""}`}
              data-cursor={`trace:${row.section_id}`}
            >
              <span className="cf-dot" />
              {(isSelected || hovered === row.section_id) && (
                <span className="cf-tag mono">{row.section_id}</span>
              )}
            </button>
          );
        })}
      </div>

      <div className="cf-readout">
        {active ? (
          <dl className="mono">
            <div>
              <dt>section</dt>
              <dd>{active.section_id}</dd>
            </div>
            <div>
              <dt>score</dt>
              <dd>{active.score.toFixed(3)}</dd>
            </div>
            <div>
              <dt>rank</dt>
              <dd>{String(active.rank).padStart(2, "0")}</dd>
            </div>
            <div>
              <dt>matched by</dt>
              <dd>
                {active.bm25_rank !== null && active.dense_rank !== null
                  ? "keyword and meaning"
                  : active.bm25_rank !== null
                    ? "keyword"
                    : "meaning"}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="muted cf-hint">
            {selectedSection ? (
              <>
                The judge selected <code>{selectedSection}</code>
                {selectedScore !== null && (
                  <> at {selectedScore.toFixed(3)}</>
                )}
                {rows[0] && rows[0].section_id !== selectedSection && (
                  <>
                    {" "}
                    over <code>{rows[0].section_id}</code>, which retrieval
                    ranked first. Selection is a separate decision from
                    ranking, and this is it happening.
                  </>
                )}
                . Hover a candidate to inspect it.
              </>
            ) : (
              "Hover a candidate to inspect it."
            )}
          </p>
        )}
      </div>
    </div>
  );
}
