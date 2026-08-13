/** React wrapper binding the sift engine to a job's event stream. */

import { useEffect, useMemo, useRef } from "react";
import { api } from "../api";
import { verdictColor } from "../lib/verdicts";
import type { ProgressEvent, Verdict } from "../types";
import { VERDICTS } from "../types";
import { SiftEngine, type SiftSection } from "./sift-engine";
import "./sift.css";

function rootOf(sectionId: string, separators: string[]): string {
  let cut = sectionId.length;
  for (const separator of separators) {
    const at = sectionId.indexOf(separator);
    if (at >= 0 && at < cut) cut = at;
  }
  return sectionId.slice(0, cut);
}

export interface SiftRecord {
  candidates: { section_id: string; score: number }[];
  selectedScore: number | null;
}

export function Sift({
  events,
  record = null,
}: {
  events: ProgressEvent[];
  /** the recorded candidate distribution, once the evidence log exists */
  record?: SiftRecord | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<SiftEngine | null>(null);
  const appliedSeq = useRef(-1);
  const corpusLoaded = useRef<string | null>(null);

  const reducedMotion = useMemo(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    [],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const engine = new SiftEngine(canvas, reducedMotion);
    engineRef.current = engine;
    const observer = new ResizeObserver(() => engine.resize());
    observer.observe(canvas);
    return () => {
      observer.disconnect();
      engine.destroy();
      engineRef.current = null;
    };
  }, [reducedMotion]);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    for (const event of events) {
      if (event.seq <= appliedSeq.current) continue;
      appliedSeq.current = event.seq;
      apply(engine, event, corpusLoaded);
    }
  }, [events]);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine || !record) return;
    engine.backfill(record.candidates, record.selectedScore);
  }, [record]);

  return (
    <div className="sift-frame">
      <canvas ref={canvasRef} className="sift-canvas" aria-hidden="true" />
      <p className="sift-caption mono">
        one mark per provision, read from the pack · thresholds from the
        recorded configuration · candidates land in a ranked pool because the
        stream carries their count and the top score, not fifty scores; the
        full distribution arrives with the evidence log
      </p>
    </div>
  );
}

function apply(
  engine: SiftEngine,
  event: ProgressEvent,
  corpusLoaded: React.MutableRefObject<string | null>,
) {
  const detail = event.detail as Record<string, unknown>;
  switch (event.stage) {
    case "job.config": {
      const packId = String(detail.pack_id ?? "");
      const thresholds = detail.thresholds as
        | { floor?: number; ceiling?: number }
        | undefined;
      if (thresholds?.floor !== undefined && thresholds?.ceiling !== undefined) {
        engine.setThresholds({
          floor: Number(thresholds.floor),
          ceiling: Number(thresholds.ceiling),
        });
      }
      if (packId && corpusLoaded.current !== packId) {
        corpusLoaded.current = packId;
        void api.corpus(packId).then((corpus) => {
          const sections: SiftSection[] = corpus.sections.map((s) => ({
            section_id: s.section_id,
            root: rootOf(s.section_id, corpus.hierarchy_separators),
          }));
          engine.setCorpus(sections);
        });
      }
      break;
    }
    case "claim.start":
      engine.beginClaim();
      break;
    case "deterministic.decided":
      engine.deterministic();
      break;
    case "retrieve.query":
      engine.query();
      break;
    case "retrieve.done":
      engine.ranked(
        Number(detail.candidates ?? 0),
        detail.top != null ? String(detail.top) : null,
        detail.score != null ? Number(detail.score) : null,
      );
      break;
    case "judge.start":
      engine.shortlist(Number(detail.offered ?? 0));
      break;
    case "judge.done": {
      const verdict = String(detail.verdict ?? "");
      const known = (VERDICTS as readonly string[]).includes(verdict);
      engine.settle(
        detail.section_id != null ? String(detail.section_id) : null,
        known ? verdictColor(verdict as Verdict) : "var(--ink)",
        verdict,
      );
      break;
    }
    default:
      break;
  }
}
