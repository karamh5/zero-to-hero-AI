/** The reticle: a bench instrument's cursor, not a decorative blob.
 *
 * A crosshair with a live coordinate readout, because this product's whole
 * argument is that its outputs are locatable. Over an interactive element it
 * opens into a ring and picks up a label taken from the element itself
 * (`data-cursor`), so the pointer says what the thing under it will do.
 *
 * The native cursor is kept, not hidden. Hiding it is the usual move and it
 * costs accessibility for the sake of a trick; the reticle sits alongside it
 * and augments. Disabled entirely for coarse pointers and for anyone who has
 * asked for reduced motion.
 */

import { useEffect, useRef, useState } from "react";
import "./cursor.css";

type Mode = "idle" | "interactive" | "text";

export function Cursor() {
  const ref = useRef<HTMLDivElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);
  const [enabled, setEnabled] = useState(false);
  const [mode, setMode] = useState<Mode>("idle");
  const [label, setLabel] = useState("");
  const [down, setDown] = useState(false);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setEnabled(fine && !still);
  }, []);

  useEffect(() => {
    if (!enabled) return;
    const node = ref.current;
    if (!node) return;

    let x = window.innerWidth / 2;
    let y = window.innerHeight / 2;
    let renderedX = x;
    let renderedY = y;
    let frame = 0;

    const onMove = (event: PointerEvent) => {
      x = event.clientX;
      y = event.clientY;
      const target = event.target as Element | null;
      const interactive = target?.closest(
        "a, button, [role='slider'], summary, select, input, textarea, [tabindex='0']",
      );
      if (interactive) {
        setMode("interactive");
        const own = interactive.getAttribute("data-cursor");
        setLabel(
          own ??
            (interactive.tagName === "A"
              ? "open"
              : interactive.getAttribute("role") === "slider"
                ? "drag"
                : ""),
        );
      } else if (target?.closest("p, blockquote, .law, .transcript-block, td")) {
        setMode("text");
        setLabel("");
      } else {
        setMode("idle");
        setLabel("");
      }
    };

    // The reticle trails by a fixed fraction per frame. Not a spring: a
    // constant approach reads as mechanical, which is the point.
    const loop = () => {
      renderedX += (x - renderedX) * 0.35;
      renderedY += (y - renderedY) * 0.35;
      node.style.transform = `translate3d(${renderedX}px, ${renderedY}px, 0)`;
      if (labelRef.current) {
        labelRef.current.textContent = `${Math.round(x)} ${Math.round(y)}`;
      }
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);

    const onDown = () => setDown(true);
    const onUp = () => setDown(false);
    const onLeave = () => node.classList.add("gone");
    const onEnter = () => node.classList.remove("gone");

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", onDown);
    window.addEventListener("pointerup", onUp);
    document.addEventListener("pointerleave", onLeave);
    document.addEventListener("pointerenter", onEnter);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      document.removeEventListener("pointerleave", onLeave);
      document.removeEventListener("pointerenter", onEnter);
    };
  }, [enabled]);

  if (!enabled) return null;

  return (
    <div
      ref={ref}
      className={`reticle mode-${mode} ${down ? "down" : ""}`}
      aria-hidden="true"
    >
      <span className="reticle-ring" />
      <span className="reticle-hair reticle-hair-h" />
      <span className="reticle-hair reticle-hair-v" />
      <span className="reticle-readout mono">
        <span ref={labelRef} className="reticle-coord" />
        {label && <span className="reticle-label">{label}</span>}
      </span>
    </div>
  );
}
