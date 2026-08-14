/** The case file. Not a card: the structure is the argument.
 *
 *   WHAT WAS SAID          the verbatim excerpt, highlighted by stored offset
 *   WHAT RULE GOVERNS IT   the judge's selected section, verbatim, in serif
 *   WHY                    verdict and rationale, severity from the pack
 *   PROOF                  hashes, model, prompt hash, thresholds
 *   TRACE                  the forensic chain, expandable
 *
 * The rule text shown is judge.rule's rule_text_in, which since the Phase 3
 * fix is the text of the section the judge selected. This screen must never
 * fall back to the top retrieval candidate's text.
 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { AudioEvidence, NoAudio } from "../components/AudioEvidence";
import { CandidateField } from "../components/CandidateField";
import { ComplianceCore } from "../components/ComplianceCore";
import { EvidenceTrace, type TraceStep } from "../components/EvidenceTrace";
import { ErrorState, Loading } from "../components/States";
import { Transcript } from "../components/Transcript";
import { VerdictMark } from "../components/VerdictMark";
import { shortHash } from "../lib/format";
import { VERDICT_META } from "../lib/verdicts";
import { useFetch } from "../lib/useFetch";
import type { Candidate, ClaimDetail, WordTiming } from "../types";
import "./claimcase.css";

export function ClaimCase() {
  const { runId = "", claimId = "" } = useParams();
  // Live loudness from the clip, so the core beside it moves with the
  // evidence rather than on a timer.
  const [amplitude, setAmplitude] = useState(0);
  const { data, error, loading, retry } = useFetch<ClaimDetail>(
    () => api.claim(runId, claimId),
    [runId, claimId],
  );

  if (loading) return <div className="page"><Loading what={`runs/${runId} claim ${claimId}`} /></div>;
  if (error) return <div className="page"><ErrorState error={error} retry={retry} /></div>;
  if (!data) return null;

  const { finding } = data;
  const meta = VERDICT_META[finding.verdict];
  const decidedBy = String(data.judge?.payload?.decided_by ?? "model");
  const isDeterministic = decidedBy === "deterministic";

  const emit = data.emit?.payload as
    | { clip_start_s?: number; clip_end_s?: number; audio_clip_ref?: string }
    | undefined;
  const wordTimings =
    (data.turn_audio?.payload?.word_timings as WordTiming[] | undefined) ?? null;

  const retrieval = data.retrieval?.payload as
    | {
        candidates?: Candidate[];
        thresholds?: Record<string, number>;
        retriever_config?: Record<string, unknown>;
        query?: string;
        cleared_floor?: boolean;
        cleared_ceiling?: boolean;
      }
    | undefined;
  const judge = data.judge?.payload as
    | {
        judge_selected_section_id?: string;
        judge_selected_score?: number;
        offered_section_ids?: string[];
        prompt_hash?: string;
        model?: string;
      }
    | undefined;

  const candidates = retrieval?.candidates ?? [];
  const thresholds = retrieval?.thresholds ?? {};
  const topCandidate = candidates[0] ?? null;
  const selectedSection =
    judge?.judge_selected_section_id ?? finding.section_id ?? null;
  const selectionDiffersFromRank1 =
    topCandidate !== null &&
    selectedSection !== null &&
    topCandidate.section_id !== selectedSection;

  const whyHeading =
    finding.verdict === "contradicted"
      ? "why it failed"
      : finding.verdict === "supported"
        ? "why it holds"
        : "why no decision";

  const queries = String(retrieval?.query ?? "")
    .split("|")
    .map((q) => q.trim())
    .filter(Boolean);

  const traceSteps: TraceStep[] = [
    {
      key: "turn",
      index: 1,
      label: "agent turn",
      detail: `${(finding.transcript ?? "").length} characters recorded, hashed as ${shortHash(String(data.turn?.payload?.transcript_hash ?? ""), 16)}. Only agent turns are adjudicated.`,
      hash: data.turn?.entry_hash,
      taken: Boolean(data.turn),
      body: (
        <p className="case-tracequote">{finding.transcript}</p>
      ),
    },
    {
      key: "claim",
      index: 2,
      label: "claim extracted",
      detail: `Located at offsets [${finding.char_start}:${finding.char_end}) as a verbatim span. A paraphrase would have been rejected rather than stored.`,
      hash: data.extract?.entry_hash,
      taken: Boolean(data.extract),
      body: (
        <p className="case-tracequote">"{finding.claim_text}"</p>
      ),
    },
    {
      key: "deterministic",
      index: 3,
      label: "deterministic check",
      detail: isDeterministic
        ? "Settled in code after canonical normalization. No model was involved and retrieval never ran."
        : data.deterministic.length > 0
          ? "Value normalised in code. Nothing known-true to compare it against, so it continued to retrieval."
          : "Not a numeric or date claim.",
      hash: data.deterministic.at(-1)?.entry_hash,
      taken: data.deterministic.length > 0,
      skippedNote: "Not a numeric or date claim, so no code check applies.",
      body:
        data.deterministic.length > 0 ? (
          <dl className="case-tracedl mono">
            {data.deterministic.map((span) => {
              const p = span.payload as Record<string, unknown>;
              return (
                <div key={span.span_id}>
                  <dt>{String(p.result)}</dt>
                  <dd>
                    parsed {String(p.value_parsed ?? "nothing")}
                    {p.expected_value != null &&
                      ` against ${String(p.expected_value)}`}
                    {p.detail ? ` (${String(p.detail)})` : ""}
                  </dd>
                </div>
              );
            })}
          </dl>
        ) : undefined,
    },
    {
      key: "retrieval",
      index: 4,
      label: "retrieval",
      detail: isDeterministic
        ? "Skipped. The claim was already settled in code, so no rule needed to be found."
        : `${candidates.length} candidate section(s) ranked from ${queries.length || 1} quer${queries.length === 1 ? "y" : "ies"} under different legal theories.`,
      hash: data.retrieval?.entry_hash,
      taken: Boolean(data.retrieval),
      skippedNote:
        "Skipped. The claim was settled in code before retrieval ran.",
      body: data.retrieval ? (
        <>
          {queries.length > 0 && (
            <ul className="case-queries">
              {queries.map((query) => (
                <li key={query} className="mono">
                  {query}
                </li>
              ))}
            </ul>
          )}
          <CandidateField
            candidates={candidates}
            floor={Number(thresholds.floor ?? 0)}
            ceiling={Number(thresholds.ceiling ?? 1)}
            selectedSection={selectedSection}
            selectedScore={
              typeof judge?.judge_selected_score === "number"
                ? judge.judge_selected_score
                : null
            }
          />
        </>
      ) : undefined,
    },
    {
      key: "rule",
      index: 5,
      label: "governing rule",
      detail: finding.rule_text
        ? `${selectedSection} selected from ${(judge?.offered_section_ids ?? []).length} offered section(s).`
        : "No section was selected as governing this claim.",
      taken: Boolean(finding.rule_text),
      skippedNote:
        finding.verdict === "no_governing_rule"
          ? "Nothing in the corpus cleared the retrieval floor, so no rule was ever offered."
          : "No governing section was selected.",
      body: finding.rule_text ? (
        <blockquote className="law case-tracerule">
          {finding.rule_text}
        </blockquote>
      ) : undefined,
    },
    {
      key: "judge",
      index: 6,
      label: "judge",
      detail: isDeterministic
        ? "Not consulted. Code decided this claim."
        : `Ruled from the selected text alone, at retrieval score ${judge?.judge_selected_score?.toFixed?.(3) ?? "-"}.`,
      hash: data.judge?.entry_hash,
      taken: Boolean(data.judge) && !isDeterministic,
      skippedNote: "Not consulted. The claim was decided in code.",
      body: (
        <p className="case-tracerationale">{finding.rationale}</p>
      ),
    },
    {
      key: "verdict",
      index: 7,
      label: "verdict",
      detail: `${finding.verdict.replace(/_/g, " ")}${finding.section_id ? ` at ${finding.section_id}` : ""}, severity ${finding.severity} from the client's criteria pack.`,
      taken: true,
    },
    {
      key: "seal",
      index: 8,
      label: "evidence seal",
      detail:
        "Written into the append-only chain. Entry N covers entry N minus one, so altering anything earlier invalidates every hash after it.",
      hash: finding.entry_hash,
      taken: true,
      body: (
        <dl className="case-tracedl mono">
          <div>
            <dt>entry hash</dt>
            <dd>{finding.entry_hash}</dd>
          </div>
          {data.emit && (
            <div>
              <dt>previous</dt>
              <dd>{data.emit.prev_hash}</dd>
            </div>
          )}
        </dl>
      ),
    },
  ];

  return (
    <article className="page case">
      <nav className="case-crumb mono">
        <Link to={`/runs/${runId}`}>{runId}</Link>
        <span className="faint"> / </span>
        <span>{finding.claim_id}</span>
      </nav>

      <header className="case-head">
        <VerdictMark verdict={finding.verdict} />
        <span className="case-cite mono">
          {finding.section_id ?? "no section cited"}
        </span>
        <span className="case-sev syslabel" data-sev={finding.severity}>
          severity {finding.severity}
        </span>
        {isDeterministic && (
          <span className="case-deterministic syslabel">
            decided in code, no model involved
          </span>
        )}
      </header>
      <p className="case-meaning muted">{meta.meaning}</p>

      {/* WHAT WAS SAID */}
      <section className="case-section">
        <h2 className="syslabel">what was said</h2>
        <Transcript
          transcript={finding.transcript ?? ""}
          charStart={finding.char_start}
          charEnd={finding.char_end}
          verdict={finding.verdict}
        />
        <p className="mono faint case-offsets">
          turn {finding.turn_id} &middot; offsets [{finding.char_start}:
          {finding.char_end}) into the recorded transcript
        </p>
        <div className="case-audio">
          {finding.has_clip && finding.audio_clip_ref && emit ? (
            <div className="case-audiorig">
              <AudioEvidence
                src={api.clipUrl(runId, finding.audio_clip_ref)}
                clipStart={emit.clip_start_s ?? 0}
                clipEnd={emit.clip_end_s ?? 0}
                wordTimings={wordTimings}
                clipRef={finding.audio_clip_ref}
                onAmplitude={setAmplitude}
              />
              <div className="case-audiocore">
                <ComplianceCore
                  scale="mini"
                  state="verdict"
                  tone={
                    finding.verdict === "contradicted"
                      ? "contradicted"
                      : finding.verdict === "supported"
                        ? "supported"
                        : "abstain"
                  }
                  amplitude={amplitude}
                  sections={120}
                  claims={5}
                />
                <span className="syslabel case-audiocorenote">
                  moves with the clip
                </span>
              </div>
            </div>
          ) : (
            <NoAudio />
          )}
        </div>
      </section>

      {/* WHAT RULE GOVERNS IT */}
      <section className="case-section">
        <h2 className="syslabel">what rule governs it</h2>
        {finding.rule_text ? (
          <blockquote className="law case-rule">
            <p>{finding.rule_text}</p>
            <footer className="mono">{selectedSection}</footer>
          </blockquote>
        ) : (
          <p className="muted case-norule">
            {finding.verdict === "no_governing_rule"
              ? "Nothing in the corpus cleared the retrieval floor for this claim. No rule text was ever passed to a judge; that absence is the verdict."
              : "No rule text was passed to the judge for this claim."}
          </p>
        )}
      </section>

      {/* WHY */}
      <section className="case-section">
        <h2 className="syslabel">{whyHeading}</h2>
        <p className="case-rationale">{finding.rationale}</p>
        {data.deterministic.length > 0 && (
          <div className="case-detchecks">
            {data.deterministic.map((span) => {
              const p = span.payload as Record<string, unknown>;
              return (
                <p key={span.span_id} className="mono muted">
                  check.deterministic &middot; parsed {String(p.value_parsed ?? "nothing")}
                  {p.expected_value != null && ` against ${String(p.expected_value)}`}
                  {" "}&middot; {String(p.result)}
                  {p.detail ? ` (${String(p.detail)})` : ""}
                </p>
              );
            })}
          </div>
        )}
      </section>

      {/* PROOF */}
      <section className="case-section">
        <h2 className="syslabel">proof</h2>
        <dl className="case-proof mono">
          <div>
            <dt>integrity hash</dt>
            <dd title={finding.entry_hash}>{shortHash(finding.entry_hash, 24)}</dd>
          </div>
          <div>
            <dt>model</dt>
            <dd>{isDeterministic ? "none (decided in code)" : finding.model || "-"}</dd>
          </div>
          {!isDeterministic && (
            <div>
              <dt>prompt hash</dt>
              <dd title={finding.prompt_hash}>{shortHash(finding.prompt_hash, 24)}</dd>
            </div>
          )}
          {retrieval?.retriever_config ? (
            <div>
              <dt>retriever</dt>
              <dd>
                {String(retrieval.retriever_config.retriever ?? "")} &middot;{" "}
                {String(retrieval.retriever_config.model ?? "")}
              </dd>
            </div>
          ) : null}
          {Object.keys(thresholds).length > 0 && (
            <div>
              <dt>thresholds</dt>
              <dd>
                floor {thresholds.floor} &middot; ceiling {thresholds.ceiling}{" "}
                &middot; conflict margin {thresholds.conflict_margin}
              </dd>
            </div>
          )}
        </dl>
      </section>

      {/* TRACE */}
      <section className="case-section case-tracesection">
        <div className="case-tracehead">
          <h2 className="syslabel">evidence trace</h2>
          {selectionDiffersFromRank1 && (
            <span className="case-rankflag mono">
              judge selected {selectedSection}, not the top ranked candidate
            </span>
          )}
        </div>
        <EvidenceTrace
          initiallyOpen={finding.verdict === "contradicted" ? "retrieval" : undefined}
          steps={traceSteps}
        />
      </section>
    </article>
  );
}
