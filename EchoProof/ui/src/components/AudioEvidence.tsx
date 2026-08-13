/** The clip is the evidence: 1.8 to 3 seconds of the exact flagged sentence.
 *
 * It gets a real waveform drawn from the decoded samples (honest data, not a
 * decorative animation) and transcript-synced captions built from the word
 * timings recorded by speech-to-text. Runs with no audio never reach this
 * component; they render the designed NO AUDIO state instead.
 */

import { useEffect, useRef, useState } from "react";
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

export function AudioEvidence({ src, clipStart, clipEnd, wordTimings, clipRef }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [peaks, setPeaks] = useState<number[] | null>(null);
  const [decodeFailed, setDecodeFailed] = useState(false);

  // Words inside the clip window. Times are in the source audio's clock;
  // the clip's own clock starts at clipStart.
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
        const buckets = 160;
        const size = Math.max(1, Math.floor(channel.length / buckets));
        const out: number[] = [];
        for (let index = 0; index < buckets; index += 1) {
          let peak = 0;
          const from = index * size;
          for (let at = from; at < Math.min(from + size, channel.length); at += 1) {
            const value = Math.abs(channel[at]);
            if (value > peak) peak = value;
          }
          out.push(peak);
        }
        setPeaks(out);
      } catch {
        if (!cancelled) setDecodeFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [src]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !peaks) return;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const g = canvas.getContext("2d");
    if (!g) return;
    g.scale(dpr, dpr);
    g.clearRect(0, 0, width, height);
    const styles = getComputedStyle(canvas);
    const inkFaint = styles.getPropertyValue("--ink-faint").trim() || "#98937f";
    const ink = styles.getPropertyValue("--ink").trim() || "#201e19";
    const duration = audioRef.current?.duration || clipEnd - clipStart || 1;
    const playedX = (time / duration) * width;
    const bar = width / peaks.length;
    for (let index = 0; index < peaks.length; index += 1) {
      const x = index * bar;
      const h = Math.max(1.5, peaks[index] * (height - 6));
      g.fillStyle = x <= playedX && (playing || time > 0) ? ink : inkFaint;
      g.fillRect(x, (height - h) / 2, Math.max(1, bar - 1.5), h);
    }
  }, [peaks, time, playing, clipEnd, clipStart]);

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) void audio.play();
    else audio.pause();
  };

  // The word under the playhead, in source-audio time.
  const sourceTime = time + clipStart;

  return (
    <figure className="audio-evidence">
      <div className="audio-row">
        <button
          className="audio-play"
          onClick={toggle}
          aria-label={playing ? "pause clip" : "play clip"}
        >
          {playing ? (
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <rect x="4" y="3" width="4" height="14" />
              <rect x="12" y="3" width="4" height="14" />
            </svg>
          ) : (
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="M5 3 L17 10 L5 17 Z" />
            </svg>
          )}
        </button>
        <div className="audio-wave-wrap">
          {decodeFailed ? (
            <span className="mono muted">waveform unavailable; clip still plays</span>
          ) : (
            <canvas ref={canvasRef} className="audio-wave" aria-hidden="true" />
          )}
        </div>
        <span className="audio-window mono">
          {clipStart.toFixed(2)}s to {clipEnd.toFixed(2)}s
        </span>
      </div>

      {words.length > 0 ? (
        <p className="audio-captions" aria-label="clip transcript">
          {words.map((w) => (
            <span
              key={`${w.char_start}-${w.char_end}`}
              className={
                sourceTime >= w.start && sourceTime <= w.end && playing
                  ? "caption-word active"
                  : "caption-word"
              }
            >
              {w.text}{" "}
            </span>
          ))}
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
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => {
          setPlaying(false);
          setTime(0);
        }}
        onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
      />
      {clipRef && (
        <figcaption className="audio-meta mono">
          clip digest {clipRef.slice(0, 16)} &middot; content addressed, served
          from disk by digest
        </figcaption>
      )}
    </figure>
  );
}

export function NoAudio({ reason }: { reason?: string }) {
  return (
    <div className="audio-none">
      <span className="syslabel">no audio, text only run</span>
      <p className="muted">
        {reason ??
          "This run adjudicated text turns. Audio, where present, is evidence for a finding, never a detection input, so a text-only record is complete rather than degraded."}
      </p>
    </div>
  );
}
