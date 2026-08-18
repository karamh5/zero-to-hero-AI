"""Measure retrieval and calibrate the two confidence thresholds.

This runs before the judge exists, on purpose. ARCHITECTURE.md decision 1 requires
retrieval to be built and measured first, because a judge tuned on top of unknown
retrieval quality cannot be debugged: every wrong verdict has two possible
causes and no way to separate them.

Outputs:
    a precision@1 number against fixtures/retrieval_pairs.jsonl
    packs/criteria/thresholds.json, holding floor and ceiling as two values

Run:
    python scripts/eval_retrieval.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import FIXTURES_DIR  # noqa: E402
from core.contracts import RetrievalCandidate  # noqa: E402
from core.packs import (  # noqa: E402
    load_criteria,
    load_policy_pack,
    policy_index_dir,
    save_criteria,
)
from engine.pipeline import build_retrieval_query  # noqa: E402
from engine.retrieval.base import RetrievalConfig, root_section  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402

PAIRS_PATH = FIXTURES_DIR / "retrieval_pairs.jsonl"

# Precision target used to pick the ceiling. Above the ceiling, a verdict is
# adjudicated rather than abstained, so this is the accuracy the judge is
# allowed to assume about its input.
CEILING_PRECISION_TARGET = 0.90

# Fraction of correct retrievals the floor is allowed to exclude. The floor
# decides no_governing_rule, which asserts to a client that nothing regulates
# an area. Being wrong there is worse than abstaining, so it is set to admit
# essentially every genuine match.
FLOOR_RECALL_TARGET = 0.98

# Recall at these depths separates a ranking problem from a recall problem. If
# recall@50 is high while precision@1 is low, the governing section is being
# retrieved and then ranked below something else, which is what the rerank stage
# in SPEC section 5 exists to fix.
RECALL_CUTOFFS = (1, 3, 5, 10, 25, 50)


def matches(expected: str, selected: str | None) -> bool:
    """Whether a retrieved identifier satisfies the pair's expectation.

    Prefix matching at paragraph granularity: a pair asking for 1006.14(b) is
    satisfied by 1006.14(b)(2)(i), because the pair named the provision and the
    retriever found a more specific paragraph inside it. The boundary character
    check matters, otherwise 1006.2 would be satisfied by 1006.22.
    """
    if selected is None:
        return False
    if selected == expected:
        return True
    return selected.startswith(expected) and selected[len(expected)] in "(#"


def load_pairs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"retrieval pairs not found at {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def precision_at(threshold: float, results: list[tuple[bool, float]]) -> tuple[float, int]:
    """Precision and coverage among results scoring at or above `threshold`."""
    kept = [hit for hit, score in results if score >= threshold]
    if not kept:
        return 0.0, 0
    return sum(kept) / len(kept), len(kept)


def choose_floor(correct_scores: list[float]) -> float:
    """Highest floor that still admits FLOOR_RECALL_TARGET of true matches."""
    if not correct_scores:
        return 0.0
    ordered = sorted(correct_scores)
    index = int((1.0 - FLOOR_RECALL_TARGET) * len(ordered))
    return round(max(0.0, ordered[min(index, len(ordered) - 1)] - 0.01), 4)


def choose_ceiling(results: list[tuple[bool, float]], floor: float) -> float:
    """Lowest ceiling above the floor that reaches the precision target."""
    candidates = sorted({round(score, 3) for _hit, score in results})
    best: float | None = None
    for threshold in candidates:
        if threshold <= floor:
            continue
        precision, coverage = precision_at(threshold, results)
        if coverage >= 5 and precision >= CEILING_PRECISION_TARGET:
            best = threshold
            break
    if best is None:
        # No threshold reaches the target. Report that honestly by setting the
        # ceiling above every observed score, which routes everything to
        # retrieval_below_confidence rather than pretending to a precision the
        # retriever does not have.
        best = round(max(score for _hit, score in results) + 0.01, 4)
    return max(best, round(floor + 0.01, 4))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and calibrate thresholds.")
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--first-stage-k", type=int, default=50)
    parser.add_argument("--rerank-k", type=int, default=50)
    parser.add_argument("--no-write", action="store_true", help="do not write thresholds.json")
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="measure fusion alone, without the SPEC section 5 rerank stage",
    )
    parser.add_argument(
        "--pairs",
        default=str(PAIRS_PATH),
        help="pair file to evaluate against",
    )
    parser.add_argument(
        "--raw-query",
        action="store_true",
        help="skip the pack query template and send the pair text unchanged",
    )
    args = parser.parse_args()

    pack = load_policy_pack(args.pack)
    chunks = build_chunks(pack.sections)
    reranker = None if args.no_rerank else CrossEncoderReranker()
    retriever = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=reranker
    )
    retriever.index(chunks)

    pairs = load_pairs(Path(args.pairs))

    # Calibration has to see the same query text production sends, or the floor
    # and ceiling are fitted to a distribution the system never encounters. That
    # was the defect that made the first calibration useless: pairs were phrased
    # as questions, production sends claims, and the two score differently
    # enough that every real claim abstained.
    criteria = None if args.raw_query else load_criteria("criteria")

    # Placeholder thresholds. Only the retrieval depths matter during the sweep,
    # since the floor and ceiling are what this run is measuring in order to set.
    sweep_config = RetrievalConfig(
        floor=0.0,
        ceiling=1.0,
        top_k=args.top_k,
        first_stage_k=args.first_stage_k,
        rerank_k=args.rerank_k,
    )

    results: list[tuple[bool, float]] = []
    misses: list[tuple[str, str, str, float]] = []
    top5_hits = 0
    recall_hits: dict[int, int] = {cutoff: 0 for cutoff in RECALL_CUTOFFS}
    root_hits = 0

    for pair in pairs:
        query = build_retrieval_query(pair["query"], criteria)
        candidates: list[RetrievalCandidate] = retriever.search(query, sweep_config)
        top = candidates[0] if candidates else None
        hit = matches(pair["expected_section_id"], top.section_id if top else None)
        score = top.score if top else 0.0
        results.append((hit, score))

        # A miss that lands in the right root section is a different failure
        # from one that lands in an unrelated part of the corpus. The first puts
        # a slightly imprecise citation on a finding card; the second cites the
        # wrong rule entirely. Reporting one number for both would hide that.
        if top is not None and root_section(top.section_id) == root_section(
            pair["expected_section_id"]
        ):
            root_hits += 1

        for cutoff in RECALL_CUTOFFS:
            if any(
                matches(pair["expected_section_id"], c.section_id)
                for c in candidates[:cutoff]
            ):
                recall_hits[cutoff] += 1
        if any(
            matches(pair["expected_section_id"], c.section_id) for c in candidates[:5]
        ):
            top5_hits += 1
        if not hit:
            misses.append(
                (
                    pair["pair_id"],
                    pair["expected_section_id"],
                    top.section_id if top else "<none>",
                    score,
                )
            )

    total = len(results)
    hits = sum(hit for hit, _ in results)
    precision_1 = hits / total

    correct_scores = [score for hit, score in results if hit]
    floor = choose_floor(correct_scores)
    ceiling = choose_ceiling(results, floor)

    # Constructing the config validates that the two values are a separated
    # pair. If calibration ever collapses them, this raises rather than
    # silently shipping a single-threshold retriever.
    config = RetrievalConfig(
        floor=floor,
        ceiling=ceiling,
        top_k=args.top_k,
        first_stage_k=args.first_stage_k,
        rerank_k=args.rerank_k,
    )

    print(f"pack                 {pack.pack_id} ({pack.citation})")
    print(f"policy_pack_version  {pack.version[:16]}")
    print(f"chunks indexed       {len(chunks)}")
    print(f"pairs evaluated      {total}")
    print()
    print(f"precision@1          {precision_1:.3f}  ({hits}/{total})   exact paragraph")
    print(f"section precision@1  {root_hits / total:.3f}  ({root_hits}/{total})   right root section")
    print("recall by depth")
    for cutoff in RECALL_CUTOFFS:
        got = recall_hits[cutoff]
        print(f"  recall@{cutoff:<3}         {got / total:.3f}  ({got}/{total})")
    print()
    print("threshold sweep (score cutoff -> precision, coverage)")
    for threshold in [0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        precision, coverage = precision_at(threshold, results)
        print(f"  >= {threshold:.2f}   precision {precision:.3f}   coverage {coverage}/{total}")
    print()
    print("calibrated thresholds (two separate values, never merged)")
    print(f"  floor   {config.floor:.4f}   below this -> no_governing_rule")
    print(f"  ceiling {config.ceiling:.4f}   below this -> retrieval_below_confidence")
    print(f"  separation {config.ceiling - config.floor:.4f}")

    if misses:
        print()
        print(f"misses at rank 1 ({len(misses)}):")
        for pair_id, expected, got, score in misses:
            print(f"  {pair_id}  expected {expected:24} got {got:24} score {score:.3f}")

    if not args.no_write:
        payload = {
            "pack_id": pack.pack_id,
            "policy_pack_version": pack.version,
            "retriever": retriever.config_fingerprint(),
            "thresholds": config.to_dict(),
            "measured": {
                "pairs": total,
                "precision_at_1": round(precision_1, 4),
                "recall_at_5": round(top5_hits / total, 4),
                "floor_recall_target": FLOOR_RECALL_TARGET,
                "ceiling_precision_target": CEILING_PRECISION_TARGET,
            },
        }
        path = save_criteria("thresholds", payload)
        print()
        print(f"wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
