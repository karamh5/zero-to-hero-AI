/** Fix and re-run: did the compliance issue actually go away?
 *
 * Findings are tracked across runs BY THE RULE THEY CITE, never by claim id
 * (claim ids are positional and a fix changes what the agent says). The
 * classification comes from engine/rerun.py via the stored rerun.json;
 * nothing here recomputes closed, persisted, new or improved.
 */

import { Link } from "react-router-dom";
import { api } from "../api";
import { Empty, ErrorState, Loading } from "../components/States";
import { useFetch } from "../lib/useFetch";
import type { RerunDelta } from "../types";
import "./delta.css";

export function Delta() {
  const runs = useFetch(() => api.runs(), []);

  if (runs.loading) return <div className="page"><Loading what="runs with a rerun delta" /></div>;
  if (runs.error) return <div className="page"><ErrorState error={runs.error} retry={runs.retry} /></div>;

  const withRerun = (runs.data?.runs ?? []).filter((run) => run.artifacts.rerun);

  return (
    <div className="page delta">
      <header className="delta-head">
        <h1 className="delta-display">The delta</h1>
        <p className="delta-lede">
          The same scenario, the same seed, run before and after a change to
          the agent. Only the agent changed: same persona, same judge, same
          thresholds, same policy pack. The question a client is asking is
          "is that compliance issue gone", and an issue is identified by the
          rule it breaches.
        </p>
      </header>

      {withRerun.length === 0 ? (
        <Empty
          label="no rerun delta on disk"
          detail="Produce one with: python scripts/fix_and_rerun.py"
        />
      ) : (
        withRerun.map((run) => <DeltaBlock key={run.run_id} runId={run.run_id} />)
      )}
    </div>
  );
}

function DeltaBlock({ runId }: { runId: string }) {
  const rerun = useFetch<RerunDelta>(() => api.rerun(runId), [runId]);
  if (rerun.loading) return <Loading what={`runs/${runId}/rerun.json`} />;
  if (rerun.error) return <ErrorState error={rerun.error} retry={rerun.retry} />;
  const delta = rerun.data;
  if (!delta) return null;

  return (
    <section className="delta-block">
      <div className="delta-meta">
        <span className="mono">
          scenario {delta.scenario_id} · seed {delta.seed} · run{" "}
          <Link to={`/runs/${runId}`}>{runId}</Link>
        </span>
      </div>

      <div className={`delta-verdict ${delta.improved ? "improved" : "incomplete"}`}>
        <strong>{delta.improved ? "Fix verified" : "Fix incomplete"}</strong>
        <span className="muted">
          {delta.improved
            ? ": the finding closed and nothing new appeared. Both conditions are required: a change that closes one issue while introducing another has not fixed the agent."
            : ": something persisted or something new appeared. See below."}
        </span>
      </div>

      <div className="delta-keys">
        <KeyList label="closed" items={delta.closed} kind="closed" />
        <KeyList label="persisted" items={delta.persisted} kind="persisted" />
        <KeyList label="new" items={delta.new} kind="new" />
      </div>

      <div className="delta-columns">
        <div>
          <h2 className="syslabel">
            before · {delta.before_count} finding(s)
          </h2>
          <ul className="delta-turns">
            {(delta.before_agent_turns ?? []).map((turn, index) => (
              <li key={index}>{turn}</li>
            ))}
          </ul>
          {(delta.before_findings ?? []).map((finding) => (
            <p key={finding.claim_id} className="delta-finding">
              <span className="mono">{finding.section_id}</span>{" "}
              <span className="muted">{finding.rationale.slice(0, 220)}…</span>
            </p>
          ))}
        </div>
        <div>
          <h2 className="syslabel">
            after · {delta.after_count} finding(s)
          </h2>
          <ul className="delta-turns">
            {(delta.after_agent_turns ?? []).map((turn, index) => (
              <li key={index}>{turn}</li>
            ))}
          </ul>
          {delta.after_count === 0 && (
            <p className="muted delta-clean">
              No finding in the re-run. The counts alone prove little; the
              turns above are what make the delta mean something: the agent
              stopped pressing for payment and closed the call.
            </p>
          )}
        </div>
      </div>

      <p className="delta-keynote muted">
        Tracked by (section_id, verdict), never by claim id. Keying on claim
        ids would report every issue as closed and new at once, which looks
        like a perfect fix and is worse than useless.
      </p>
    </section>
  );
}

function KeyList({
  label,
  items,
  kind,
}: {
  label: string;
  items: { section_id: string; verdict: string }[];
  kind: "closed" | "persisted" | "new";
}) {
  return (
    <div className={`delta-keygroup ${kind}`}>
      <span className="syslabel">{label}</span>
      {items.length === 0 ? (
        <span className="mono faint">none</span>
      ) : (
        items.map((item) => (
          <span key={item.section_id + item.verdict} className="mono delta-key">
            {item.section_id}
          </span>
        ))
      )}
    </div>
  );
}
