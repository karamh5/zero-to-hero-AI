/** One cursor, and only one.
 *
 * The native cursor is hidden at the document level and this replaces it
 * entirely, so there is never a system arrow travelling alongside a drawn
 * mark. That is a real commitment: if this component fails to mount, or the
 * pointer is coarse, or the visitor asked for reduced motion, `cursor: none`
 * must not apply. The class that hides the native cursor is therefore added
 * by this component after it decides it is taking over, and removed on
 * teardown.
 *
 * The mark is a single hollow ring, small and precise. It changes shape by
 * context rather than by decoration:
 *
 *   default      a small ring
 *   interactive  the ring opens and takes a label
 *   claim        a precision reticle over an adjudicated span
 *   policy       a section locator over verbatim rule text
 *   audio        a playhead marker over the clip
 *   trace        a concentric mark over the forensic chain
 *
 * Position is written once per animation frame as a transform, never as top
 * and left, and the label follows on the same frame.
 */

import { useEffect, useRef, useState } from "react";
import "./cursor.css";

type Mode = "default" | "interactive" | "claim" | "policy" | "audio" | "trace" | "text";

interface Context {
  mode: Mode;
  label: string;
}

function contextFor(target: Element | null): Context {
  if (!target) return { mode: "default", label: "" };

  const marked = target.closest<HTMLElement>("[data-cursor]");
  const interactive = target.closest<HTMLElement>(
    "a, button, [role='slider'], summary, select, input, textarea, [tabindex='0']",
  );

  // An explicit data-cursor wins, and its value names the mode when it
  // matches one, otherwise it is treated as a label on the interactive mode.
  if (marked) {
    const raw = marked.getAttribute("data-cursor") ?? "";
    const [head, ...rest] = raw.split(":");
    const known: Mode[] = ["claim", "policy", "audio", "trace", "interactive"];
    if ((known as string[]).includes(head)) {
      return { mode: head as Mode, label: rest.join(":") };
    }
    return { mode: interactive ? "interactive" : "default", label: raw };
  }

  if (target.closest(".law, .case-rule, .corpus-text")) {
    return { mode: "policy", label: "" };
  }
  if (interactive) {
    return {
      mode: "interactive",
      label: interactive.tagName === "A" ? "open" : "",
    };
  }
  if (target.closest("p, blockquote, td, li")) {
    return { mode: "text", label: "" };
  }
  return { mode: "default", label: "" };
}

export function Cursor() {
  const markRef = useRef<HTMLDivElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);
  const [active, setActive] = useState(false);
  const [context, setContext] = useState<Context>({ mode: "default", label: "" });
  const [pressed, setPressed] = useState(false);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const taking = fine && !still;
    setActive(taking);
    if (!taking) return;
    // Only now is the native cursor hidden. Doing this in a stylesheet would
    // leave a page with no cursor at all if this component never mounted.
    document.documentElement.classList.add("cursor-hidden");
    return () => document.documentElement.classList.remove("cursor-hidden");
  }, []);

  useEffect(() => {
    if (!active) return;
    const mark = markRef.current;
    if (!mark) return;

    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let x = targetX;
    let y = targetY;
    let labelX = targetX;
    let labelY = targetY;
    let frame = 0;

    const onMove = (event: PointerEvent) => {
      targetX = event.clientX;
      targetY = event.clientY;
      const next = contextFor(event.target as Element | null);
      setContext((previous) =>
        previous.mode === next.mode && previous.label === next.label
          ? previous
          : next,
      );
    };

    const loop = () => {
      // The mark tracks almost exactly; the label trails, which is what makes
      // the pair read as one instrument rather than two dots.
      x += (targetX - x) * 0.5;
      y += (targetY - y) * 0.5;
      labelX += (targetX - labelX) * 0.18;
      labelY += (targetY - labelY) * 0.18;
      mark.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      if (labelRef.current) {
        labelRef.current.style.transform = `translate3d(${labelX + 16}px, ${labelY + 16}px, 0)`;
      }
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);

    const down = () => setPressed(true);
    const up = () => setPressed(false);
    const leave = () => mark.classList.add("away");
    const enter = () => mark.classList.remove("away");

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", down);
    window.addEventListener("pointerup", up);
    document.addEventListener("pointerleave", leave);
    document.addEventListener("pointerenter", enter);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", down);
      window.removeEventListener("pointerup", up);
      document.removeEventListener("pointerleave", leave);
      document.removeEventListener("pointerenter", enter);
    };
  }, [active]);

  if (!active) return null;

  return (
    <>
      <div
        ref={markRef}
        className={`cur cur-${context.mode} ${pressed ? "cur-down" : ""}`}
        aria-hidden="true"
      >
        <span className="cur-ring" />
        <span className="cur-dot" />
      </div>
      <span
        ref={labelRef}
        className={`cur-label ${context.label ? "on" : ""}`}
        aria-hidden="true"
      >
        {context.label}
      </span>
    </>
  );
}
