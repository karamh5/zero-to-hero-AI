/** The boot screen.
 *
 * A voice is a waveform until something reads it. That is the whole idea of
 * this product, so the boot sequence draws a spoken waveform and then
 * resolves it into the structure EchoProof turns it into: discrete claim
 * marks on a line. Speech in, structure out, in about a second and a half.
 *
 * It is short on purpose. A loading screen that outlasts the thing it is
 * loading is a tax on every visit, so this holds only until the fonts are
 * ready and the first data call has answered, with a hard ceiling either way.
 *
 * The waveform is generated from a fixed seed rather than from a microphone.
 * There is no live audio anywhere in this product and there is none here.
 */

import { useEffect, useRef, useState } from "react";
import "./boot.css";

const HOLD_MIN_MS = 900;
const HOLD_MAX_MS = 2600;

export function Boot({ onDone }: { onDone: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const started = performance.now();
    let done = false;

    const finish = () => {
      if (done) return;
      done = true;
      const waited = performance.now() - started;
      const remaining = Math.max(0, HOLD_MIN_MS - waited);
      window.setTimeout(() => {
        setLeaving(true);
        window.setTimeout(onDone, 520);
      }, remaining);
    };

    // Ready when the fonts have loaded and the API has answered once, so the
    // first painted screen is the real one rather than a reflow.
    const ready = Promise.allSettled([
      document.fonts?.ready ?? Promise.resolve(),
      fetch("/api/runs").catch(() => null),
    ]);
    void ready.then(finish);
    const ceiling = window.setTimeout(finish, HOLD_MAX_MS);
    return () => window.clearTimeout(ceiling);
  }, [onDone]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const g = canvas.getContext("2d");
    if (!g) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let width = 0;
    let height = 0;
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    // A fixed pseudo-waveform: same shape on every visit, so the boot is a
    // signature rather than a random squiggle.
    const BARS = 96;
    let seed = 8675309;
    const rand = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };
    const amps = Array.from({ length: BARS }, (_, i) => {
      const envelope = Math.sin((i / BARS) * Math.PI);
      const speech = 0.35 + rand() * 0.65;
      const burst = i % 11 < 4 ? 1 : 0.55;
      return Math.max(0.06, envelope * speech * burst);
    });
    // Where the claims land once the waveform resolves.
    const claims = [11, 28, 46, 63, 81];

    const styles = getComputedStyle(canvas);
    const read = (n: string, f: string) =>
      styles.getPropertyValue(n).trim() || f;
    const ink = read("--ink", "#e9e7e1");
    const faint = read("--line-strong", "#363c46");
    const trace = read("--sig-trace", "#45c8da");

    const start = performance.now();
    let frame = 0;

    const draw = () => {
      const t = still ? 1 : Math.min(1, (performance.now() - start) / 1700);
      // Two phases: the waveform speaks, then it collapses to structure.
      const speak = Math.min(1, t / 0.55);
      const resolve = Math.max(0, (t - 0.5) / 0.5);
      const ease = 1 - Math.pow(1 - resolve, 3);

      g.clearRect(0, 0, width, height);
      const mid = height / 2;
      const barW = width / BARS;

      for (let i = 0; i < BARS; i += 1) {
        const appear = Math.min(1, Math.max(0, speak * BARS - i) / 6);
        if (appear <= 0) continue;
        const isClaim = claims.includes(i);
        // Everything that is not a claim shrinks to the baseline; claims
        // stand up as marks. Speech becomes structure.
        const full = amps[i] * (height * 0.34) * appear;
        const settled = isClaim ? height * 0.13 : 1.2;
        const h = full + (settled - full) * ease;
        g.fillStyle = isClaim && ease > 0.25 ? trace : ease > 0.6 ? faint : ink;
        g.globalAlpha = isClaim ? 1 : 1 - ease * 0.55;
        g.fillRect(i * barW, mid - h / 2, Math.max(1, barW - 1.6), h);
      }
      g.globalAlpha = 1;

      // The baseline the structure sits on, drawn in as it resolves.
      if (ease > 0) {
        g.fillStyle = faint;
        g.fillRect(0, mid - 0.5, width * ease, 1);
      }

      if (t < 1) frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    draw();

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <div className={`boot ${leaving ? "leaving" : ""}`} role="status" aria-live="polite">
      <div className="boot-inner">
        <canvas ref={canvasRef} className="boot-wave" aria-hidden="true" />
        <div className="boot-caption">
          <span className="boot-mark">ECHOPROOF</span>
          <span className="boot-line mono">speech in, structure out</span>
        </div>
      </div>
      <span className="visually-hidden">Loading EchoProof</span>
    </div>
  );
}
