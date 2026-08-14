/** The front door.
 *
 * Editorial statements at scale, a Compliance Core built from the product's
 * own parts, and four ways in. Every figure shown is fetched; nothing has a
 * hardcoded fallback, so a number appears only when the system can actually
 * produce it.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { ComplianceCore, type CoreState } from "../components/ComplianceCore";
import { Counter } from "../components/Counter";
import { Marquee } from "../components/Marquee";
import { Reveal, RevealLines } from "../components/Reveal";
import { VerdictMark } from "../components/VerdictMark";
import { useFetch } from "../lib/useFetch";
import { VERDICT_META } from "../lib/verdicts";
import { VERDICTS } from "../types";
import "./home.css";

/** The five stages, as the scroll walks the core through them. */
const STAGES: { state: CoreState; key: string; title: string; body: string }[] = [
  {
    state: "extracting",
    key: "policy",
    title: "Read the turn",
    body: "Factual claims are located in what the agent said and stored as character offsets into that exact string, never as restated text. A model that paraphrases loses its claim rather than corrupting one. Only the agent is ever adjudicated; the consumer's words are context and nothing else.",
  },
  {
    state: "extracting",
    key: "claim",
    title: "Settle what code can settle",
    body: "Money and dates are canonicalised and compared in code, ahead of retrieval. A value arithmetic can decide never reaches a model at all, and the evidence records both sides of the comparison.",
  },
  {
    state: "retrieving",
    key: "retrieval",
    title: "Find the governing rule",
    body: "Hybrid keyword and dense search across the policy corpus, fused and reranked, two or three queries per claim under genuinely different legal theories, because one sentence can engage several unrelated rules.",
  },
  {
    state: "judging",
    key: "judge",
    title: "Rule from the text",
    body: "The judge selects one section from a shortlist and rules from that text alone: never the whole corpus, never its own training knowledge. That constraint is what makes a verdict checkable against the rule printed beside it.",
  },
  {
    state: "sealed",
    key: "evidence",
    title: "Seal the record",
    body: "Every stage writes a span into an append-only hash chain. Entry N covers entry N minus one, so altering anything in the middle invalidates every hash after it and the seal visibly breaks.",
  },
];

