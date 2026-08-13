"""Record the fix-and-rerun segment for playback during the live call's dead time.

Measured adjudication latency is up to 140 seconds per turn, so a fix-and-rerun
cannot complete inside a single call's dead time. It is pre-recorded, and the
slide says so.

The recording is a replay of `runs/fix-and-rerun/rerun.json`, which is real
output from a real run. Nothing here is mocked or re-enacted: the agent turns,
the findings, and the delta are the ones the system produced.

Run:
    python scripts/record_rerun_clip.py
    python scripts/record_rerun_clip.py --play     # play it back at demo pace
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import PROJECT_ROOT, RUNS_DIR  # noqa: E402

# Pacing, in seconds. Tuned so the whole clip runs about 100 seconds, which sits
# inside the measured 140 second worst case for a live adjudication.
BEAT = 1.6
LINE = 0.45


def build_frames(rerun: dict) -> list[tuple[float, str]]:
    """Turn the recorded delta into timed lines."""
    frames: list[tuple[float, str]] = []

    def add(text: str, pause: float = LINE) -> None:
        frames.append((pause, text))

    add("EchoProof fix and re-run", BEAT)
    add(f"scenario {rerun.get('scenario_id')}  seed {rerun.get('seed')}", BEAT)
    add("", LINE)
    add("BEFORE  original agent prompt", BEAT)
    for turn in rerun.get("before_agent_turns", []):
        add(f"  agent: {turn}", LINE)
    add("", LINE)
    for finding in rerun.get("before_findings", []):
        add(f"  FINDING {finding.get('verdict')} @ {finding.get('section_id')}", BEAT)
    add(f"  {rerun.get('before_count', 0)} finding(s)", BEAT)
    add("", BEAT)
    add("Agent prompt corrected to honour the cease request.", BEAT)
    add("Same scenario. Same seed. Same judge. Same thresholds.", BEAT)
    add("", LINE)
    add("AFTER   corrected agent prompt", BEAT)
    for turn in rerun.get("after_agent_turns", []):
        add(f"  agent: {turn}", LINE)
    add("", LINE)
    add(f"  {rerun.get('after_count', 0)} finding(s)", BEAT)
    add("", BEAT)
    add("DELTA", BEAT)
    closed = [k.get("section_id") for k in rerun.get("closed", [])]
    persisted = [k.get("section_id") for k in rerun.get("persisted", [])]
    new = [k.get("section_id") for k in rerun.get("new", [])]
    add(f"  closed     {closed or 'none'}", BEAT)
    add(f"  persisted  {persisted or 'none'}", BEAT)
    add(f"  new        {new or 'none'}", BEAT)
    add(f"  improved   {rerun.get('improved')}", BEAT)
    add("", BEAT)
    add("A finding is only useful if the fix can be verified.", BEAT * 2)
    return frames


def main() -> int:
    parser = argparse.ArgumentParser(description="Record the fix-and-rerun clip.")
    parser.add_argument("--play", action="store_true", help="play at demo pace")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    source = RUNS_DIR / "fix-and-rerun" / "rerun.json"
    if not source.exists():
        print(f"no recorded rerun at {source}; run scripts/fix_and_rerun.py first")
        return 1

    rerun = json.loads(source.read_text(encoding="utf-8"))
    frames = build_frames(rerun)
    duration = sum(pause for pause, _ in frames)

    out_dir = PROJECT_ROOT / "demo" / "backup"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "rerun_clip.json").write_text(
        json.dumps(
            {
                "source": str(source),
                "note": "Replay of a real fix-and-rerun. Not a mock.",
                "duration_seconds": round(duration, 1),
                "frames": [{"pause": p, "text": t} for p, t in frames],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out_dir / "rerun_clip.txt").write_text(
        "\n".join(text for _pause, text in frames), encoding="utf-8"
    )

    print(f"frames            {len(frames)}")
    print(f"clip duration     {duration:.0f}s")
    print(f"fits in dead time {duration <= 140} (measured worst case 140s)")
    print(f"written           {out_dir / 'rerun_clip.json'}")
    print(f"plain text        {out_dir / 'rerun_clip.txt'}")

    if args.play:
        print()
        for pause, text in frames:
            print(text, flush=True)
            time.sleep(pause / max(args.speed, 0.01))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
