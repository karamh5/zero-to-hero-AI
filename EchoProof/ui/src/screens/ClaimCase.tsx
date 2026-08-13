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

import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { AudioEvidence, NoAudio } from "../components/AudioEvidence";
import { ErrorState, Loading } from "../components/States";
import { ThresholdBand } from "../components/ThresholdBand";
import { Transcript } from "../components/Transcript";
import { VerdictMark } from "../components/VerdictMark";
import { shortHash } from "../lib/format";
import { VERDICT_META } from "../lib/verdicts";
import { useFetch } from "../lib/useFetch";
import type { Candidate, ClaimDetail, WordTiming } from "../types";
import "./claimcase.css";

export function ClaimCase() {
  const { runId = "", claimId = "" } = useParams();
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
            <AudioEvidence
              src={api.clipUrl(runId, finding.audio_clip_ref)}
              clipStart={emit.clip_start_s ?? 0}
              clipEnd={emit.clip_end_s ?? 0}
              wordTimings={wordTimings}
              clipRef={finding.audio_clip_ref}
            />
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
      <section className="case-section">
        <details className="case-trace" open={finding.verdict === "contradicted"}>
          <summary>
            <span className="syslabel">trace: how this verdict was reached</span>
            {selectionDiffersFromRank1 && (
              <span className="case-rankflag mono">
                judge selected {selectedSection}, not the top-ranked candidate
              </span>
            )}
          </summary>

          <ol className="trace-chain">
            <TraceNode
              label="agent.turn"
              hash={data.turn?.entry_hash}
              body={`${(finding.transcript ?? "").length} characters recorded, transcript hash ${shortHash(String(data.turn?.payload?.transcript_hash ?? ""), 16)}`}
            />
            <TraceNode
              label="extract.claims"
              hash={data.extract?.entry_hash}
              body={`claim located at [${finding.char_start}:${finding.char_end}) as a verbatim span; a paraphrase would have been rejected`}
            />
            {isDeterministic ? (
              <TraceNode
                label="check.deterministic"
                hash={data.deterministic.at(-1)?.entry_hash}
                body="value compared in code after canonical normalization. Retrieval and judge never ran for this claim; the path ends here."
                terminal
              />
            ) : (
              <>
                <TraceNode
                  label="retrieve.rule"
                  hash={data.retrieval?.entry_hash}
                  body={
                    retrieval?.query
                      ? `queries: ${retrieval.query}`
                      : "no retrieval span recorded for this claim"
                  }
                />
                <TraceNode
                  label="judge.rule"
                  hash={data.judge?.entry_hash}
                  body={`${(judge?.offered_section_ids ?? []).length} section(s) offered; selected ${selectedSection ?? "none"} at score ${judge?.judge_selected_score?.toFixed?.(3) ?? "-"}`}
                />
              </>
            )}
            {data.emit && (
              <TraceNode
                label="finding.emit"
                hash={data.emit.entry_hash}
                body="finding written to the chain with its audio reference"
                terminal
              />
            )}
          </ol>

          {!isDeterministic && candidates.length > 0 && (
            <>
              <h3 className="syslabel trace-sub">
                the shortlist, and where the thresholds fell
              </h3>
              <ThresholdBand
                candidates={candidates}
                floor={Number(thresholds.floor ?? 0)}
                ceiling={Number(thresholds.ceiling ?? 1)}
                conflictMargin={Number(thresholds.conflict_margin ?? 0)}
                selectedSection={selectedSection}
                selectedScore={
                  typeof judge?.judge_selected_score === "number"
                    ? judge.judge_selected_score
                    : null
                }
              />

              <table className="plain trace-candidates">
                <thead>
                  <tr>
                    <th>candidate section</th>
                    <th>score</th>
                    <th>bm25 rank</th>
                    <th>dense rank</th>
                    <th>outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((candidate, index) => {
                    const isSelected = candidate.section_id === selectedSection;
                    return (
                      <tr key={candidate.chunk_id} className={isSelected ? "selected" : ""}>
                        <td className="mono">{candidate.section_id}</td>
                        <td className="num">{candidate.score.toFixed(3)}</td>
                        <td className="num">{candidate.bm25_rank ?? "-"}</td>
                        <td className="num">{candidate.dense_rank ?? "-"}</td>
                        <td className="mono">
                          {isSelected
                            ? index === 0
                              ? "selected by the judge"
                              : `selected by the judge over ${index} higher-ranked`
                            : index === 0
                              ? "top ranked, not selected"
                              : ""}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="muted trace-note">
                Rank 1 is unreliable while the shortlist is not: the governing
                section is nearly always retrieved and rarely ranked first,
                which is why selection exists. When the selected row is not the
                top row, that is the system working as measured, not a glitch.
              </p>
            </>
          )}
        </details>
      </section>
    </article>
  );
}

function TraceNode({
  label,
  hash,
  body,
  terminal = false,
}: {
  label: string;
  hash?: string;
  body: string;
  terminal?: boolean;
}) {
  return (
    <li className={`trace-node ${terminal ? "terminal" : ""}`}>
      <span className="trace-nodelabel mono">{label}</span>
      {hash && (
        <span className="trace-nodehash mono faint" title={hash}>
          {shortHash(hash, 16)}
        </span>
      )}
      <p className="trace-nodebody muted">{body}</p>
    </li>
  );
}
