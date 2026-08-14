/** The rig: a prepared test console, not a chatbot.
 *
 * Choose a corpus, choose a prepared conversation, name the assessment, run
 * it. Free text is not accepted, and that is a safety property rather than a
 * convenience: unlabelled text cannot guarantee that only the agent's turns
 * are adjudicated, and the consumer's words must never receive a verdict.
 *
 * While it runs, every line shown came from a real pipeline event. There is
 * no percentage and no spinner; the only number that moves on its own is an
 * elapsed clock.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { ComplianceCore, type CoreState, type CoreTone } from "../components/ComplianceCore";
import { Reveal, RevealLines } from "../components/Reveal";
import { ErrorState, Loading } from "../components/States";
import { VerdictMark } from "../components/VerdictMark";
import { useFetch } from "../lib/useFetch";
import { useJobStream } from "../lib/useJobStream";
import type {
  ConversationPack,
  PreparedConversation,
  ProgressEvent,
  Verdict,
} from "../types";
import { VERDICTS } from "../types";
import "./rig.css";

const STAGE_LABELS: Record<string, string> = {
  "job.stack": "STACK      loading model weights",
  "job.config": "CONFIG     corpus and thresholds pinned",
  "turn.agent": "TURN       agent turn under adjudication",
  "turn.skipped": "TURN       consumer turn, context only",
  "extract.start": "EXTRACT    reading the turn",
  "extract.done": "EXTRACT    claims found",
  "claim.start": "CLAIM      adjudicating",
  "deterministic.decided": "VERIFY     decided in code",
  "retrieve.query": "RETRIEVE   searching the corpus",
  "retrieve.done": "RETRIEVE   candidates ranked",
  "judge.start": "JUDGE      reading the rules",
  "judge.done": "JUDGE      verdict",
  "evidence.written": "EVIDENCE   chain written",
  "job.done": "SEALED     assessment complete",
  "job.failed": "FAILED",
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
    case "turn.agent":
      return `${d.index}/${d.of}  "${String(d.text ?? "")}"`;
    case "turn.skipped":
      return `not adjudicated  "${String(d.text ?? "")}"`;
    case "job.config":
      return `${d.pack_id} · ${d.corpus_size} provisions · ${d.agent_turns} agent turn(s), ${d.customer_turns} context turn(s)`;
    case "job.done":
      return `${d.findings} finding(s), ${d.supported} supported, ${d.abstentions} abstention(s)`;
    case "job.failed":
      return String(d.error ?? "");
    default:
      return Object.entries(d)
        .map(([k, v]) => `${k}=${String(v)}`)
        .join(" ");
  }
}

/** The core's state follows the last meaningful event, nothing else. */
function coreStateFrom(events: ProgressEvent[]): { state: CoreState; tone: CoreTone } {
  let state: CoreState = "submitted";
  let tone: CoreTone = "neutral";
  for (const event of events) {
    switch (event.stage) {
      case "extract.start":
      case "extract.done":
      case "claim.start":
        state = "extracting";
        break;
      case "retrieve.query":
      case "retrieve.done":
        state = "retrieving";
        break;
      case "judge.start":
        state = "judging";
        break;
      case "judge.done":
      case "deterministic.decided": {
        state = "verdict";
        const verdict = String(event.detail.verdict ?? "");
        if (verdict === "contradicted") tone = "contradicted";
        else if (verdict === "supported" && tone !== "contradicted") tone = "supported";
        else if (tone === "neutral") tone = "abstain";
        break;
      }
      case "evidence.written":
      case "job.done":
        state = "sealed";
        break;
      default:
        break;
    }
  }
  return { state, tone };
}

interface ClaimRow {
  claimId: string;
  text: string;
  claimType: string;
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
  const library = useFetch(() => api.conversations(), []);

  const [packId, setPackId] = useState<string | null>(null);
  const [chosen, setChosen] = useState<PreparedConversation | null>(null);
  const [title, setTitle] = useState("");
  const [titleTouched, setTitleTouched] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const stream = useJobStream(jobId);

  const packs = library.data?.packs ?? [];
  const pack: ConversationPack | null =
    packs.find((p) => p.pack_id === packId) ?? packs[0] ?? null;

  // Depends on the first pack's id rather than the array, which is a fresh
  // object every render and would re-run this on every keystroke.
  const firstPackId = packs[0]?.pack_id;
  useEffect(() => {
    if (!packId && firstPackId) setPackId(firstPackId);
  }, [firstPackId, packId]);

  // The title defaults to the conversation's own name and stays editable.
  useEffect(() => {
    if (chosen && !titleTouched) setTitle(chosen.title);
  }, [chosen, titleTouched]);

