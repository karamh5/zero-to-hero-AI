/** The reference library as a single living object.
 *
 * Every mark is one real provision from the loaded policy pack, arranged on a
 * cylinder: one column per root section, ordered as the corpus orders them,
 * with depth by obligation type. It rotates slowly and leans toward the
 * pointer, so it reads as an object in a room rather than a looping graphic.
 *
 * This is the landing page's centre, and it is deliberately NOT the sift.
 * The sift reports work in progress and is bound by the rule that nothing
 * moves unless a real pipeline event arrived. This object reports a static
 * fact, the shape and size of the corpus, so idle rotation makes no claim
 * that anything is happening. When the pack cannot be read, it renders
 * nothing and says so rather than inventing a field of marks.
 *
 * Hand-rolled perspective projection on a 2d canvas: no WebGL, no external
 * library, no bundle cost, and it holds frame budget with room to spare.
 */

import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import "./corpusobject.css";

interface Point {
  x: number;
  y: number;
  z: number;
  obligation: string;
  section: string;
  root: string;
}

const DEPTH_BY_OBLIGATION: Record<string, number> = {
  prohibition: 1,
  requirement: 0.62,
  permission: 0.3,
  definition: 0,
};

export function CorpusObject({
  packId = "reg_f",
  onReady,
}: {
  packId?: string;
  onReady?: (info: { count: number; citation: string }) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [points, setPoints] = useState<Point[] | null>(null);
  const [failed, setFailed] = useState(false);
  const pointer = useRef({ x: 0, y: 0 });

  useEffect(() => {
    let cancelled = false;
    api
      .corpus(packId)
      .then((corpus) => {
        if (cancelled) return;
        const separators = corpus.hierarchy_separators;
        const rootOf = (id: string) => {
          let cut = id.length;
          for (const separator of separators) {
            const at = id.indexOf(separator);
            if (at >= 0 && at < cut) cut = at;
          }
          return id.slice(0, cut);
        };
        const roots: string[] = [];
        for (const section of corpus.sections) {
          const root = rootOf(section.section_id);
          if (!roots.includes(root)) roots.push(root);
        }
        const counts = new Map<string, number>();
        const built: Point[] = corpus.sections.map((section) => {
          const root = rootOf(section.section_id);
          const column = roots.indexOf(root);
          const index = counts.get(root) ?? 0;
          counts.set(root, index + 1);
          const angle = (column / roots.length) * Math.PI * 2;
          const radius = 1 + DEPTH_BY_OBLIGATION[section.obligation_type] * 0.22;
          return {
            x: Math.cos(angle) * radius,
            z: Math.sin(angle) * radius,
            y: index * 0.052,
            obligation: section.obligation_type,
            section: section.section_id,
            root,
          };
        });
        // Centre the stack vertically around its own mean height.
        const meanY = built.reduce((sum, p) => sum + p.y, 0) / built.length;
        for (const point of built) point.y -= meanY;
        setPoints(built);
        onReady?.({
          count: corpus.sections.length,
          citation: String(corpus.manifest.citation ?? packId),
        });
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [packId]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !points) return;
    const g = canvas.getContext("2d");
    if (!g) return;
    // Locals the closures below can rely on without re-narrowing.
    const ctx = g;
    const marks = points;

    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let width = 0;
    let height = 0;
    let dpr = 1;

    const styles = getComputedStyle(canvas);
    const read = (name: string, fallback: string) =>
      styles.getPropertyValue(name).trim() || fallback;
    const colorFor = (obligation: string) => {
      if (obligation === "prohibition") return read("--sig-contradicted", "#a83226");
      if (obligation === "requirement") return read("--ink", "#201e19");
      if (obligation === "permission") return read("--sig-supported", "#2f6f5c");
      return read("--ink-faint", "#716b59");
    };
    const colors = new Map(
      [...new Set(marks.map((p) => p.obligation))].map((o) => [o, colorFor(o)]),
    );

    let spin = 0;
    let leanX = 0;
    let leanY = 0;
    let frame = 0;

    const onPointer = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.current = {
        x: (event.clientX - rect.left) / rect.width - 0.5,
        y: (event.clientY - rect.top) / rect.height - 0.5,
      };
    };
    window.addEventListener("pointermove", onPointer, { passive: true });

    const paint = () => {
      ctx.clearRect(0, 0, width, height);
      const scale = Math.min(width, height) * 0.42;
      const cx = width / 2;
      const cy = height / 2;
      const cosS = Math.cos(spin + leanY);
      const sinS = Math.sin(spin + leanY);
      const cosT = Math.cos(leanX);
      const sinT = Math.sin(leanX);

      const projected: { sx: number; sy: number; depth: number; color: string }[] = [];
      for (const point of marks) {
        // yaw
        const x1 = point.x * cosS - point.z * sinS;
        const z1 = point.x * sinS + point.z * cosS;
        // pitch
        const y2 = point.y * cosT - z1 * sinT;
        const z2 = point.y * sinT + z1 * cosT;
        // perspective
        const perspective = 3.4 / (3.4 + z2);
        projected.push({
          sx: cx + x1 * scale * perspective,
          sy: cy + y2 * scale * perspective,
          depth: perspective,
          color: colors.get(point.obligation) ?? "#888",
        });
      }
      // Painter's algorithm: far marks first, so the near face reads solid.
      projected.sort((a, b) => a.depth - b.depth);

      for (const mark of projected) {
        const size = 1.1 + (mark.depth - 0.72) * 5.2;
        ctx.globalAlpha = Math.max(0.16, Math.min(1, (mark.depth - 0.66) * 3.1));
        ctx.fillStyle = mark.color;
        ctx.fillRect(mark.sx - size / 2, mark.sy - size / 2, size, size);
      }
      ctx.globalAlpha = 1;
    };

    const resize = () => {
      dpr = window.devicePixelRatio || 1;
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // Setting width clears the surface, so repaint immediately rather than
      // waiting for the next animation frame. In a document that never
      // composites, an animation frame may never arrive at all, and the
      // object must still be there.
      paint();
    };

    const draw = () => {
      // Slow constant rotation plus a lean toward the pointer. The rotation
      // is the object existing, not the system working: it reports the size
      // and shape of the corpus, which does not change while you watch it.
      if (!still) spin += 0.0016;
      leanX += (pointer.current.y * 0.36 - leanX) * 0.045;
      leanY += (pointer.current.x * 0.5 - leanY) * 0.045;
      paint();
      frame = requestAnimationFrame(draw);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    frame = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("pointermove", onPointer);
    };
  }, [points]);

  if (failed) {
    return (
      <div className="corpusobject-failed">
        <span className="syslabel">policy pack not readable</span>
        <p className="muted">
          Nothing is drawn here rather than a placeholder shape. Build the
          corpus with <code>python scripts/build_policy_pack_ecfr.py</code>.
        </p>
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className="corpusobject"
      role="img"
      aria-label={
        points
          ? `The policy corpus rendered as an object: ${points.length} provisions arranged by section, coloured by whether each one prohibits, requires, permits or defines.`
          : "Loading the policy corpus."
      }
    />
  );
}
