/** The clip is the evidence: 1.8 to 3 seconds of the exact flagged sentence.
 *
 * It gets a real waveform drawn from the decoded samples, a scrubbable
 * playhead, and captions built from the word timings speech-to-text actually
 * recorded. Every pixel of the waveform is measured amplitude; none of it is
 * a generated shape, because a decorative waveform on a compliance artifact
 * would be a picture of evidence rather than evidence.
 *
 * Clicking a caption word seeks to that word. That is only possible because
 * the offsets, the word timings and the clip window are all recorded in the
 * evidence log and all index the same transcript.
 *
 * Runs with no audio never reach this component; they render the designed
 * NO AUDIO state instead.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { WordTiming } from "../types";
import "./audio.css";

interface Props {
  src: string;
  /** clip window inside the source turn audio, from finding.emit */
  clipStart: number;
  clipEnd: number;
  /** word timings for the whole turn, from the agent.turn.audio span */
  wordTimings: WordTiming[] | null;
  clipRef: string | null;
}

const BUCKETS = 220;

export function AudioEvidence({ src, clipStart, clipEnd, wordTimings, clipRef }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const railRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(Math.max(0.05, clipEnd - clipStart));
  const [peaks, setPeaks] = useState<number[] | null>(null);
  const [decodeFailed, setDecodeFailed] = useState(false);
  const [hover, setHover] = useState<number | null>(null);

  const words = (wordTimings ?? []).filter(
    (w) => w.end > clipStart && w.start < clipEnd + 0.05,
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(src);
        if (!response.ok) throw new Error(String(response.status));
        const raw = await response.arrayBuffer();
        const ctx = new AudioContext();
        const decoded = await ctx.decodeAudioData(raw);
        void ctx.close();
        if (cancelled) return;
        const channel = decoded.getChannelData(0);
        const size = Math.max(1, Math.floor(channel.length / BUCKETS));
        const out: number[] = [];
        for (let index = 0; index < BUCKETS; index += 1) {
          let peak = 0;
          const from = index * size;
          for (let at = from; at < Math.min(from + size, channel.length); at += 1) {
            const value = Math.abs(channel[at]);
            if (value > peak) peak = value;
          }
          out.push(peak);
        }
        // Normalise to the clip's own loudest point: a quiet clip should
        // still be readable, and the absolute level is not the evidence.
        const loudest = Math.max(...out, 0.0001);
        setPeaks(out.map((value) => value / loudest));
        setDuration(decoded.duration);
      } catch {
        if (!cancelled) setDecodeFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [src]);

  const paint = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !peaks) return;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }
    const g = canvas.getContext("2d");
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, width, height);

    const styles = getComputedStyle(canvas);
    const read = (name: string, fallback: string) =>
      styles.getPropertyValue(name).trim() || fallback;
    const spent = read("--ink", "#201e19");
    const ahead = read("--line-strong", "#b5ae99");
    const accent = read("--sig-trace", "#187582");

    const progress = duration > 0 ? time / duration : 0;
    const playedX = progress * width;
    const hoverX = hover !== null ? hover * width : null;
    const bar = width / peaks.length;
    const mid = height / 2;

    for (let index = 0; index < peaks.length; index += 1) {
      const x = index * bar;
      const h = Math.max(1.5, peaks[index] * (height - 8));
      const isSpent = x <= playedX;
      const isHovered =
        hoverX !== null && Math.abs(x - hoverX) < bar * 3.5;
      g.fillStyle = isHovered ? accent : isSpent ? spent : ahead;
      g.globalAlpha = isSpent || isHovered ? 1 : 0.55;
      g.fillRect(x, mid - h / 2, Math.max(1, bar - 1), h);
    }
    g.globalAlpha = 1;

    // playhead
    if (progress > 0) {
      g.fillStyle = accent;
      g.fillRect(playedX - 1, 0, 2, height);
    }
  }, [peaks, time, duration, hover]);

  useEffect(() => {
    paint();
  }, [paint]);

  useEffect(() => {
    const onResize = () => paint();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [paint]);

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) void audio.play();
    else audio.pause();
  };

  const seekTo = (fraction: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.max(0, Math.min(1, fraction)) * duration;
    setTime(audio.currentTime);
  };

  const fractionFromEvent = (clientX: number) => {
    const rail = railRef.current;
    if (!rail) return 0;
    const rect = rail.getBoundingClientRect();
    return (clientX - rect.left) / rect.width;
  };

  const sourceTime = time + clipStart;

  return (
    <figure className="audio-evidence">
      <div className="audio-row">
        <button
          className={`audio-play ${playing ? "playing" : ""}`}
          onClick={toggle}
          aria-label={playing ? "pause clip" : "play clip"}
          data-cursor={playing ? "pause" : "play"}
        >
          {playing ? (
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <rect x="5" y="3" width="3.5" height="14" />
              <rect x="11.5" y="3" width="3.5" height="14" />
            </svg>
          ) : (
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="M5 3 L17 10 L5 17 Z" />
            </svg>
          )}
        </button>

        <div
          className="audio-rail"
          ref={railRef}
          role="slider"
          tabIndex={0}
          aria-label="clip position"
          aria-valuemin={0}
          aria-valuemax={Number(duration.toFixed(2))}
          aria-valuenow={Number(time.toFixed(2))}
          data-cursor="scrub"
          onPointerDown={(event) => {
            (event.target as Element).setPointerCapture(event.pointerId);
            seekTo(fractionFromEvent(event.clientX));
          }}
          onPointerMove={(event) => {
            const fraction = fractionFromEvent(event.clientX);
            setHover(fraction);
            if (event.buttons === 1) seekTo(fraction);
          }}
          onPointerLeave={() => setHover(null)}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
              event.preventDefault();
              const step = (event.key === "ArrowRight" ? 1 : -1) * 0.05;
              seekTo((duration ? time / duration : 0) + step);
            }
            if (event.key === " " || event.key === "Enter") {
              event.preventDefault();
              toggle();
            }
          }}
        >
          {decodeFailed ? (
            <span className="mono muted audio-nowave">
              waveform unavailable; the clip still plays
            </span>
          ) : (
            <canvas ref={canvasRef} className="audio-wave" aria-hidden="true" />
          )}
          {hover !== null && !decodeFailed && (
            <span
              className="audio-hovertime mono"
              style={{ left: `${Math.max(0, Math.min(1, hover)) * 100}%` }}
            >
              {(hover * duration).toFixed(2)}s
            </span>
          )}
        </div>

        <span className="audio-clock mono">
          <span className="audio-clocknow">{time.toFixed(2)}</span>
          <span className="audio-clocktotal">/ {duration.toFixed(2)}s</span>
        </span>
      </div>

      {words.length > 0 ? (
        <p className="audio-captions" aria-label="clip transcript">
          {words.map((w) => {
            const active = sourceTime >= w.start && sourceTime <= w.end;
            const low = w.confidence < 0.75;
            return (
              <button
                key={`${w.char_start}-${w.char_end}`}
                className={`caption-word ${active ? "active" : ""} ${low ? "low" : ""}`}
                onClick={() => seekTo((w.start - clipStart) / duration)}
                title={
                  low
                    ? `speech-to-text confidence ${w.confidence.toFixed(2)}, below the 0.75 floor`
                    : `${w.start.toFixed(2)}s, confidence ${w.confidence.toFixed(2)}`
                }
                data-cursor="seek"
              >
                {w.text}
              </button>
            );
          })}
        </p>
      ) : (
        <p className="mono muted audio-nocaption">
          no word timings recorded for this clip window
        </p>
      )}

      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        onLoadedMetadata={(event) => {
          const value = event.currentTarget.duration;
          if (Number.isFinite(value) && value > 0) setDuration(value);
        }}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => {
          setPlaying(false);
          setTime(0);
        }}
        onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
      />

      <figcaption className="audio-meta mono">
        <span>
          window {clipStart.toFixed(2)}s to {clipEnd.toFixed(2)}s of the turn
        </span>
        {clipRef && (
          <span title={clipRef}>
            clip digest {clipRef.slice(0, 16)} &middot; content addressed,
            served by digest
          </span>
        )}
      </figcaption>
    </figure>
  );
}

export function NoAudio({ reason }: { reason?: string }) {
  return (
    <div className="audio-none">
      <span className="syslabel">no audio, text only run</span>
      <p className="muted">
        {reason ??
          "This run adjudicated text turns. Audio, where present, is evidence for a finding and never a detection input, so a text-only record is complete rather than degraded."}
      </p>
    </div>
  );
}