  const running = stream.status === "connecting" || stream.status === "streaming";
  const [now, setNow] = useState(0);
  const startedAt = useRef<number | null>(null);
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setNow(performance.now()), 100);
    return () => window.clearInterval(timer);
  }, [running]);
  useEffect(() => {
    if (jobId) {
      startedAt.current = performance.now();
      setNow(performance.now());
    }
  }, [jobId]);
  const elapsed = startedAt.current !== null ? (now - startedAt.current) / 1000 : 0;

  const claims = useMemo(() => claimsFromEvents(stream.events), [stream.events]);
  const core = useMemo(() => coreStateFrom(stream.events), [stream.events]);
  const logRef = useRef<HTMLOListElement>(null);
  useEffect(() => {
    logRef.current?.lastElementChild?.scrollIntoView({ block: "nearest" });
  }, [stream.events.length]);

  const submit = async () => {
    if (!pack || !chosen) return;
    setSubmitError(null);
    try {
      const job = await api.runConversation(pack.pack_id, chosen.conversation_id, title);
      setJobId(job.job_id);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : String(error));
    }
  };

  const reset = () => {
    setJobId(null);
    setChosen(null);
    setTitle("");
    setTitleTouched(false);
    startedAt.current = null;
  };

  if (availability.loading || library.loading)
    return <div className="page"><Loading what="prepared conversation library" /></div>;
  if (availability.error)
    return <div className="page"><ErrorState error={availability.error} retry={availability.retry} /></div>;

  const available = availability.data?.available ?? false;

  return (
    <div className="page rig">
      <header className="rig-head">
        <RevealLines as="h1" className="rig-display" lines={["ADJUDICATION", "RIG"]} />
        <Reveal delay={220}>
          <p className="rig-lede">
            Choose a corpus and a prepared conversation, name the assessment,
            and run it. Only the agent's turns are adjudicated; the consumer's
            turns are context and never receive a verdict.
          </p>
        </Reveal>
      </header>

      {!available && (
        <section className="rig-disabled">
          <span className="syslabel">live adjudication disabled</span>
          <p>{availability.data?.reason}</p>
          <p className="muted">
            The bench, corpus and delta all read stored evidence and work
            without credentials.
          </p>
        </section>
      )}

      {available && !jobId && (
        <div className="rig-config">
          <div className="rig-steps">
            {/* ---------------------------------------------- 01 corpus */}
            <section className="rig-step">
              <span className="rig-stepnum syslabel">01 / select corpus</span>
              <div className="rig-corpuslist">
                {packs.map((entry) => (
                  <button
                    key={entry.pack_id}
                    className={`rig-corpus ${entry.pack_id === pack?.pack_id ? "on" : ""}`}
                    onClick={() => {
                      setPackId(entry.pack_id);
                      setChosen(null);
                      setTitleTouched(false);
                    }}
                    data-cursor="select"
                  >
                    <span className="rig-corpusname">
                      {entry.policy_label ?? entry.pack_id}
                    </span>
                    <span className="rig-corpusmeta mono">
                      {entry.policy_citation ?? entry.pack_id} ·{" "}
                      {entry.provisions ?? "?"} provisions ·{" "}
                      {entry.count} prepared
                    </span>
                    {entry.pack_id === pack?.pack_id && (
                      <span className="rig-selected syslabel">selected</span>
                    )}
                  </button>
                ))}
              </div>
            </section>

            {/* ---------------------------------------- 02 conversation */}
            <section className="rig-step">
              <span className="rig-stepnum syslabel">02 / select conversation</span>
              {pack && pack.groups.length === 0 && (
                <p className="muted">
                  This pack has no prepared conversations yet.
                </p>
              )}
              {pack?.groups.map((group) => (
                <div className="rig-group" key={group.category}>
                  <h3 className="rig-grouptitle">
                    <span className={`rig-groupdot v-${group.category}`} aria-hidden="true" />
                    {group.label}
                    <span className="rig-groupcount mono">
                      {group.conversations.length}
                    </span>
                  </h3>
                  <ul className="rig-convlist">
                    {group.conversations.map((conversation, index) => (
                      <li key={conversation.conversation_id}>
                        <button
                          className={`rig-conv ${chosen?.conversation_id === conversation.conversation_id ? "on" : ""}`}
                          onClick={() => {
                            setChosen(conversation);
                            setTitleTouched(false);
                          }}
                          data-cursor="choose"
                        >
                          <span className="rig-convnum mono">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span className="rig-convbody">
                            <span className="rig-convtitle">{conversation.title}</span>
                            <span className="rig-convsummary">
                              {conversation.summary}
                            </span>
                            <span className="rig-convmeta mono">
                              {conversation.agent_turns} agent turn(s) ·{" "}
                              {conversation.customer_turns} context turn(s)
                              {conversation.verified && conversation.claims !== null
                                ? ` · ${conversation.claims} claims on record`
                                : " · not yet verified"}
                            </span>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </section>

            {/* ----------------------------------------------- 03 title */}
            <section className="rig-step">
              <span className="rig-stepnum syslabel">03 / assessment title</span>
              <input
                className="rig-title"
                value={title}
                placeholder={
                  chosen ? chosen.title : "choose a conversation first"
                }
                disabled={!chosen}
                onChange={(event) => {
                  setTitle(event.target.value);
                  setTitleTouched(true);
                }}
                maxLength={90}
              />
              <p className="rig-titlenote muted">
                This is the name the assessment carries on the bench. It
                replaces the generated identifier everywhere it appears.
              </p>
            </section>

            <button
              className="rig-run"
              onClick={() => void submit()}
              disabled={!chosen || !title.trim()}
              data-cursor="run"
            >
              run adjudication &rarr;
            </button>
            {submitError && (
              <p className="rig-submiterror mono" role="alert">
                {submitError}
              </p>
            )}
          </div>

          {/* ------------------------------------------- source preview */}
          <aside className="rig-preview">
            <span className="rig-stepnum syslabel">source conversation</span>
            {!chosen ? (
              <p className="muted rig-previewempty">
                Nothing selected. The conversation you choose is shown here in
                full before it runs, so there is no hidden input.
              </p>
            ) : (
              <>
                <ol className="rig-turns">
                  {chosen.turns.map((turn, index) => {
                    const isAgent = turn.role.toLowerCase() !== "customer";
                    return (
                      <li
                        key={index}
                        className={`rig-turn ${isAgent ? "agent" : "customer"}`}
                      >
                        <span className="rig-turnrole syslabel">
                          {isAgent ? "agent" : "consumer"}
                          {!isAgent && (
                            <span className="rig-turnnote"> context only</span>
                          )}
                        </span>
                        <p className="rig-turntext">{turn.text}</p>
                      </li>
                    );
                  })}
                </ol>
                {chosen.verified && (
                  <div className="rig-record">
                    <span className="syslabel">on record</span>
                    <p className="mono">
                      last run produced{" "}
                      {Object.entries(chosen.verdict_counts)
                        .map(([verdict, count]) => `${count} ${verdict}`)
                        .join(", ")}
                    </p>
                    {chosen.findings.length > 0 && (
                      <p className="mono rig-recordcites">
                        cited{" "}
                        {chosen.findings
                          .map((f) => f.section_id)
                          .filter(Boolean)
                          .join("  ")}
                      </p>
                    )}
                  </div>
                )}
              </>
            )}
          </aside>
        </div>
      )}

      {/* ----------------------------------------------------- execution */}
      {jobId && (
        <section className="rig-live">
          <div className="rig-livehead">
            <div>
              <span className="syslabel">assessment</span>
              <h2 className="rig-livetitle">{title}</h2>
              <span className="mono muted">{stream.final?.run_id ?? ""}</span>
            </div>
            <div className="rig-clockbox">
              <span className="mono rig-clock">{elapsed.toFixed(1)}s</span>
              <span className={`syslabel rig-status rig-status-${stream.status}`}>
                {stream.status === "lost"
                  ? "stream lost, the job continues on the server"
                  : stream.status}
              </span>
            </div>
          </div>

          <div className="rig-stage">
            <ComplianceCore
              state={core.state}
              tone={core.tone}
              scale="panel"
              sections={303}
              claims={Math.max(3, claims.length)}
            />
          </div>

          <div className="rig-columns">
            <div>
              <h3 className="syslabel">stage log, every line a real event</h3>
              <ol className="rig-log" ref={logRef} aria-live="polite">
                {stream.events.map((event) => (
                  <li
                    key={event.seq}
                    className={`rig-logline stage-${event.stage.replace(/\./g, "-")}`}
                  >
                    <span className="rig-log-at">[{event.at.toFixed(1)}s]</span>
                    <span className="rig-log-label">
                      {STAGE_LABELS[event.stage] ?? event.stage}
                    </span>
                    <span className="rig-log-note">{describe(event)}</span>
                  </li>
                ))}
                {stream.events.length === 0 && (
                  <li className="rig-logline muted">waiting for the first event</li>
                )}
              </ol>
            </div>

            <div className="rig-claims">
              <h3 className="syslabel">claims</h3>
              {claims.length === 0 ? (
                <p className="muted">none extracted yet</p>
              ) : (
                <ol className="rig-claimlist">
                  {claims.map((claim) => (
                    <li
                      key={claim.claimId}
                      className={`rig-claim ${claim.verdict ? "settled" : "inflight"}`}
                    >
                      <span className="mono faint">{claim.claimType}</span>
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
              <span className="syslabel">assessment failed</span>
              <p className="mono">{stream.error}</p>
            </div>
          )}

          {stream.status === "done" && stream.final?.result && (
            <div className="rig-done">
              <span className="syslabel">sealed</span>
              <p>
                {stream.final.result.findings} finding(s),{" "}
                {stream.final.result.supported ?? 0} supported,{" "}
                {stream.final.result.abstentions} abstention(s) across{" "}
                {stream.final.result.claims} claims from{" "}
                {stream.final.result.agent_turns ?? 0} agent turn(s).{" "}
                {stream.final.result.customer_turns_skipped ?? 0} consumer
                turn(s) were used as context and never adjudicated.
              </p>
              <p>
                <Link
                  to={`/runs/${stream.final.result.run_id}`}
                  className="rig-openlink mono"
                  data-cursor="open"
                >
                  open the assessment &rarr;
                </Link>
              </p>
              <button className="rig-again mono" onClick={reset} data-cursor="new">
                run another
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
