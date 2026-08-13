/** The rig: submit a turn, watch the instrument work at full speed.
 *
 * A turn takes 105 seconds median, 140 worst (demo/latency.json). The screen
 * is built to be watched for that long without lying: every line in the
 * stage log is a real pipeline event, the only clock is elapsed time set
 * against the measured median, and there is no percentage anywhere because
 * none would be honest.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Sift, type SiftRecord } from "../components/Sift";
import { ErrorState, Loading } from "../components/States";
import { VerdictMark } from "../components/VerdictMark";
import { seconds1 } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import { useJobStream } from "../lib/useJobStream";
import type { ProgressEvent, Verdict } from "../types";
import { VERDICTS } from "../types";
import "./rig.css";

const STAGE_LABELS: Record<string, string> = {
  "job.stack": "stack     loading model weights",
  "job.config": "config    corpus and thresholds pinned",
  "extract.start": "extract   reading the turn",
  "extract.done": "extract   claims found",
  "claim.start": "claim     adjudicating",
  "deterministic.decided": "verify    decided in code",
  "retrieve.query": "retrieve  searching the corpus",
  "retrieve.done": "retrieve  candidates ranked",
  "judge.start": "judge     reading the rules",
  "judge.done": "judge     verdict",
  "evidence.written": "evidence  chain written",
  "job.done": "job       complete",
  "job.failed": "job       FAILED",
};

function describe(event: ProgressEvent): string {
  const d = event.detail;
  switch (event.stage) {
    case "extract.start":
      return `${d.chars} characters`;
    case "extract.done":
      return `${d.claims} claim(s)${Number(d.rejected) ? `, ${d.rejected} rejected` : ""}`;
    case "claim.start":
      return `${d.index}/${d.total}  ${d.claim_type}  "${String(d.text ?? "")}"`;
    case "deterministic.decided":
      return `${d.value} -> ${d.verdict} (no model involved)`;
    case "retrieve.query":
      return `query ${d.number}/${d.of}  "${String(d.query ?? "")}"`;
    case "retrieve.done":
      return `${d.candidates} candidates, top ${d.top} @ ${d.score}`;
    case "judge.start":
      return `${d.offered} sections offered`;
    case "judge.done":
      return `${d.verdict} @ ${d.section_id ?? "-"}`;
    case "evidence.written":
      return `${d.spans} spans, ${d.findings} finding(s)`;
    case "job.config":
      return `${d.pack_id} · ${d.corpus_size} provisions`;
    case "job.done":
      return `${d.findings} finding(s), ${d.abstentions} abstention(s): evidence on the bench`;
    case "job.failed":
      return String(d.error ?? "");
    default:
      return Object.entries(d)
        .map(([k, v]) => `${k}=${String(v)}`)
        .join(" ");
  }
}

interface ClaimRow {
  claimId: string;
  text: string;
  claimType: string;
  index: number;
  total: number;
  verdict: Verdict | null;
  sectionId: string | null;
  decidedInCode: boolean;
}

function claimsFromEvents(events: ProgressEvent[]): ClaimRow[] {
  const rows: ClaimRow[] = [];
  for (const event of events) {
    const d = event.detail;
    if (event.stage === "claim.start") {
      rows.push({
        claimId: String(d.claim_id ?? ""),
        text: String(d.text ?? ""),
        claimType: String(d.claim_type ?? ""),
        index: Number(d.index ?? rows.length + 1),
        total: Number(d.total ?? 0),
        verdict: null,
        sectionId: null,
        decidedInCode: false,
      });
    } else if (event.stage === "judge.done" || event.stage === "deterministic.decided") {
      const row = rows.find((r) => r.claimId === String(d.claim_id ?? ""));
      if (row) {
        const verdict = String(d.verdict ?? "");
        row.verdict = (VERDICTS as readonly string[]).includes(verdict)
          ? (verdict as Verdict)
          : null;
        row.sectionId = d.section_id != null ? String(d.section_id) : null;
        row.decidedInCode = event.stage === "deterministic.decided";
      }
    }
  }
  return rows;
}

export function Rig() {
  const availability = useFetch(() => api.availability(), []);
  const presets = useFetch(() => api.rigPresets().catch(() => ({ presets: [] })), []);
  const measurements = useFetch(() => api.measurements(), []);

  const [transcript, setTranscript] = useState("");
  const [knownAmounts, setKnownAmounts] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const stream = useJobStream(jobId);

  const running =
    stream.status === "connecting" || stream.status === "streaming";

  // The elapsed clock: real time since the stream began, shown against the
  // measured median. Ticks only while the job runs.
  const [now, setNow] = useState(0);
  const startedAt = useRef<number | null>(null);
  useEffect(() => {
    if (!running) return;
    if (startedAt.current === null) startedAt.current = performance.now();
    const timer = window.setInterval(
      () => setNow(performance.now()),
      100,
    );
    return () => window.clearInterval(timer);
  }, [running]);
  useEffect(() => {
    if (jobId) {
      startedAt.current = performance.now();
      setNow(performance.now());
    }
  }, [jobId]);

  const elapsed =
    startedAt.current !== null ? (now - startedAt.current) / 1000 : 0;
  const latency = measurements.data?.latency.data ?? null;

  const claims = useMemo(() => claimsFromEvents(stream.events), [stream.events]);

  // Once the run's evidence log exists, back-fill the axis with the recorded
  // candidate distribution for the last retrieved claim. Live events carry a
  // count and a top score; the log carries the actual scores, so this is the
  // moment the full record honestly becomes available.
  const [record, setRecord] = useState<SiftRecord | null>(null);
  useEffect(() => {
    if (stream.status !== "done" || !stream.final?.result) return;
    let cancelled = false;
    api
      .spans(stream.final.result.run_id)
      .then((body) => {
        if (cancelled) return;
        const retrievals = body.spans.filter((s) => s.span_type === "retrieve.rule");
        const last = retrievals.at(-1);
        if (!last) return;
        const judge = body.spans
          .filter(
            (s) =>
              s.span_type === "judge.rule" &&
              s.payload.claim_id === last.payload.claim_id,
          )
          .at(-1);
        setRecord({
          candidates: (last.payload.candidates as { section_id: string; score: number }[]) ?? [],
          selectedScore:
            typeof judge?.payload.judge_selected_score === "number"
              ? judge.payload.judge_selected_score
              : null,
        });
      })
      .catch(() => {
        /* the run page still shows the full record; the sift just keeps its live marks */
      });
    return () => {
      cancelled = true;
    };
  }, [stream.status, stream.final]);
  const logRef = useRef<HTMLOListElement>(null);
  useEffect(() => {
    logRef.current?.lastElementChild?.scrollIntoView({ block: "nearest" });
  }, [stream.events.length]);

  const submit = async () => {
    setSubmitError(null);
    const expectations: Record<string, unknown> = {};
    const amounts = knownAmounts
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    if (amounts.length) expectations.amounts = amounts;
    try {
      const job = await api.submitTurn(transcript, expectations);
      setJobId(job.job_id);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : String(error));
    }
  };

  if (availability.loading)
    return <div className="page"><Loading what="rig availability" /></div>;
  if (availability.error)
    return <div className="page"><ErrorState error={availability.error} retry={availability.retry} /></div>;

  const available = availability.data?.available ?? false;

  return (
    <div className="page rig">
      <header className="rig-head">
        <h1 className="rig-display">The rig</h1>
        <p className="rig-lede">
          Submit an agent turn and watch it adjudicated against the corpus:
          claims out, rules retrieved, one section selected, verdict written to
          the chain. Median {latency ? seconds1(latency.median_total) : "105s"},
          worst {latency ? seconds1(latency.worst_total) : "140s"} per turn,
          measured. The wait is the work.
        </p>
      </header>

      {!available && (
        <section className="rig-disabled">
          <span className="syslabel">live adjudication disabled</span>
          <p>{availability.data?.reason}</p>
          <p className="muted">
            Everything else on this bench reads stored evidence and works
            without credentials. Set <code>MISTRAL_API_KEY</code> in{" "}
            <code>EchoProof/.env</code> and restart the server to enable the
            rig.
          </p>
        </section>
      )}

      {available && !jobId && (
        <section className="rig-form">
          <label className="syslabel" htmlFor="rig-transcript">
            agent turn to adjudicate
          </label>
          <textarea
            id="rig-transcript"
            value={transcript}
            onChange={(event) => setTranscript(event.target.value)}
            rows={4}
            maxLength={4000}
            placeholder="What the agent said, verbatim."
          />
          <div className="rig-expect">
            <label className="syslabel" htmlFor="rig-amounts">
              known-true amounts, optional, comma separated
            </label>
            <input
              id="rig-amounts"
              className="mono"
              value={knownAmounts}
              onChange={(event) => setKnownAmounts(event.target.value)}
              placeholder="940.00"
            />
            <p className="muted rig-expect-note">
              A numeric claim matching one of these is settled in code before
              retrieval ever runs: the short path on the instrument.
            </p>
          </div>

          {(presets.data?.presets.length ?? 0) > 0 && (
            <div className="rig-presets">
              <span className="syslabel">
                or replay a recorded turn from runs/demo-campaign
              </span>
              <ul>
                {presets.data!.presets.map((preset) => (
                  <li key={`${preset.source_run}-${preset.turn_id}`}>
                    <button
                      className="rig-preset"
                      onClick={() => setTranscript(preset.transcript)}
                    >
                      <span className="mono faint">{preset.turn_id}</span>
                      <span className="rig-preset-text">
                        {preset.transcript.slice(0, 110)}
                        {preset.transcript.length > 110 ? "…" : ""}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <button
            className="rig-submit"
            onClick={() => void submit()}
            disabled={!transcript.trim()}
          >
            adjudicate
          </button>
          {submitError && (
            <p className="rig-submiterror mono" role="alert">
              {submitError}
            </p>
          )}
          {availability.data?.stack_state === "cold" && (
            <p className="muted rig-coldnote">
              First run loads the embedding and reranker weights: roughly 20
              seconds warm, a 1.5 GB download cold. The stack stays loaded
              afterwards.
            </p>
          )}
        </section>
      )}

      {jobId && (
        <section className="rig-live">
          <div className="rig-meter">
            <span className="mono rig-clock">
              {elapsed.toFixed(1)}s
              {latency && (
                <span className="muted">
                  {" "}
                  elapsed · measured median {seconds1(latency.median_total)},
                  worst {seconds1(latency.worst_total)}
                </span>
              )}
            </span>
            <span className={`syslabel rig-status rig-status-${stream.status}`}>
              {stream.status === "lost"
                ? "stream lost: the job continues server side; refresh to rejoin"
                : stream.status}
            </span>
          </div>

          <Sift events={stream.events} record={record} />

          <div className="rig-columns">
            <div className="rig-log-wrap">
              <h2 className="syslabel">stage log: every line is a real event</h2>
              <ol className="rig-log" ref={logRef} aria-live="polite">
                {stream.events.map((event) => (
                  <li key={event.seq} className={`rig-logline stage-${event.stage.replace(/\./g, "-")}`}>
                    <span className="rig-log-at">[{event.at.toFixed(1)}s]</span>
                    <span className="rig-log-label">
                      {STAGE_LABELS[event.stage] ?? event.stage}
                    </span>
                    <span className="rig-log-note">{describe(event)}</span>
                  </li>
                ))}
                {stream.events.length === 0 && (
                  <li className="rig-logline muted">waiting for the first event…</li>
                )}
              </ol>
            </div>

            <div className="rig-claims">
              <h2 className="syslabel">claims</h2>
              {claims.length === 0 ? (
                <p className="muted">none extracted yet</p>
              ) : (
                <ol className="rig-claimlist">
                  {claims.map((claim) => (
                    <li
                      key={claim.claimId}
                      className={`rig-claim ${claim.verdict ? "settled" : "inflight"}`}
                    >
                      <span className="mono faint">
                        {claim.index}/{claim.total} {claim.claimType}
                      </span>
                      <p className="rig-claimtext">"{claim.text}"</p>
                      {claim.verdict ? (
                        <span className="rig-claimverdict">
                          <VerdictMark verdict={claim.verdict} showKind={false} />
                          {claim.sectionId && (
                            <span className="mono"> @ {claim.sectionId}</span>
                          )}
                          {claim.decidedInCode && (
                            <span className="syslabel rig-code"> decided in code</span>
                          )}
                        </span>
                      ) : (
                        <span className="mono muted">in flight</span>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>

          {stream.status === "failed" && (
            <div className="rig-failed" role="alert">
              <span className="syslabel">job failed</span>
              <p className="mono">{stream.error}</p>
            </div>
          )}

          {stream.status === "done" && stream.final?.result && (
            <div className="rig-done">
              <span className="syslabel">evidence written</span>
              <p>
                {stream.final.result.findings} finding(s),{" "}
                {stream.final.result.abstentions} abstention(s) across{" "}
                {stream.final.result.claims} claim(s): counted separately, as
                always. The run is on the bench with a verifiable chain:
              </p>
              <p>
                <Link to={`/runs/${stream.final.result.run_id}`} className="mono">
                  {stream.final.result.run_id}
                </Link>
              </p>
              <button
                className="rig-again mono"
                onClick={() => {
                  setJobId(null);
                  setTranscript("");
                }}
              >
                adjudicate another turn
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
