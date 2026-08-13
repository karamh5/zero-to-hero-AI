/** A real number, counted up once when it scrolls into view.
 *
 * The count is presentation of a value that is already known and already
 * fetched. It animates the arrival of a fact, never the progress of work,
 * which is the distinction this product cares about: nothing on the
 * adjudication path may animate toward a number it does not have.
 */

import { useEffect, useRef, useState } from "react";

export function Counter({
  value,
  decimals = 0,
  duration = 1100,
  prefix = "",
  suffix = "",
}: {
  value: number;
  decimals?: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(value);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setStarted(true);
          observer.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!started) return;
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      // expo-out: lands on the true value early and settles
      const eased = 1 - Math.pow(1 - t, 4);
      setShown(value * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
      else setShown(value);
    };
    setShown(0);
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [started, value, duration]);

  return (
    <span ref={ref} className="counter">
      {prefix}
      {shown.toFixed(decimals)}
      {suffix}
    </span>
  );
}
