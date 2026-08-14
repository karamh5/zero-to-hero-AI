/** The evidence trace: the path a verdict actually took, as objects.
 *
 * Eight steps, each one a real span from the hash chain with its own entry
 * hash. Steps that did not happen are shown as not taken rather than hidden,
 * because a deterministic decision skipping retrieval entirely is one of the
 * more interesting things this system does and concealing the gap would make
 * every trace look the same.
 *
 * Rows expand in place: retrieval opens the candidate field, the governing
 * rule opens the verbatim text, the seal opens the chain link. Nothing here
 * recomputes anything.
 */

import { useState, type ReactNode } from "react";
import { shortHash } from "../lib/format";
import "./evidencetrace.css";

export interface TraceStep {
  key: string;
  index: number;
  label: string;
  detail: string;
  hash?: string | null;
  taken: boolean;
  skippedNote?: string;
  body?: ReactNode;
}

export function EvidenceTrace({
  steps,
  initiallyOpen,
}: {
  steps: TraceStep[];
  initiallyOpen?: string;
}) {
  const [open, setOpen] = useState<string | null>(initiallyOpen ?? null);

  return (
    <ol className="et">
      {steps.map((step) => {
        const expanded = open === step.key;
        const openable = Boolean(step.body) && step.taken;
        return (
          <li
            key={step.key}
            className={`et-step ${step.taken ? "" : "not-taken"} ${expanded ? "open" : ""}`}
          >
            <div className="et-rail" aria-hidden="true">
              <span className="et-node" />
            </div>

            <div className="et-content">
              <button
                className="et-header"
                onClick={() => openable && setOpen(expanded ? null : step.key)}
                aria-expanded={openable ? expanded : undefined}
                disabled={!openable}
                data-cursor={openable ? "trace:expand" : "trace"}
              >
                <span className="et-num mono">
                  {String(step.index).padStart(2, "0")}
                </span>
                <span className="et-label mono">{step.label}</span>
                {step.hash && (
                  <span className="et-hash mono" title={step.hash}>
                    {shortHash(step.hash, 12)}
                  </span>
                )}
                {openable && (
                  <span className="et-toggle mono" aria-hidden="true">
                    {expanded ? "close" : "open"}
                  </span>
                )}
              </button>

              <p className="et-detail">
                {step.taken ? step.detail : step.skippedNote ?? "not taken"}
              </p>

              {expanded && step.body && (
                <div className="et-body">{step.body}</div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
