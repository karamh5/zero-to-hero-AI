"""Measure the live adjudication path, by stage.

The run sheet needs a real number for how long the room waits between the agent
speaking and the finding appearing. Estimating it would be guessing at the one
quantity a live demo cannot recover from.

Reported as a distribution over repeated runs, cold cache and warm, because a
single sample is not a measurement. The run sheet quotes the **worst case**: a
demo is planned against the bad case, not the median.

Run:
    python scripts/measure_latency.py
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import POLICY_DIR, PROJECT_ROOT, load_settings  # noqa: E402
from core.packs import (  # noqa: E402
    load_criteria,
    load_policy_pack,
    policy_index_dir,
)
from engine.extract import extract_claims  # noqa: E402
from engine.judge import judge_claim  # noqa: E402
from engine.pipeline import build_retrieval_query  # noqa: E402
from engine.retrieval.base import RetrievalConfig, merge  # noqa: E402
from engine.retrieval.cache import CachingRetriever  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402
from models.client import ModelClient  # noqa: E402

TURN = (
    "If we do not have payment by end of business today, a warrant gets issued "
    "and you could be picked up over the weekend."
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure adjudication latency.")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--pack", default="reg_f")
    args = parser.parse_args()

    settings = load_settings()
    pack = load_policy_pack(args.pack)
    criteria = load_criteria("criteria")
    thresholds = load_criteria("thresholds")["thresholds"]
    config = RetrievalConfig(
        floor=float(thresholds["floor"]),
        ceiling=0.548,
        conflict_margin=float(thresholds["conflict_margin"]),
        top_k=int(thresholds.get("top_k", 50)),
        first_stage_k=int(thresholds.get("first_stage_k", 50)),
        rerank_k=int(thresholds.get("rerank_k", 50)),
        judge_candidates=int(thresholds.get("judge_candidates", 10)),
    )

    load_started = time.perf_counter()
    inner = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    inner.index(build_chunks(pack.sections))
    retriever = CachingRetriever(
        inner, POLICY_DIR / args.pack / "retrieval_cache", pack.version
    )
    # Force the reranker to load now rather than inside the first timed query.
    retriever.search("warm up the model", config)
    startup = time.perf_counter() - load_started

    client = ModelClient(settings)
    samples: list[dict[str, float]] = []

    for index in range(args.repeat):
        totals = {"extract": 0.0, "retrieve": 0.0, "judge": 0.0}

        started = time.perf_counter()
        extraction = extract_claims(client, TURN, turn_id=f"lat{index}")
        totals["extract"] = time.perf_counter() - started

        for claim in extraction.claims:
            questions = list(claim.retrieval_questions) or [claim.text(TURN)]

            started = time.perf_counter()
            results = [
                retriever.retrieve(build_retrieval_query(q, criteria), config)
                for q in questions
            ]
            retrieval = merge(results, config)
            totals["retrieve"] += time.perf_counter() - started

            started = time.perf_counter()
            judge_claim(
                client=client,
                claim=claim,
                transcript=TURN,
                retrieval=retrieval,
                call_date=date.today(),
                shortlist_size=config.judge_candidates,
                ceiling=config.ceiling,
            )
            totals["judge"] += time.perf_counter() - started

        totals["claims"] = float(len(extraction.claims))
        totals["total"] = totals["extract"] + totals["retrieve"] + totals["judge"]
        samples.append(totals)
        state = "cold" if index == 0 else "warm"
        print(f"run {index + 1} ({state:4}) {totals['claims']:.0f} claims  "
              f"extract {totals['extract']:5.1f}s  "
              f"retrieve {totals['retrieve']:6.1f}s  "
              f"judge {totals['judge']:5.1f}s  "
              f"total {totals['total']:6.1f}s")

    def stat(key: str, fn) -> float:  # type: ignore[no-untyped-def]
        return fn([s[key] for s in samples])

    print()
    print("stage latency, seconds")
    print(f"{'stage':<12} {'median':>8} {'worst':>8}")
    for key in ("extract", "retrieve", "judge", "total"):
        print(f"{key:<12} {stat(key, statistics.median):>8.1f} {stat(key, max):>8.1f}")
    print()
    print(f"stack startup (one time, before the demo)  {startup:.1f}s")
    print(f"cache stats                                {retriever.stats()}")
    print()
    print(f"RUN SHEET NUMBER, worst case per turn      {stat('total', max):.0f}s")
    print("Planned against the worst case, not the median.")

    out = PROJECT_ROOT / "demo" / "latency.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "samples": samples,
                "startup_seconds": round(startup, 2),
                "median_total": round(stat("total", statistics.median), 2),
                "worst_total": round(stat("total", max), 2),
                "cache": retriever.stats(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
