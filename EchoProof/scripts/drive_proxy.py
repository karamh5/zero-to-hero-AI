"""Drive the capture proxy the way a client's voice agent would.

Calls the proxy's OpenAI-compatible endpoint with the standard SDK, so the proxy
is exercised through its real interface rather than through a bespoke test hook.
Reports the added overhead as a distribution, because a single sample is not a
measurement.

Run, in a second shell, with scripts/run_proxy.py already listening:
    python scripts/drive_proxy.py
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import httpx
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import EXTRACT_MODEL  # noqa: E402

# Agent system prompt seeded to produce a turn with a real compliance issue in
# it, so the end to end path has something to find.
AGENT_SYSTEM = (
    "You are a collections voice agent for Harbor Recovery. Answer the caller in "
    "two sentences, conversationally, as if speaking on a phone call. Do not use "
    "bullet points."
)
AGENT_TURNS = [
    "Hi, I got a voicemail about an account. What do I owe and can anything be done about my credit?",
    "What time will you call me next?",
    "I already told you I have a lawyer for this.",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Drive the EchoProof proxy.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8077/v1")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--pace", type=float, default=2.0, help="seconds between calls")
    args = parser.parse_args()

    # The proxy authenticates upstream itself, so the key here is unused. Sent
    # only because the SDK requires one to be present.
    client = OpenAI(api_key="unused-by-proxy", base_url=args.base_url)

    overheads: list[float] = []
    upstreams: list[float] = []

    for round_index in range(args.repeat):
        for index, user_turn in enumerate(AGENT_TURNS, start=1):
            # Paced and retried here rather than inside the proxy. A capture
            # proxy must stay transparent: it returns whatever upstream returned,
            # including a 429, because swallowing upstream state would hide a
            # real condition from the client's own retry logic.
            response = None
            for attempt in range(5):
                try:
                    response = client.chat.completions.with_raw_response.create(
                        model=EXTRACT_MODEL,
                        messages=[
                            {"role": "system", "content": AGENT_SYSTEM},
                            {"role": "user", "content": user_turn},
                        ],
                        temperature=0,
                        max_tokens=160,
                    )
                    break
                except Exception as exc:  # noqa: BLE001 - retried below
                    if "429" not in str(exc) and "rate" not in str(exc).lower():
                        raise
                    time.sleep(2 * (attempt + 1))
            if response is None:
                print("  upstream stayed rate limited, skipping this turn")
                continue
            overhead = float(response.headers.get("x-echoproof-overhead-ms", "nan"))
            upstream = float(response.headers.get("x-echoproof-upstream-ms", "nan"))
            overheads.append(overhead)
            upstreams.append(upstream)

            completion = response.parse()
            text = completion.choices[0].message.content or ""
            print(f"[{round_index + 1}.{index}] agent said: {text.strip()[:110]}")
            print(f"      echoproof overhead {overhead:7.3f} ms | "
                  f"upstream {upstream:8.1f} ms")
            time.sleep(args.pace)

    print()
    print("proxy overhead added by EchoProof, milliseconds")
    print(f"  samples   {len(overheads)}")
    print(f"  median    {statistics.median(overheads):.3f}")
    print(f"  mean      {statistics.fmean(overheads):.3f}")
    print(f"  max       {max(overheads):.3f}")
    print(f"  budget    50.000")
    print(f"  verdict   {'WITHIN BUDGET' if max(overheads) < 50 else 'OVER BUDGET'}")
    print()
    print(f"upstream model latency for comparison, median "
          f"{statistics.median(upstreams):.1f} ms")

    metrics = httpx.get(args.base_url.replace('/v1', '') + "/metrics", timeout=10).json()
    print()
    print("server side metrics")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
