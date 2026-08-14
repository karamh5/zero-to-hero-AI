/** The bench: completed assessments, presented as work rather than rows.
 *
 * An assessment carries a number, the title whoever ran it chose, the corpus
 * it was judged against, its verdict summary, and whether audio evidence is
 * attached. Audio presence is stated explicitly in both directions, because
 * "some entries have it and some do not" is only mysterious when the absence
 * is left unsaid.
 *
 * Runs made before titles existed show their identifier instead. Inventing a
 * name for them would be worse than admitting they predate the convention.
 */

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { ComplianceCore } from "../components/ComplianceCore";
import { Reveal, RevealLines } from "../components/Reveal";
import { Empty, ErrorState, Loading } from "../components/States";
import { useFetch } from "../lib/useFetch";
import type { RunSummary } from "../types";
import "./bench.css";

/** Assessment number: the trailing digits of an assessment- run, otherwise a
 * stable position so every entry has a large numeral to navigate by. */
function numberFor(run: RunSummary, fallbackIndex: number): string {
  const match = run.run_id.match(/^assessment-(\d+)$/);
  if (match) return match[1].padStart(3, "0");
  return String(fallbackIndex).padStart(3, "0");
}

function displayTitle(run: RunSummary): string {
  if (run.title) return run.title;
  return run.run_id.replace(/[-_]/g, " ");
}

function natureOf(run: RunSummary): string[] {
  const parts: string[] = [];
  if (run.artifacts.campaign) parts.push("campaign");
  if (run.artifacts.scored) parts.push("scored split");
  if (run.artifacts.rerun) parts.push("fix and re-run");
  if (run.artifacts.swap) parts.push("pack swap");
  if (run.run_id.startsWith("assessment-")) parts.push("prepared adjudication");
  return parts;
}

export function Bench() {
  const { data, error, loading, retry } = useFetch(() => api.runs(), []);
  const [open, setOpen] = useState<string | null>(null);

  const ordered = useMemo(() => {
    const runs = data?.runs ?? [];
    // Assessments first, newest number first, then everything else by name.
    const rank = (run: RunSummary) => (run.run_id.startsWith("assessment-") ? 0 : 1);
    return [...runs].sort((a, b) => {
      const byKind = rank(a) - rank(b);
      if (byKind !== 0) return byKind;
      if (rank(a) === 0) return b.run_id.localeCompare(a.run_id);
      return a.run_id.localeCompare(b.run_id);
    });
  }, [data]);

  if (loading) return <div className="page"><Loading what="assessments on disk" /></div>;
  if (error) return <div className="page"><ErrorState error={error} retry={retry} /></div>;

  if (ordered.length === 0) {
    return (
      <div className="page">
        <BenchIntro />
        <Empty
          label="no assessments yet"
          detail="Run a prepared adjudication on the rig and it will appear here."
        />
      </div>
    );
  }

  return (
    <div className="page bench">
      <BenchIntro />
      <ol className="bench-list">
        {ordered.map((run, index) => {
          const expanded = open === run.run_id;
          return (
            <Reveal as="li" key={run.run_id} delay={Math.min(index, 6) * 45}>
              <article
                className={`bench-entry ${expanded ? "open" : ""}`}
                onPointerEnter={() => setOpen(run.run_id)}
                onPointerLeave={() => setOpen((c) => (c === run.run_id ? null : c))}
              >
                <span className="bench-number mono" aria-hidden="true">
                  {numberFor(run, index + 1)}
                </span>

                <div className="bench-body">
                  <h2 className="bench-title">
                    <Link to={`/runs/${run.run_id}`} data-cursor="open case">
                      {displayTitle(run)}
                    </Link>
                  </h2>

                  <div className="bench-tags">
                    {run.pack_id && (
                      <span className="bench-tag mono">
                        {run.pack_id.toUpperCase().replace("_", "-")}
                      </span>
                    )}
                    {natureOf(run).map((part) => (
                      <span className="bench-tag mono" key={part}>
                        {part}
                      </span>
                    ))}
                    <span className="bench-tag mono">
                      {run.chain_ok ? "chain verified" : "CHAIN FAILED"}
                      {run.seal_state === "intact" && " · sealed"}
                    </span>
                  </div>

                  {run.chain_ok && (
                    <dl className="bench-counts">
                      <div>
                        <dt className="syslabel">findings</dt>
                        <dd className="mono" data-nonzero={run.violations > 0}>
                          {String(run.violations).padStart(2, "0")}
                        </dd>
                      </div>
                      <div>
                        <dt className="syslabel">supported</dt>
                        <dd className="mono">
                          {String(run.supported).padStart(2, "0")}
                        </dd>
                      </div>
                      <div>
                        <dt className="syslabel">abstentions</dt>
                        <dd className="mono">
                          {String(run.abstentions).padStart(2, "0")}
                        </dd>
                      </div>
                      <div>
                        <dt className="syslabel">claims</dt>
                        <dd className="mono">
                          {String(run.claims).padStart(2, "0")}
                        </dd>
                      </div>
                    </dl>
                  )}

                  <p className="bench-audio mono">
                    {run.clip_count > 0 ? (
                      <>
                        <span className="bench-audioon">audio</span>{" "}
                        {run.clip_count} clip(s) attached
                      </>
                    ) : (
                      <>
                        <span className="bench-audiooff">audio</span> not
                        attached, this assessment ran on text
                      </>
                    )}
                  </p>
                </div>

                <div className="bench-core" aria-hidden="true">
                  {/* Mounted only for the entry being looked at. Each core
                      holds a WebGL context and browsers cap those at around
                      sixteen; mounting one per row silently dropped contexts
                      and wedged the page on a bench of any size. */}
                  {expanded && (
                    <ComplianceCore
                      scale="mini"
                      state={
                        !run.chain_ok
                          ? "idle"
                          : run.violations > 0
                            ? "verdict"
                            : "sealed"
                      }
                      tone={
                        run.violations > 0
                          ? "contradicted"
                          : run.supported > 0
                            ? "supported"
                            : "abstain"
                      }
                      sections={Math.max(40, Math.min(run.span_count * 2, 220))}
                      claims={Math.max(3, Math.min(run.claims, 10))}
                    />
                  )}
                  <Link
                    className="bench-open mono"
                    to={`/runs/${run.run_id}`}
                    data-cursor="open case"
                  >
                    open case file &rarr;
                  </Link>
                </div>
              </article>
            </Reveal>
          );
        })}
      </ol>
    </div>
  );
}

function BenchIntro() {
  return (
    <header className="bench-head">
      <RevealLines as="h1" className="bench-display" lines={["ASSESSMENT", "BENCH"]} />
      <Reveal delay={240}>
        <p className="bench-lede">
          Completed adjudications, each one an append-only hash-chained
          evidence log. Open an assessment to read every verdict against the
          rule text it rests on.
        </p>
      </Reveal>
    </header>
  );
}
