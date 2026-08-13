/** The bench: every run on disk, presented as objects with weight, not rows.
 *
 * Runs differ in nature (a campaign, an audio demo, a scored split, a pack
 * swap, a deliberate failure drill) and the entry says which, derived from
 * the artifacts each run actually carries. Nothing here is hardcoded to the
 * runs that exist today; a new rig run lands on the bench by being written
 * to disk.
 */

import { Link } from "react-router-dom";
import { api } from "../api";
import { Reveal, RevealLines } from "../components/Reveal";
import { Empty, ErrorState, Loading } from "../components/States";
import { useFetch } from "../lib/useFetch";
import type { RunSummary } from "../types";
import "./bench.css";

function natureOf(run: RunSummary): string {
  const parts: string[] = [];
  if (run.artifacts.campaign) parts.push("campaign");
  if (run.artifacts.scored) parts.push("scored split");
  if (run.artifacts.rerun) parts.push("fix and re-run");
  if (run.artifacts.swap) parts.push("pack swap");
  if (run.clip_count > 0) parts.push(`${run.clip_count} audio clips`);
  if (run.run_id.startsWith("rig-")) parts.push("live rig turn");
  if (run.run_id.includes("failure") || run.run_id.includes("drill"))
    parts.push("failure drill");
  if (parts.length === 0) parts.push("evidence log");
  return parts.join(" · ");
}

export function Bench() {
  const { data, error, loading, retry } = useFetch(() => api.runs(), []);

  if (loading) return <div className="page"><Loading what="runs/ on disk" /></div>;
  if (error) return <div className="page"><ErrorState error={error} retry={retry} /></div>;

  const runs = data?.runs ?? [];
  if (runs.length === 0) {
    return (
      <div className="page">
        <BenchIntro />
        <Empty
          label="no runs on disk"
          detail="runs/ is empty. Adjudicate a turn on the rig, or run a campaign with scripts/run_campaign.py, and its evidence log will appear here."
        />
      </div>
    );
  }

  // Substantial runs first: campaigns and clip-bearing runs are what a
  // visitor should pick up first, then everything else by name.
  const weight = (run: RunSummary) =>
    (run.artifacts.campaign ? 4 : 0) +
    (run.clip_count > 0 ? 2 : 0) +
    (run.artifacts.scored ? 2 : 0) +
    (run.artifacts.rerun || run.artifacts.swap ? 1 : 0);
  const ordered = [...runs].sort(
    (a, b) => weight(b) - weight(a) || a.run_id.localeCompare(b.run_id),
  );

  return (
    <div className="page">
      <BenchIntro />
      <ol className="bench-list">
        {ordered.map((run, index) => (
          <Reveal as="li" key={run.run_id} delay={Math.min(index, 6) * 55}>
            <Link
              to={`/runs/${run.run_id}`}
              className="bench-entry rowlink"
              aria-label={`run ${run.run_id}`}
              data-cursor="open run"
            >
              <div className="bench-title-row">
                <span className="bench-runid">{run.run_id}</span>
                <span className="bench-nature syslabel">{natureOf(run)}</span>
              </div>
              <div className="bench-meta">
                <ChainState run={run} />
                {run.pack_id && (
                  <span className="mono muted">corpus {run.pack_id}</span>
                )}
                <span className="mono muted">{run.span_count} spans</span>
              </div>
              {run.chain_ok && (
                <dl className="bench-counts">
                  <div>
                    <dt className="syslabel">turns</dt>
                    <dd className="mono">{run.turns}</dd>
                  </div>
                  <div>
                    <dt className="syslabel">claims</dt>
                    <dd className="mono">{run.claims}</dd>
                  </div>
                  <div>
                    <dt className="syslabel">violations</dt>
                    <dd className="mono" data-nonzero={run.violations > 0}>
                      {run.violations}
                    </dd>
                  </div>
                  <div>
                    <dt className="syslabel">abstentions</dt>
                    <dd className="mono">{run.abstentions}</dd>
                  </div>
                  <div>
                    <dt className="syslabel">supported</dt>
                    <dd className="mono">{run.supported}</dd>
                  </div>
                </dl>
              )}
            </Link>
          </Reveal>
        ))}
      </ol>
      <p className="bench-footnote muted">
        Violations and abstentions are separate counts everywhere on this
        bench. An abstention is a refusal to decide; adding it to a findings
        count would overstate what the system detected.
      </p>
    </div>
  );
}

function BenchIntro() {
  return (
    <header className="bench-head">
      <RevealLines as="h1" className="bench-display" lines={["The", "bench"]} />
      <Reveal delay={260}>
        <p className="bench-lede">
          Every adjudication run on disk, each an append-only, hash-chained
          evidence log. Open one to read its findings against the rule text
          they rest on.
        </p>
      </Reveal>
    </header>
  );
}

function ChainState({ run }: { run: RunSummary }) {
  if (!run.chain_ok) {
    return (
      <span className="bench-chainfail mono" role="alert">
        chain verification FAILED
      </span>
    );
  }
  return (
    <span className="mono muted">
      chain verified
      {run.seal_state === "intact" && " · seal intact"}
      {run.seal_state === "broken" && (
        <span className="bench-sealbroken"> · SEAL BROKEN</span>
      )}
    </span>
  );
}
