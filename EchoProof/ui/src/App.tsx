import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";

import { Cursor } from "./components/Cursor";
import { Bench } from "./screens/Bench";
import { ClaimCase } from "./screens/ClaimCase";
import { Corpus } from "./screens/Corpus";
import { Delta } from "./screens/Delta";
import { Home } from "./screens/Home";
import { Report } from "./screens/Report";
import { Rig } from "./screens/Rig";
import { RunDetail } from "./screens/RunDetail";
import "./app.css";

/** Screens that live on the rig ground. Everything else sits on the bench. */
const RIG_PATHS = [/^\/rig/];

const NAV = [
  { to: "/bench", label: "BENCH" },
  { to: "/rig", label: "RIG" },
  { to: "/corpus", label: "CORPUS" },
  { to: "/delta", label: "DELTA" },
];

/** A technical label resolving into place, not a hacker effect.
 *
 * Two intermediate frames over about 200ms when the label first mounts or is
 * hovered. The accessible text is always the final string: the scrambling
 * happens in a span marked aria-hidden with the real word held alongside it. */
function ScrambleLabel({ text }: { text: string }) {
  const [shown, setShown] = useState(text);
  const timers = useRef<number[]>([]);

  const run = useCallback(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    timers.current.forEach(window.clearTimeout);
    timers.current = [];
    const pool = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789";
    const scramble = (keep: number) =>
      text
        .split("")
        .map((character, index) =>
          index < keep ? character : pool[Math.floor(Math.random() * pool.length)],
        )
        .join("");
    timers.current.push(window.setTimeout(() => setShown(scramble(0)), 0));
    timers.current.push(
      window.setTimeout(() => setShown(scramble(Math.ceil(text.length / 2))), 90),
    );
    timers.current.push(window.setTimeout(() => setShown(text), 200));
  }, [text]);

  useEffect(() => {
    run();
    return () => timers.current.forEach(window.clearTimeout);
  }, [run]);

  // aria-hidden throughout: the enclosing link supplies the accessible name,
  // so mid-scramble letters are never announced.
  return (
    <span className="shell-navlabel" onPointerEnter={run} aria-hidden="true">
      {shown}
    </span>
  );
}

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
          {NAV.map((item, index) => (
            <NavLink
              key={item.to}
              to={item.to}
              data-cursor={item.label.toLowerCase()}
              // The link carries the name; everything inside is decoration,
              // so the index and the resolving letters are not announced.
              aria-label={item.label}
            >
              <span className="shell-navnum" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <ScrambleLabel text={item.label} />
            </NavLink>
          ))}
        </nav>
      </header>
      <main id="main" key={location.pathname} className="shell-main">
        <Routes location={location}>
          <Route path="/" element={<Home />} />
          <Route path="/bench" element={<Bench />} />
          <Route path="/rig" element={<Rig />} />
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
  return (
    <footer className="shell-foot">
      <span className="shell-footmark">
        EchoProof <span className="shell-footdot">&middot;</span> Pre-deployment
        compliance assurance for voice AI agents
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
