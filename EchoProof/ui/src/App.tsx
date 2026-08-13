import { useEffect } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";

import { Bench } from "./screens/Bench";
import { ClaimCase } from "./screens/ClaimCase";
import { Corpus } from "./screens/Corpus";
import { Delta } from "./screens/Delta";
import { Reading } from "./screens/Reading";
import { Report } from "./screens/Report";
import { Rig } from "./screens/Rig";
import { RunDetail } from "./screens/RunDetail";
import "./app.css";

/** Screens that live on the rig ground. Everything else sits on the bench. */
const RIG_PATHS = [/^\/rig/];

export function App() {
  const location = useLocation();
  const onRig = RIG_PATHS.some((p) => p.test(location.pathname));

  useEffect(() => {
    document.documentElement.setAttribute(
      "data-ground",
      onRig ? "rig" : "bench",
    );
  }, [onRig]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="shell">
      <header className="shell-head">
        <NavLink to="/" className="wordmark">
          EchoProof
        </NavLink>
        <span className="wordmark-sub syslabel">
          compliance assurance, evidence first
        </span>
        <nav className="shell-nav" aria-label="primary">
          <NavLink to="/" end>bench</NavLink>
          <NavLink to="/rig">rig</NavLink>
          <NavLink to="/reading">reading</NavLink>
          <NavLink to="/corpus">corpus</NavLink>
          <NavLink to="/delta">delta</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Bench />} />
          <Route path="/rig" element={<Rig />} />
          <Route path="/reading" element={<Reading />} />
          <Route path="/corpus" element={<Corpus />} />
          <Route path="/corpus/:packId" element={<Corpus />} />
          <Route path="/delta" element={<Delta />} />
          <Route path="/runs/:runId" element={<RunDetail />} />
          <Route path="/runs/:runId/report" element={<Report />} />
          <Route path="/runs/:runId/claims/:claimId" element={<ClaimCase />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="shell-foot">
        <span className="syslabel">
          EchoProof is a triage layer that routes to human review. It is not a
          release gate.
        </span>
      </footer>
    </div>
  );
}

function NotFound() {
  return (
    <div className="page">
      <span className="syslabel">no such screen</span>
      <p className="muted" style={{ marginTop: "0.5rem" }}>
        Nothing lives at this path. The bench is at <code>/</code>.
      </p>
    </div>
  );
}
