/** The filed deliverable, in its own deliberately quiet register.
 *
 * The artifact is engine/report.render_html()'s self-contained HTML; this
 * screen serves and frames it, it does not rebuild it. A compliance officer
 * files that document, and nothing about this page should compete with it.
 */

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Loading } from "../components/States";
import "./report.css";

export function Report() {
  const { runId = "" } = useParams();
  const [status, setStatus] = useState<"loading" | "ok" | "missing">("loading");

  useEffect(() => {
    let cancelled = false;
    fetch(api.reportUrl(runId), { method: "GET" }).then(
      (response) => {
        if (!cancelled) setStatus(response.ok ? "ok" : "missing");
      },
      () => {
        if (!cancelled) setStatus("missing");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [runId]);

  return (
    <div className="report-screen">
      <div className="report-bar">
        <nav className="mono">
          <Link to={`/runs/${runId}`}>{runId}</Link>
          <span className="faint"> / deployment readiness report</span>
        </nav>
        {status === "ok" && (
          <a className="mono report-download" href={api.reportUrl(runId)} download={`${runId}-report.html`}>
            download the artifact
          </a>
        )}
      </div>
      <p className="report-note muted">
        This is the filed document itself: one self-contained HTML file with
        no server, no login and no external reference, rendered from the
        evidence log when the run was reported. Audio is embedded so it plays
        from the file. Nothing on this page was recomputed.
      </p>

      {status === "loading" && (
        <div className="page">
          <Loading what={`runs/${runId}/deployment-readiness-report.html`} />
        </div>
      )}
      {status === "missing" && (
        <div className="page">
          <span className="syslabel">no rendered report for this run</span>
          <p className="muted" style={{ marginTop: "0.5rem", maxWidth: "var(--measure)" }}>
            The artifact is built from the evidence log on demand:
          </p>
          <code className="report-cmd mono">
            python scripts/build_report.py --run-id {runId}
          </code>
        </div>
      )}
      {status === "ok" && (
        <iframe
          className="report-frame"
          src={api.reportUrl(runId)}
          title={`Deployment Readiness Report for ${runId}`}
        />
      )}
    </div>
  );
}
