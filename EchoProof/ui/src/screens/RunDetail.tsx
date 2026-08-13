/** One run opened on the bench: gate, verdicts, campaign, findings, gaps. */

import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Empty, ErrorState, Loading } from "../components/States";
import { VerdictMark } from "../components/VerdictMark";
import { caughtFlags, shortHash } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import type { Campaign, Finding, RunDetail as RunDetailType, Verdict } from "../types";
import { VERDICTS } from "../types";
import "./rundetail.css";

export function RunDetail() {
  const { runId = "" } = useParams();
  const run = useFetch(() => api.run(runId), [runId]);
  const findings = useFetch(
    () => api.findings(runId).catch(() => ({ run_id: runId, findings: [] as Finding[] })),
    [runId],
  );

  if (run.loading) return <div className="page"><Loading what={`runs/${runId}`} /></div>;
  if (run.error) return <div className="page"><ErrorState error={run.error} retry={run.retry} /></div>;
  const detail = run.data;
  if (!detail) return null;

  if (!detail.chain_ok) {
    return (
      <div className="page">
        <RunHeader detail={detail} />
        <div className="run-chainfail" role="alert">
          <span className="syslabel">evidence chain does not verify</span>
          <p>
            Reading this log failed integrity verification, so nothing derived
            from it is shown. A chain that does not verify means the file was
            edited, truncated or corrupted after it was written; that is the
            tamper-evidence working, not a display bug.
          </p>
          <code className="mono">{detail.chain_error}</code>
        </div>
      </div>
    );
  }

  const list = findings.data?.findings ?? [];
  const violations = list.filter((f) => f.verdict === "contradicted");
  const supported = list.filter((f) => f.verdict === "supported");
  const abstentions = list.filter((f) => f.is_abstention);

  return (
    <div className="page">
      <RunHeader detail={detail} />

      {detail.gate && (
        <section className={`run-gate run-gate-${detail.gate.kind}`}>
          <span className="syslabel">gate decision, computed from the client's criteria pack</span>
          <strong className="run-gate-label">{detail.gate.label}</strong>
          <p className="muted">{detail.gate.reason}</p>
          <p className="run-gate-triage">
            A gate decision is a client-defined threshold computation over the
            findings below. EchoProof is a triage layer that routes to human
            review; this is not a certification.
          </p>
        </section>
      )}

      <section className="run-verdicts">
        <h2 className="syslabel">verdicts</h2>
        <table className="plain run-verdict-table">
          <thead>
            <tr>
              <th>verdict</th>
              <th>kind</th>
              <th>count</th>
            </tr>
          </thead>
          <tbody>
            {VERDICTS.filter((v) => (detail.verdict_counts[v] ?? 0) > 0).map((verdict) => (
              <tr key={verdict}>
                <td><VerdictMark verdict={verdict as Verdict} showKind={false} /></td>
                <td className="mono muted">
                  {verdict === "supported" || verdict === "contradicted"
                    ? "decision"
                    : "abstention"}
                </td>
                <td className="num">{detail.verdict_counts[verdict]}</td>
              </tr>
            ))}
            {(detail.deterministic_decisions ?? 0) > 0 && (
              <tr>
                <td className="mono" style={{ color: "var(--sig-deterministic)" }}>
                  decided in code
                </td>
                <td className="mono muted">deterministic</td>
                <td className="num">{detail.deterministic_decisions}</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {detail.campaign && <CampaignSection campaign={detail.campaign} />}

      <FindingsSection
        title="findings"
        note="Verdicts of contradicted: the agent said something the retrieved rule forbids."
        items={violations}
        runId={runId}
        emptyLabel="no violations in this run"
      />
      <FindingsSection
        title="supported claims"
        note="The retrieved rule supports what the agent said."
        items={supported}
        runId={runId}
        emptyLabel="no supported claims recorded"
      />
      <FindingsSection
        title="abstentions"
        note="Refusals to decide, counted separately from findings and routed to human review or the policy gap list, never totalled into detection."
        items={abstentions}
        runId={runId}
        emptyLabel="no abstentions"
      />

      <section className="run-gaps">
        <h2 className="syslabel">policy gap list</h2>
        {detail.policy_gap_claims.length === 0 ? (
          <p className="muted run-gaps-empty">
            Empty. Only a claim where nothing in the corpus cleared the
            retrieval floor lands here; a judge rejecting the sections it was
            shown is a retrieval failure and routes to human review instead.
          </p>
        ) : (
          <>
            <p className="muted">
              Claims where no section in the corpus cleared the retrieval
              floor. Candidates for a rulebook gap, not violations.
            </p>
            <ul className="run-gaplist">
              {detail.policy_gap_claims.map((f) => (
                <li key={f.claim_id}>
                  <Link to={`/runs/${runId}/claims/${f.claim_id}`} className="mono">
                    {f.claim_id}
                  </Link>{" "}
                  <span className="muted">{f.claim_text.slice(0, 140)}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      {detail.rerun && (
        <p className="run-crosslink">
          This run carries a fix-and-rerun delta.{" "}
          <Link to="/delta">Read it on the delta screen.</Link>
        </p>
      )}

      <section className="run-integrity">
        <h2 className="syslabel">integrity</h2>
        <dl className="run-integrity-grid mono">
          <div>
            <dt>chain head</dt>
            <dd title={detail.chain_head ?? ""}>{shortHash(detail.chain_head, 24)}</dd>
          </div>
          <div>
            <dt>seal</dt>
            <dd className={detail.seal_state === "broken" ? "run-sealbroken" : ""}>
              {detail.seal_state}
            </dd>
          </div>
          <div>
            <dt>agent version</dt>
            <dd>{detail.agent_version}</dd>
          </div>
          <div>
            <dt>spans</dt>
            <dd>{detail.span_count}</dd>
          </div>
        </dl>
        {detail.artifacts.report && (
          <p className="run-reportlink">
            <Link to={`/runs/${runId}/report`}>
              Open the filed Deployment Readiness Report
            </Link>
          </p>
        )}
      </section>
    </div>
  );
}

function RunHeader({ detail }: { detail: RunDetailType }) {
  return (
    <header className="run-head">
      <nav className="mono run-crumb">
        <Link to="/bench">bench</Link>
        <span className="faint"> / </span>
      </nav>
      <h1 className="run-title mono">{detail.run_id}</h1>
      <div className="run-headmeta">
        {detail.pack_id && (
          <span className="mono muted">corpus {detail.pack_id}</span>
        )}
        <span className="mono muted">
          {detail.turns} turn(s) · {detail.claims} claim(s) adjudicated
        </span>
        {detail.clip_count > 0 ? (
          <span className="mono muted">{detail.clip_count} audio clips</span>
        ) : (
          <span className="syslabel">no audio, text only run</span>
        )}
      </div>
    </header>
  );
}

function CampaignSection({ campaign }: { campaign: Campaign }) {
  const graded = campaign.scenarios.filter((s) => !s.is_control);
  const passAt3 = graded.filter((s) => s.pass_at_3).length;
  const passCubed = graded.filter((s) => s.pass_cubed).length;
  const controls = campaign.scenarios.filter((s) => s.is_control);

  return (
    <section className="run-campaign">
      <h2 className="syslabel">campaign</h2>
      <p className="muted run-campaign-lede">
        {campaign.scenarios.length} scenarios, {campaign.runs_per_scenario} runs
        each, {campaign.turns_per_call} turns per call. The caught column reads
        left to right by run; a mixed row is instability and is shown as such,
        never averaged into a percentage.
      </p>
      <table className="plain run-campaign-table">
        <thead>
          <tr>
            <th>scenario</th>
            <th>expected section</th>
            <th>caught</th>
            <th>pass@3</th>
            <th>pass^3</th>
            <th>drifted</th>
          </tr>
        </thead>
        <tbody>
          {campaign.scenarios.map((s) => (
            <tr key={s.scenario_id} className={s.is_control ? "control" : ""}>
              <td className="mono">
                {s.scenario_id}
                {s.is_control && <span className="syslabel run-controltag"> control</span>}
              </td>
              <td className="mono">{s.expected_section_id ?? "-"}</td>
              <td className="mono run-flags">
                {s.is_control ? `${s.false_positive_calls} false positive call(s)` : caughtFlags(s.caught)}
              </td>
              <td className="mono">{s.is_control ? "-" : s.pass_at_3 ? "yes" : "no"}</td>
              <td className="mono">{s.is_control ? "-" : s.pass_cubed ? "yes" : "no"}</td>
              <td className="num">{s.drifted}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="run-campaign-tally mono">
        pass@3 {passAt3}/{graded.length} · pass^3 {passCubed}/{graded.length}
      </p>
      {controls.length > 0 && (
        <p className="run-campaign-control">
          The control scenario produced{" "}
          <strong>
            {controls.reduce((n, s) => n + s.false_positive_calls, 0)} false
            positives across {campaign.runs_per_scenario * controls.length} compliant calls
          </strong>
          . Staying quiet on a compliant call is one of this system's genuinely
          strong results.
        </p>
      )}
    </section>
  );
}

function FindingsSection({
  title,
  note,
  items,
  runId,
  emptyLabel,
}: {
  title: string;
  note: string;
  items: Finding[];
  runId: string;
  emptyLabel: string;
}) {
  return (
    <section className="run-findings">
      <h2 className="syslabel">
        {title} <span className="run-count mono">{items.length}</span>
      </h2>
      <p className="muted run-findings-note">{note}</p>
      {items.length === 0 ? (
        <Empty label={emptyLabel} />
      ) : (
        <ol className="run-findinglist">
          {items.map((f) => (
            <li key={f.claim_id}>
              <Link to={`/runs/${runId}/claims/${f.claim_id}`} className="run-findingrow rowlink">
                <div className="run-findingtop">
                  <VerdictMark verdict={f.verdict} showKind={false} />
                  <span className="mono">{f.section_id ?? "no section"}</span>
                  <span className="syslabel">sev {f.severity}</span>
                  {f.has_clip && <span className="syslabel">audio</span>}
                  <span className="mono faint">{f.claim_id}</span>
                </div>
                <p className="run-findingquote">
                  {(f.transcript ?? "").slice(f.char_start, f.char_end) || f.claim_text}
                </p>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
