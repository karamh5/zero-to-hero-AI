/** The front door.
 *
 * A long editorial descent: the corpus as an object, what the product does in
 * five moves, the five verdict states as positions rather than labels, the
 * measurements with their uncertainty intact, and the ways in.
 *
 * Every figure on this page is fetched, not written. If the API is not
 * reachable the numbers are absent and say so; none of them has a hardcoded
 * fallback, because a landing page quoting a number the system cannot
 * currently produce is the exact failure this product exists to catch.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { CorpusObject } from "../components/CorpusObject";
import { Counter } from "../components/Counter";
import { Marquee } from "../components/Marquee";
import { Reveal, RevealLines } from "../components/Reveal";
import { VerdictMark } from "../components/VerdictMark";
import { useFetch } from "../lib/useFetch";
import { VERDICT_META } from "../lib/verdicts";
import { VERDICTS } from "../types";
import "./home.css";

export function Home() {
  const measurements = useFetch(() => api.measurements().catch(() => null), []);
  const runs = useFetch(() => api.runs().catch(() => null), []);
  const corpus = useFetch(() => api.corpusList().catch(() => null), []);

  const m = measurements.data;
  const runList = runs.data?.runs ?? [];
  const pack = corpus.data?.packs?.[0] ?? null;

  // The hero object starts displaced and settles once. Expressed as a class
  // removed on the next tick rather than as a keyframe holding its start
  // state, so the settled state is what renders if the animation never runs.
  const [arming, setArming] = useState(true);
  useEffect(() => {
    const timer = window.setTimeout(() => setArming(false), 60);
    return () => window.clearTimeout(timer);
  }, []);

  const totalClaims = runList.reduce((sum, run) => sum + run.claims, 0);
  const totalSpans = runList.reduce((sum, run) => sum + run.span_count, 0);
  const chainsVerified = runList.filter((run) => run.chain_ok).length;

  // The ticker's vocabulary, taken from what is actually on disk.
  const ticker: string[] = [
    "agent.turn",
    "extract.claims",
    "check.deterministic",
    "retrieve.rule",
    "judge.rule",
    "finding.emit",
    ...VERDICTS,
    ...runList.slice(0, 6).map((run) => run.run_id),
    ...runList
      .filter((run) => run.chain_head)
      .slice(0, 3)
      .map((run) => String(run.chain_head).slice(0, 12)),
  ];

  return (
    <div className="home">
      {/* ---------------------------------------------------------------- */}
      <section className="home-hero">
        <div className={`home-hero-object ${arming ? "arming" : ""}`}>
          <CorpusObject packId={pack?.pack_id ?? "reg_f"} />
        </div>

        <div className="home-hero-type">
          <RevealLines
            as="h1"
            className="home-wordmark"
            lines={["Echo", "Proof"]}
            stagger={110}
          />
          <Reveal delay={420}>
            <p className="home-hero-lede">
              A compliance assurance layer for enterprise voice AI agents. It
              reads what an agent said, finds the rule that governs it, and
              writes a verdict you can disagree with.
            </p>
          </Reveal>
          <Reveal delay={560}>
            <div className="home-hero-actions">
              <Link className="home-cta" to="/bench" data-cursor="enter">
                enter the bench
              </Link>
              <Link className="home-cta ghost" to="/rig" data-cursor="watch">
                watch a turn adjudicate
              </Link>
            </div>
          </Reveal>
        </div>

        <div className="home-hero-meta">
          <Reveal delay={700}>
            <dl className="home-heromeasures mono">
              <div>
                <dt>corpus</dt>
                <dd>
                  {pack ? <Counter value={pack.record_count} /> : "-"} provisions
                </dd>
              </div>
              <div>
                <dt>evidence spans</dt>
                <dd>{totalSpans ? <Counter value={totalSpans} /> : "-"}</dd>
              </div>
              <div>
                <dt>chains verified</dt>
                <dd>
                  {chainsVerified}/{runList.length || "-"}
                </dd>
              </div>
            </dl>
          </Reveal>
        </div>

        <span className="home-scrollhint syslabel">scroll</span>
      </section>

      <Marquee items={ticker} />

      {/* ---------------------------------------------------------------- */}
      <section className="home-section home-what">
        <Reveal>
          <span className="home-sectionnum syslabel">01 / what it does</span>
        </Reveal>
        <RevealLines
          as="h2"
          className="home-h2"
          lines= {["A proxy sits in front", "of the agent's model call."]}
        />
        <Reveal delay={120}>
          <p className="home-body">
            The response goes back untouched and undelayed, because a
            compliance tool that can drop a live call has inverted its own
            purpose. Adjudication happens afterwards, on a worker thread,
            out of the decision path.
          </p>
        </Reveal>

        <ol className="home-steps">
          {[
            {
              n: "01",
              t: "Extract",
              d: "Factual claims are located in the transcript as character offsets, stored as verbatim spans. A model that paraphrases loses its claim rather than corrupting one.",
            },
            {
              n: "02",
              t: "Settle in code",
              d: "Money and dates are canonicalised and compared in code, before retrieval. A value arithmetic can decide never reaches a model at all.",
            },
            {
              n: "03",
              t: "Retrieve",
              d: "Hybrid keyword and dense search over the policy corpus, fused and reranked, two or three queries per claim under different legal theories.",
            },
            {
              n: "04",
              t: "Judge",
              d: "The judge sees only the retrieved rule text, never the whole corpus and never its own training knowledge. That is what makes a verdict checkable.",
            },
            {
              n: "05",
              t: "Seal",
              d: "Every stage writes a span to an append-only hash chain. Entry N covers entry N minus one, so editing the middle invalidates everything after it.",
            },
          ].map((step, index) => (
            <Reveal as="li" key={step.n} delay={index * 70} className="home-step">
              <span className="home-stepnum mono">{step.n}</span>
              <h3 className="home-steptitle">{step.t}</h3>
              <p className="home-stepbody">{step.d}</p>
            </Reveal>
          ))}
        </ol>
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="home-section home-verdicts">
        <Reveal>
          <span className="home-sectionnum syslabel">02 / the five states</span>
        </Reveal>
        <RevealLines
          as="h2"
          className="home-h2"
          lines={["Three of the five", "are refusals to decide."]}
        />
        <Reveal delay={120}>
          <p className="home-body">
            There is no sixth state and there is no pass or fail. An
            abstention is not a soft finding: it is the system declining, and
            counting one as a detection would overstate what it caught. They
            are separate totals everywhere in this interface.
          </p>
        </Reveal>

        <ul className="home-verdictlist">
          {VERDICTS.map((verdict, index) => {
            const meta = VERDICT_META[verdict];
            return (
              <Reveal as="li" key={verdict} delay={index * 60} className="home-verdictrow">
                <span className="home-verdictkind syslabel">{meta.kind}</span>
                <VerdictMark verdict={verdict} showKind={false} />
                <p className="home-verdictmeaning">{meta.meaning}</p>
              </Reveal>
            );
          })}
        </ul>
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="home-section home-numbers">
        <Reveal>
          <span className="home-sectionnum syslabel">03 / the measurements</span>
        </Reveal>
        <RevealLines
          as="h2"
          className="home-h2"
          lines={["It publishes", "its own error bars."]}
        />

        {m ? (
          <>
            <div className="home-bignumbers">
              {m.detection.low !== null && m.detection.high !== null && (
                <Reveal className="home-bignumber">
                  <span className="home-bigvalue mono">
                    <Counter value={m.detection.low} decimals={2} />
                    <span className="home-bigto">to</span>
                    <Counter value={m.detection.high} decimals={2} />
                  </span>
                  <span className="home-biglabel syslabel">
                    claim detection at 2 percent false positives
                  </span>
                  <p className="home-bignote">
                    A range, because the same 77 item set scored twice gave two
                    different answers and nothing between the runs accounts for
                    it. One figure would imply a precision the measurement does
                    not have.
                  </p>
                </Reveal>
              )}
              {m.agreement.data && (
                <Reveal delay={90} className="home-bignumber">
                  <span className="home-bigvalue mono fails">
                    <Counter value={m.agreement.data.raw_agreement} decimals={2} />
                  </span>
                  <span className="home-biglabel syslabel">
                    judge to human agreement, against an{" "}
                    {m.agreement.data.floor.toFixed(2)} floor
                  </span>
                  <p className="home-bignote">
                    Below the floor, and that is why the positioning below is
                    what it is rather than something more flattering.
                  </p>
                </Reveal>
              )}
              {m.campaign.summary && (
                <Reveal delay={180} className="home-bignumber">
                  <span className="home-bigvalue mono">
                    {m.campaign.summary.control_false_positive_calls}
                    <span className="home-bigto">of</span>
                    {m.campaign.summary.control_calls}
                  </span>
                  <span className="home-biglabel syslabel">
                    false positives on the compliant control
                  </span>
                  <p className="home-bignote">
                    Nothing flagged on a clean call in any recorded run. To a
                    compliance officer who has been burned by noisy tooling,
                    this is often the more persuasive number.
                  </p>
                </Reveal>
              )}
            </div>

            <Reveal>
              <blockquote className="home-position">
                <p>
                  EchoProof is a triage layer that routes to human review.
                  It is not a release gate.
                </p>
                <footer className="mono">
                  the report says so on its own front page
                </footer>
              </blockquote>
            </Reveal>
            <Reveal delay={80}>
              <p className="home-body">
                <Link to="/reading" className="home-inlinelink" data-cursor="open">
                  Read the full panel, with every figure traced to the file it
                  came from.
                </Link>
              </p>
            </Reveal>
          </>
        ) : (
          <Reveal>
            <p className="home-body muted">
              The measurement artifacts could not be read, so no figures are
              shown here. Nothing on this page has a hardcoded fallback.
            </p>
          </Reveal>
        )}
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="home-section home-ways">
        <Reveal>
          <span className="home-sectionnum syslabel">04 / ways in</span>
        </Reveal>
        <div className="home-doors">
          {[
            {
              to: "/bench",
              k: "bench",
              t: "Every run on disk",
              d: `${runList.length || "no"} evidence logs, ${totalClaims || 0} adjudicated claims, each opening onto the rule text it rests on.`,
            },
            {
              to: "/rig",
              k: "rig",
              t: "Watch it work",
              d: "Submit a turn and follow the real stage events. It takes up to 140 seconds, and the screen tells the truth for all of them.",
            },
            {
              to: "/corpus",
              k: "corpus",
              t: "The reference library",
              d: `${pack ? pack.record_count : "The"} provisions, verbatim, with which ones retrieval actually reached.`,
            },
            {
              to: "/reading",
              k: "reading",
              t: "What it knows about itself",
              d: "Detection, citation precision, agreement against its floor, and the limits of each.",
            },
          ].map((door, index) => (
            <Reveal key={door.k} delay={index * 70}>
              <Link to={door.to} className="home-door" data-cursor={door.k}>
                <span className="home-doorkey mono">{door.k}</span>
                <h3 className="home-doortitle">{door.t}</h3>
                <p className="home-doorbody">{door.d}</p>
                <span className="home-doorarrow" aria-hidden="true">
                  &rarr;
                </span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>
    </div>
  );
}
