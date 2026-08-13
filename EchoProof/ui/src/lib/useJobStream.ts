/** Follow one adjudication job over SSE.
 *
 * Every event in `events` arrived from the server; the hook adds nothing,
 * reorders nothing and drops nothing. The elapsed clock is the only thing
 * computed client side, and it is a clock, not a progress estimate.
 */

import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { JobInfo, ProgressEvent } from "../types";

export interface JobStream {
  events: ProgressEvent[];
  status: "idle" | "connecting" | "streaming" | "done" | "failed" | "lost";
  final: JobInfo | null;
  error: string | null;
}

export function useJobStream(jobId: string | null): JobStream {
  const [state, setState] = useState<JobStream>({
    events: [],
    status: "idle",
    final: null,
    error: null,
  });
  const seen = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (!jobId) return;
    seen.current = new Set();
    setState({ events: [], status: "connecting", final: null, error: null });

    const source = new EventSource(api.eventsUrl(jobId));

    const onEvent = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data) as ProgressEvent;
        if (seen.current.has(parsed.seq)) return;
        seen.current.add(parsed.seq);
        setState((previous) => ({
          ...previous,
          status: "streaming",
          events: [...previous.events, parsed].sort((a, b) => a.seq - b.seq),
        }));
      } catch {
        /* a malformed frame is dropped, not invented around */
      }
    };

    // Named SSE events: one listener per stage name we know, plus a generic
    // fallback for any stage the pipeline adds later.
    const stages = [
      "job.stack",
      "job.config",
      "job.done",
      "job.failed",
      "extract.start",
      "extract.done",
      "claim.start",
      "deterministic.decided",
      "retrieve.query",
      "retrieve.done",
      "judge.start",
      "judge.done",
      "evidence.written",
    ];
    for (const stage of stages) source.addEventListener(stage, onEvent);
    source.onmessage = onEvent;

    source.addEventListener("end", (event: MessageEvent) => {
      try {
        const info = JSON.parse(event.data) as JobInfo;
        setState((previous) => ({
          ...previous,
          status: info.status === "failed" ? "failed" : "done",
          final: info,
          error: info.error,
        }));
      } catch {
        setState((previous) => ({ ...previous, status: "done" }));
      }
      source.close();
    });

    source.onerror = () => {
      setState((previous) =>
        previous.status === "done" || previous.status === "failed"
          ? previous
          : { ...previous, status: "lost" },
      );
    };

    return () => source.close();
  }, [jobId]);

  return state;
}
