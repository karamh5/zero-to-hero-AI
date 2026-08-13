/** Scroll-triggered reveals.
 *
 * Two kinds. `Reveal` slides and fades a block once it enters the viewport.
 * `RevealLines` wipes a heading in line by line with a clip-path, which is
 * the move that makes oversized display type land as composition rather than
 * as a large word sitting there.
 *
 * Both are one-shot: they fire once and stop observing. Nothing here loops,
 * pulses or shimmers, because motion that repeats forever stops carrying
 * information and starts being wallpaper.
 *
 * Under prefers-reduced-motion the end state renders immediately and the
 * observer is never created.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";
import "./reveal.css";

const still = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function useOnce<T extends HTMLElement>(rootMargin = "-8% 0px -8% 0px") {
  const ref = useRef<T>(null);
  const [shown, setShown] = useState(() => still());

  useEffect(() => {
    if (shown) return;
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShown(true);
            observer.disconnect();
          }
        }
      },
      { rootMargin, threshold: 0.01 },
    );
    observer.observe(node);
    // Dead man's switch. If the observer never reports, for instance because
    // the document was hidden when it mounted, the content reveals itself
    // anyway. A missed animation is acceptable; unreadable text is not.
    const failsafe = window.setTimeout(() => setShown(true), 2500);
    return () => {
      observer.disconnect();
      window.clearTimeout(failsafe);
    };
  }, [shown, rootMargin]);

  return { ref, shown };
}

export function Reveal({
  children,
  delay = 0,
  as: Tag = "div",
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  as?: "div" | "section" | "li" | "article" | "p";
  className?: string;
}) {
  const { ref, shown } = useOnce<HTMLDivElement>();
  return (
    <Tag
      ref={ref as never}
      className={`reveal ${shown ? "in" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}

export function RevealLines({
  lines,
  className = "",
  as: Tag = "h1",
  stagger = 90,
}: {
  lines: string[];
  className?: string;
  as?: "h1" | "h2" | "p";
  stagger?: number;
}) {
  const { ref, shown } = useOnce<HTMLHeadingElement>();
  // The visual lines are separate blocks, so their text nodes would run
  // together for a screen reader ("Thebench"). The heading carries the
  // spaced string as its accessible name and the spans are hidden from the
  // tree; sighted and assistive readings then match.
  return (
    <Tag
      ref={ref as never}
      className={`reveal-lines ${className}`}
      aria-label={lines.join(" ")}
    >
      {lines.map((line, index) => (
        <span className="reveal-line" aria-hidden="true" key={line + index}>
          <span
            className={`reveal-line-inner ${shown ? "in" : ""}`}
            style={{ transitionDelay: `${index * stagger}ms` }}
          >
            {line}
          </span>
        </span>
      ))}
    </Tag>
  );
}
