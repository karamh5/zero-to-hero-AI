/** The reading: what the instrument measures about itself, with uncertainty.
 *
 * Not a certification screen. The triage statement is unavoidable, detection
 * is a range because the measurement is a range, and judge-human agreement is
 * shown failing its floor because it fails its floor. Every figure names the
 * file it was read from.
 */

import { Link } from "react-router-dom";
import { api } from "../api";
import { FloorBand, RangeBand } from "../components/Band";
import { ErrorState, Loading } from "../components/States";
import { useFetch } from "../lib/useFetch";
import { seconds1 } from "../lib/format";
import "./reading.css";

export function Reading() {
  const measurements = useFetch(() => api.measurements(), []);
  const campaignRun = useFetch(
    () => api.run("campaign").catch(() => null),
    [],
  );

  if (measurements.loading)
    return <div className="page"><Loading what="measurement artifacts" /></div>;
  if (measurements.error)
    return <div className="page"><ErrorState error={measurements.error} retry={measurements.retry} /></div>;
  const data = measurements.data;
  if (!data) return null;

  const detection = data.detection;
  const agreement = data.agreement.data;
  const latency = data.latency.data;
  const campaign = data.campaign.summary;
  const gate = campaignRun.data?.gate ?? null;

  return (
    <div className="page reading">
      <header className="reading-head">
        <h1 className="reading-display">The reading</h1>
      </header>

      <section className="reading-triage">
        <p className="reading-triage-statement">
          EchoProof is a triage layer that routes to human review.
          <br />
          It is not a release gate.
        </p>
        <p className="reading-triage-why muted">
          {agreement
            ? `Judge-human agreement is ${agreement.raw_agreement.toFixed(3)} against a ${agreement.floor.toFixed(2)} floor, and three independent measurements point the same way. That positioning is what the specification prescribes when the floor fails; it is printed on the filed report's face and it is printed here.`
            : "The agreement baseline artifact is absent, so the floor comparison cannot be shown. The triage positioning stands on the remaining measurements."}
        </p>
      </section>

      {gate && (
        <section className={`reading-gate reading-gate-${gate.kind}`}>
          <span className="syslabel">
            gate decision on the recorded campaign, computed now from the
            client's own thresholds: never stored
          </span>
          <strong className="reading-gate-label">{gate.label}</strong>
          <p className="muted">{gate.reason}</p>
          <p className="muted reading-gate-link">
            <Link to="/runs/campaign">Open the campaign run this was computed from.</Link>
          </p>
        </section>
      )}

      <section className="reading-bands">
        {detection.low !== null && detection.high !== null ? (
          <RangeBand
            name="claim detection at 2 percent false positives"
            low={detection.low}
            high={detection.high}
            ticks={detection.runs
              .filter((run) => run.detection !== null)
              .map((run) => ({ value: run.detection!, label: run.run_id }))}
            caption={detection.note}
            source={`computed from ${detection.runs.map((r) => r.source).join(" and ")} at the recorded operating ceiling ${detection.ceiling}`}
          />
        ) : (
          <p className="muted">
            Detection range unavailable: {detection.note}
          </p>
        )}

        {detection.citation_low !== null && detection.citation_high !== null && (
          <RangeBand
            name="citation precision at that operating point"
            low={detection.citation_low}
            high={detection.citation_high}
            ticks={detection.runs
              .filter((run) => run.citation_precision !== null)
              .map((run) => ({ value: run.citation_precision!, label: run.run_id }))}
            caption="Of the violations detected, the share citing the correct governing paragraph. Three or four findings in five land on the right rule; roughly one in four or five lands on an adjacent paragraph, and the trace is what makes that checkable."
            source={`computed from ${detection.runs.map((r) => r.source).join(" and ")}`}
          />
        )}

        {agreement && (
          <FloorBand
            name="judge to human agreement"
            value={agreement.raw_agreement}
            floor={agreement.floor}
            meets={agreement.meets_floor}
            caption={`${agreement.matched} of ${agreement.total} blind-labelled items agreed; Cohen's kappa ${agreement.cohens_kappa.toFixed(3)} against the skewed verdict distribution. ${data.agreement.self_graded_note}`}
            source={data.agreement.source}
          />
        )}
      </section>

      <section className="reading-panel">
        <h2 className="syslabel">the rest of the panel</h2>
        <dl className="reading-facts">
          {campaign && (
            <>
              <Fact
                label="campaign pass@3"
                value={`${campaign.pass_at_3} of ${campaign.graded_scenarios}`}
                note={`pass^3 ${campaign.pass_cubed} of ${campaign.graded_scenarios}. pass@3 counts a violation caught at least once in three runs; pass^3 requires every run. They are never merged.`}
                source={data.campaign.source}
              />
              <Fact
                label="control false positives"
                value={`${campaign.control_false_positive_calls} in ${campaign.control_calls} compliant calls`}
                note="The compliant control produced no false positive in any recorded run. Staying quiet on a clean call is one of the genuinely strong results."
                source={data.campaign.source}
                strong
              />
              {campaign.cost_usd !== null && (
                <Fact
                  label="measured campaign cost"
                  value={`$${campaign.cost_usd?.toFixed(2)} for ${campaign.calls} calls`}
                  note={`${campaign.turns_per_call} turns per call, ${campaign.wall_clock_min?.toFixed(0)} minutes wall clock. Retrieval cache hit rate ${campaign.cache ? (campaign.cache.hit_rate * 100).toFixed(1) : "-"} percent, because agent replies diverge between runs.`}
                  source={data.campaign.source}
                />
              )}
            </>
          )}
          {latency && (
            <Fact
              label="adjudication latency"
              value={`${seconds1(latency.median_total)} median, ${seconds1(latency.worst_total)} worst`}
              note="Per turn, dominated by retrieval reranking on CPU. The rig is built around this number rather than hiding it."
              source={data.latency.source}
            />
          )}
          {data.proxy_overhead.documented_median_ms !== null && (
            <Fact
              label="proxy overhead on a live call"
              value={`${data.proxy_overhead.documented_median_ms} ms median`}
              note={data.proxy_overhead.note}
              source={data.proxy_overhead.source}
            />
          )}
          <Fact
            label="evidence chains"
            value={
              data.chain_verification.all_verified
                ? `all ${Object.keys(data.chain_verification.runs).length} runs verify`
                : "VERIFICATION FAILURE on disk"
            }
            note={
              data.chain_verification.all_verified
                ? "Every evidence log on disk re-verifies its hash chain on read."
                : `Failing: ${Object.entries(data.chain_verification.runs)
                    .filter(([, ok]) => !ok)
                    .map(([id]) => id)
                    .join(", ")}. A failing chain means the file changed after it was written.`
            }
            source="recomputed from runs/*/evidence.jsonl just now"
            alert={!data.chain_verification.all_verified}
          />
        </dl>
      </section>

      <section className="reading-honesty">
        <h2 className="syslabel">what these numbers cannot say</h2>
        <p className="muted">
          Ground truth was single-authored, the human baseline was self-graded
          at the project owner's direction, and five scenarios separate 1/5
          from 2/5 by a single result. The full accounting lives in{" "}
          <code>LIMITATIONS.md</code>, which is the honest half of the result,
          not a footnote.
        </p>
      </section>
    </div>
  );
}

function Fact({
  label,
  value,
  note,
  source,
  strong = false,
  alert = false,
}: {
  label: string;
  value: string;
  note: string;
  source: string;
  strong?: boolean;
  alert?: boolean;
}) {
  return (
    <div className={`reading-fact ${strong ? "strong" : ""} ${alert ? "alert" : ""}`}>
      <dt className="syslabel">{label}</dt>
      <dd>
        <span className="reading-fact-value mono">{value}</span>
        <p className="reading-fact-note muted">{note}</p>
        <p className="reading-fact-source mono">{source}</p>
      </dd>
    </div>
  );
}
