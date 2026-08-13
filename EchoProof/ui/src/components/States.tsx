/** The designed non-happy states. None of them is an alert() or a blank.
 *
 * Loading deliberately has no spinner and no skeleton pulse: a quiet mono
 * line that says what is being read. Stillness is information.
 */

import type { ApiError } from "../api";
import "./states.css";

export function Loading({ what }: { what: string }) {
  return (
    <div className="state-block" role="status">
      <span className="syslabel">reading</span>
      <span className="mono muted">{what}</span>
    </div>
  );
}

export function ErrorState({
  error,
  retry,
}: {
  error: ApiError;
  retry?: () => void;
}) {
  const disconnected = error.disconnected;
  return (
    <div className="state-block" role="alert">
      <span className="syslabel">
        {disconnected ? "backend not reachable" : `error ${error.status || ""}`}
      </span>
      <p className="state-message">
        {disconnected
          ? "The API server is not running. Start it with:"
          : error.message}
      </p>
      {disconnected && (
        <code className="state-command">python scripts/run_ui.py</code>
      )}
      {retry && (
        <button className="state-retry mono" onClick={retry}>
          retry
        </button>
      )}
    </div>
  );
}

export function Empty({ label, detail }: { label: string; detail?: string }) {
  return (
    <div className="state-block">
      <span className="syslabel">{label}</span>
      {detail && <p className="state-message muted">{detail}</p>}
    </div>
  );
}
