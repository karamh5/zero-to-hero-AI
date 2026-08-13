import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";

import { Cursor } from "./components/Cursor";
import { Bench } from "./screens/Bench";
import { ClaimCase } from "./screens/ClaimCase";
import { Corpus } from "./screens/Corpus";
import { Delta } from "./screens/Delta";
import { Home } from "./screens/Home";
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
  const onHome = location.pathname === "/";

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
    <div className={`shell ${onHome ? "on-home" : ""}`}>
      <Cursor />
      <a className="skiplink" href="#main">
        skip to content
      </a>
      <header className="shell-head">
        <NavLink to="/" className="wordmark" data-cursor="home">
          <span className="wordmark-mark" aria-hidden="true" />
          EchoProof
        </NavLink>
        <nav className="shell-nav" aria-label="primary">
          <NavLink to="/bench" data-cursor="bench">bench</NavLink>
          <NavLink to="/rig" data-cursor="rig">rig</NavLink>
          <NavLink to="/reading" data-cursor="reading">reading</NavLink>
          <NavLink to="/corpus" data-cursor="corpus">corpus</NavLink>
          <NavLink to="/delta" data-cursor="delta">delta</NavLink>
        </nav>
      </header>
      <main id="main" key={location.pathname} className="shell-main">
        <Routes location={location}>
          <Route path="/" element={<Home />} />
          <Route path="/bench" element={<Bench />} />
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
      <Footer />
    </div>
  );
}

function Footer() {
  const [year] = useState(() => new Date().getFullYear());
  return (
    <footer className="shell-foot">
      <span className="shell-footmark">
        EchoProof <span className="shell-footdot">&middot;</span> Pre-deployment
        compliance assurance for voice AI agents
      </span>
      <span className="shell-footmeta syslabel">
        evidence first {year}
      </span>
    </footer>
  );
}

function NotFound() {
  return (
    <div className="page">
      <span className="syslabel">no such screen</span>
      <p className="muted" style={{ marginTop: "0.5rem" }}>
        Nothing lives at this path. The bench is at <code>/bench</code>.
      </p>
    </div>
  );
}