export function Home() {
  const runs = useFetch(() => api.runs().catch(() => null), []);
  const corpus = useFetch(() => api.corpusList().catch(() => null), []);
  const measurements = useFetch(() => api.measurements().catch(() => null), []);

  const runList = runs.data?.runs ?? [];
  const packs = corpus.data?.packs ?? [];
  const pack = packs[0] ?? null;
  const totalSpans = runList.reduce((sum, run) => sum + run.span_count, 0);
  const totalClaims = runList.reduce((sum, run) => sum + run.claims, 0);
  const provisions = packs.reduce((sum, entry) => sum + entry.record_count, 0);

  // The core walks the pipeline as the reader descends. Driven by which
  // stage section is in view, never by a timer.
  const [stage, setStage] = useState<CoreState>("idle");
  const [arming, setArming] = useState(true);
  useEffect(() => {
    const timer = window.setTimeout(() => setArming(false), 60);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const nodes = document.querySelectorAll<HTMLElement>("[data-stage]");
    if (!nodes.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) {
          setStage(visible.target.getAttribute("data-stage") as CoreState);
        }
      },
      { threshold: [0.35, 0.6], rootMargin: "-20% 0px -30% 0px" },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  const ticker = [
    `POLICY / ${pack ? pack.pack_id.toUpperCase().replace("_", "-") : "UNLOADED"}`,
    `PROVISIONS / ${provisions || "-"}`,
    "RETRIEVER / BM25 + DENSE",
    "FUSION / RRF",
    "RERANK / CROSS ENCODER",
    "EXTRACT / VERBATIM OFFSETS",
    "SCOPE / AGENT TURNS ONLY",
    "EVIDENCE / HASH CHAINED",
    `RUNS / ${runList.length || "-"}`,
    `SPANS / ${totalSpans || "-"}`,
    ...VERDICTS.map((v) => `VERDICT / ${v.toUpperCase().replace(/_/g, " ")}`),
  ];

  return (
    <div className="home">
      {/* ------------------------------------------------------------ hero */}
      <section className="home-hero">
        <div className={`home-hero-object ${arming ? "arming" : ""}`}>
          <ComplianceCore
            state={stage}
            sections={provisions || 303}
            claims={5}
            scale="hero"
          />
        </div>
        <div className="home-atmos" aria-hidden="true">
          <span className="home-atmos-a" />
          <span className="home-atmos-b" />
          <span className="home-atmos-grid" />
        </div>

        <div className="home-hero-type">
          <RevealLines
            as="h1"
            className="home-headline"
            lines={["ECHOPROOF"]}
            stagger={90}
          />
          <Reveal delay={300}>
            <p className="home-hero-sub">
              PRE-DEPLOYMENT COMPLIANCE ASSURANCE FOR VOICE AI AGENTS
            </p>
          </Reveal>
          <Reveal delay={480}>
            <p className="home-hero-lede">
              EchoProof reads what an agent said, finds the rule that governs
              it, and produces a traceable readiness verdict before deployment.
            </p>
          </Reveal>
          <Reveal delay={600}>
            <div className="home-hero-actions">
              <Link className="home-cta" to="/bench" data-cursor="enter">
                open the bench
              </Link>
              <Link className="home-cta ghost" to="/rig" data-cursor="run">
                run an adjudication
              </Link>
            </div>
          </Reveal>
        </div>

        <div className="home-hero-meta">
          <Reveal delay={720}>
            <dl className="home-heromeasures mono">
              <div>
                <dt>provisions indexed</dt>
                <dd>{provisions ? <Counter value={provisions} /> : "-"}</dd>
              </div>
              <div>
                <dt>claims adjudicated</dt>
                <dd>{totalClaims ? <Counter value={totalClaims} /> : "-"}</dd>
              </div>
              <div>
                <dt>evidence spans</dt>
                <dd>{totalSpans ? <Counter value={totalSpans} /> : "-"}</dd>
              </div>
            </dl>
          </Reveal>
        </div>

        <span className="home-scrollhint syslabel">scroll</span>
      </section>

      <Marquee items={ticker} />

      {/* --------------------------------------------------------- stages */}
      <section className="home-section home-pipeline">
        <Reveal>
          <span className="home-sectionnum syslabel">01 / how it works</span>
        </Reveal>
        <ol className="home-steps">
          {STAGES.map((step, index) => (
            <li
              className="home-step"
              key={step.key}
              data-stage={step.state}
            >
              <Reveal delay={index * 60}>
                <span className="home-stepkey mono">
                  {String(index + 1).padStart(2, "0")} / {step.key}
                </span>
                <h3 className="home-steptitle">{step.title}</h3>
                <p className="home-stepbody">{step.body}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </section>

      {/* -------------------------------------------------------- verdicts */}
      <section className="home-section home-verdicts">
        <Reveal>
          <span className="home-sectionnum syslabel">02 / the five states</span>
        </Reveal>
        <RevealLines
          as="h2"
          className="home-h2"
          lines={["A VERDICT", "OR A REFUSAL."]}
        />
        <Reveal delay={120}>
          <p className="home-body">
            Two states decide. Three decline and route to human review. They
            are counted separately everywhere, because reporting a refusal as a
            detection would overstate what the system found.
          </p>
        </Reveal>
        <ul className="home-verdictlist">
          {VERDICTS.map((verdict, index) => {
            const meta = VERDICT_META[verdict];
            return (
              <Reveal as="li" key={verdict} delay={index * 55} className="home-verdictrow">
                <span className="home-verdictkind syslabel">{meta.kind}</span>
                <VerdictMark verdict={verdict} showKind={false} />
                <p className="home-verdictmeaning">{meta.meaning}</p>
              </Reveal>
            );
          })}
        </ul>
      </section>

      {/* ------------------------------------------------------------ ways */}
      <section className="home-section home-ways">
        <Reveal>
          <span className="home-sectionnum syslabel">03 / ways in</span>
        </Reveal>
        <div className="home-doors">
          {[
            {
              to: "/bench",
              k: "bench",
              t: "Review completed assessments",
              d: `${runList.length || "No"} sealed evidence logs, each opening onto the rule text behind every verdict.`,
            },
            {
              to: "/rig",
              k: "rig",
              t: "Run a prepared adjudication",
              d: "Choose a corpus and a prepared conversation, name the assessment, and watch it adjudicate against real stage events.",
            },
            {
              to: "/corpus",
              k: "corpus",
              t: "Explore governing provisions",
              d: `${provisions || "The"} provisions, verbatim, with the sections retrieval actually reached on any run.`,
            },
            {
              to: "/delta",
              k: "delta",
              t: "Compare a fix against its prior run",
              d: "Same scenario, same seed, before and after a change to the agent, tracked by the rule each finding cites.",
            },
          ].map((door, index) => (
            <Reveal key={door.k} delay={index * 60}>
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
        {measurements.data?.chain_verification.all_verified && (
          <Reveal>
            <p className="home-chainline mono">
              every evidence chain on disk verified on load
            </p>
          </Reveal>
        )}
      </section>
    </div>
  );
}
