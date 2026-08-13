"""Measure the retrieval cache, and prove it does not change results.

Speed is worthless here if the cached path returns anything different from the
uncached one, so this checks equality first and reports timing second.

Run:
    python scripts/bench_cache.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import POLICY_DIR  # noqa: E402
from core.packs import load_criteria, load_policy_pack, policy_index_dir  # noqa: E402
from engine.retrieval.base import RetrievalConfig  # noqa: E402
from engine.retrieval.cache import CachingRetriever  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402

QUERIES = [
    "What limits apply to contacting a person at an unusual hour?",
    "May an agent state that it will take an action it cannot legally take?",
    "What is required after receiving a written dispute?",
    "How often may an agent place telephone calls about one debt?",
    "What must be disclosed in the first communication about a debt?",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the retrieval cache.")
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--clear", action="store_true", help="wipe the cache first")
    args = parser.parse_args()

    pack = load_policy_pack(args.pack)
    thresholds = load_criteria("thresholds")["thresholds"]
    config = RetrievalConfig(
        floor=float(thresholds["floor"]),
        ceiling=0.548,
        top_k=int(thresholds.get("top_k", 50)),
        first_stage_k=int(thresholds.get("first_stage_k", 50)),
        rerank_k=int(thresholds.get("rerank_k", 50)),
    )

    cache_dir = POLICY_DIR / args.pack / "retrieval_cache"
    if args.clear and cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"cleared {cache_dir}")

    print("loading retrieval stack ...")
    inner = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    inner.index(build_chunks(pack.sections))
    retriever = CachingRetriever(inner, cache_dir, pack.version)

    print()
    print("pass 1, cold")
    cold_started = time.perf_counter()
    cold = {q: retriever.search(q, config) for q in QUERIES}
    cold_elapsed = time.perf_counter() - cold_started
    print(f"  {cold_elapsed:.2f} s for {len(QUERIES)} queries "
          f"({cold_elapsed / len(QUERIES):.2f} s each)")

    print()
    print("pass 2, warm")
    warm_started = time.perf_counter()
    warm = {q: retriever.search(q, config) for q in QUERIES}
    warm_elapsed = time.perf_counter() - warm_started
    print(f"  {warm_elapsed:.3f} s for {len(QUERIES)} queries "
          f"({warm_elapsed / len(QUERIES):.3f} s each)")

    print()
    print("equality check, cached against uncached")
    identical = True
    for query in QUERIES:
        a, b = cold[query], warm[query]
        if len(a) != len(b):
            identical = False
            break
        for x, y in zip(a, b):
            if (
                x.section_id != y.section_id
                or x.chunk_id != y.chunk_id
                or abs(x.score - y.score) > 1e-12
                or x.text != y.text
            ):
                identical = False
                break
    print(f"  candidate lists identical: {identical}")
    if not identical:
        print("  CACHE CHANGES RESULTS. Do not use it.")
        return 1

    print()
    print(f"speedup        {cold_elapsed / max(warm_elapsed, 1e-6):.0f}x")
    print(f"cache stats    {retriever.stats()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
