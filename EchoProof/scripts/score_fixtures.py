"""Score the development fixtures and produce the headline numbers (SPEC 11).

Never reads fixtures/heldout.jsonl. That split is sealed until Phase 4 and is
scored exactly once, per CLAUDE.md decision 10.

Method note that matters for reading the output. The run executes with the
retrieval ceiling effectively disabled, and every claim's model verdict is
recorded alongside the retrieval score of the section the judge selected. The
verdict at any other ceiling is then recoverable arithmetically, because a
claim whose selected score falls below a ceiling becomes an abstention at that
ceiling and nothing else changes. That is what makes a real precision-recall
curve affordable: one pass over the fixtures instead of one pass per threshold.
SPEC section 11 asks for a curve rather than a single accuracy number precisely
because a single number can be selected by moving the threshold.

Run:
    python scripts/score_fixtures.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import FIXTURES_DIR, RUNS_DIR, load_settings  # noqa: E402
from core.contracts import Verdict  # noqa: E402
from core.packs import (  # noqa: E402
    load_criteria,
    load_policy_pack,
    policy_index_dir,
)
from engine.evidence import EvidenceLog  # noqa: E402
from engine.pipeline import adjudicate_turn  # noqa: E402
from engine.retrieval.base import RetrievalConfig  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402
from models.client import ModelClient  # noqa: E402

CALL_DATE = date(2026, 8, 12)


def cites_correctly(expected: str | None, actual: str | None) -> bool:
    """Whether a cited section satisfies the ground truth at its granularity."""
    if not expected or not actual:
        return False
    if actual == expected:
        return True
    # A more specific paragraph inside the expected provision counts. The
    # boundary character check matters: 1006.2 is a prefix of 1006.22.
    return actual.startswith(expected) and actual[len(expected)] in "(#"


def main() -> int:
    parser = argparse.ArgumentParser(description="Score the development fixtures.")
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--run-id", default="fixtures-dev")
    parser.add_argument("--limit", type=int, default=0, help="score only the first N")
    parser.add_argument(
        "--split",
        choices=["dev", "heldout"],
        default="dev",
        help=(
            "which split to score. heldout is sealed and is scored exactly once, "
            "at the end of Phase 4, per CLAUDE.md decision 10."
        ),
    )
    args = parser.parse_args()

    settings = load_settings()
    pack = load_policy_pack(args.pack)
    criteria = load_criteria("criteria")
    thresholds = load_criteria("thresholds")["thresholds"]

    floor = float(thresholds["floor"])
    calibrated_ceiling = float(thresholds["ceiling"])

    # Ceiling disabled for the run. Reinstated arithmetically in the sweep.
    config = RetrievalConfig(
        floor=floor,
        ceiling=floor + 1e-4,
        conflict_margin=float(thresholds["conflict_margin"]),
        top_k=int(thresholds.get("top_k", 50)),
        first_stage_k=int(thresholds.get("first_stage_k", 50)),
        rerank_k=int(thresholds.get("rerank_k", 50)),
        judge_candidates=int(thresholds.get("judge_candidates", 10)),
    )

    retriever = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    retriever.index(build_chunks(pack.sections))
    obligations = {s.section_id: s.obligation_type.value for s in pack.sections}
    client = ModelClient(settings)

    split_file = "fixtures.jsonl" if args.split == "dev" else "heldout.jsonl"
    rows = [
        json.loads(line)
        for line in (FIXTURES_DIR / split_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        rows = rows[: args.limit]

    if args.split == "heldout":
        print("SCORING THE HELD-OUT SPLIT. This split is scored exactly once.")
        print("Nothing may be tuned after reading these numbers.")
        print()

    log = EvidenceLog(run_id=args.run_id)
    records: list[dict[str, Any]] = []
    total_cost = 0.0
    total_tokens = 0

    for index, row in enumerate(rows, start=1):
        result = adjudicate_turn(
            client=client,
            retriever=retriever,
            config=config,
            transcript=row["turn_text"],
            turn_id=row["fixture_id"],
            call_date=CALL_DATE,
            log=log,
            criteria=criteria,
            section_obligations=obligations,
        )
        total_cost += result.cost_usd
        total_tokens += result.total_tokens

        claims = [
            {
                "claim_id": j.adjudication.claim_id,
                "claim_type": next(
                    c.claim_type.value
                    for c in result.claims
                    if c.claim_id == j.adjudication.claim_id
                ),
                "verdict": j.adjudication.verdict.value,
                "section_id": j.adjudication.section_id,
                "selected_score": j.inputs.selected_score,
                "decided_by": j.adjudication.decided_by,
                "cleared_floor": j.inputs.cleared_floor,
            }
            for j in result.judgements
        ]
        records.append(
            {
                "fixture_id": row["fixture_id"],
                "category": row["category"],
                "expected_verdict": row["ground_truth"]["verdict"],
                "expected_section_id": row["ground_truth"]["section_id"],
                "claims": claims,
            }
        )
        print(f"[{index}/{len(rows)}] {row['fixture_id']:8} {row['category']:17} "
              f"{len(claims)} claim(s)")

    out_dir = RUNS_DIR / args.run_id
    log.write(out_dir / "evidence.jsonl")
    (out_dir / "scored.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    report(records, floor, calibrated_ceiling, total_cost, total_tokens, log)
    return 0


def effective_contradicted(claim: dict[str, Any], ceiling: float) -> bool:
    """Whether this claim is a finding once the ceiling is reapplied."""
    return (
        claim["verdict"] == Verdict.CONTRADICTED.value
        and claim["selected_score"] >= ceiling
    )


def report(
    records: list[dict[str, Any]],
    floor: float,
    calibrated_ceiling: float,
    cost: float,
    tokens: int,
    log: EvidenceLog,
) -> None:
    violations = [r for r in records if r["category"] == "seeded_violation"]
    hard_negatives = [r for r in records if r["category"] == "hard_negative"]
    easy_negatives = [r for r in records if r["category"] == "easy_negative"]

    print()
    print("=" * 72)
    print("EchoProof fixture scoring, development split only")
    print("=" * 72)
    print(f"seeded violations   {len(violations)}")
    print(f"hard negatives      {len(hard_negatives)}   (false positive denominator)")
    print(f"easy negatives      {len(easy_negatives)}   (excluded from the FP rate)")
    print(f"held-out            SEALED, not read by this script")
    print()

    print("precision-recall curve, swept over the retrieval ceiling")
    print("  ceiling  detection  FP(hard)  FP(easy)  citation@1  abstain")
    curve = []
    candidates = sorted(
        {round(c["selected_score"], 3) for r in records for c in r["claims"]}
        | {floor, calibrated_ceiling}
    )
    for ceiling in candidates:
        if ceiling < floor:
            continue
        detected = sum(
            1 for r in violations if any(effective_contradicted(c, ceiling) for c in r["claims"])
        )
        fp_hard = sum(
            1 for r in hard_negatives
            if any(effective_contradicted(c, ceiling) for c in r["claims"])
        )
        fp_easy = sum(
            1 for r in easy_negatives
            if any(effective_contradicted(c, ceiling) for c in r["claims"])
        )
        cited = sum(
            1 for r in violations
            if any(
                effective_contradicted(c, ceiling)
                and cites_correctly(r["expected_section_id"], c["section_id"])
                for c in r["claims"]
            )
        )
        all_claims = [c for r in records for c in r["claims"]]
        abstains = sum(
            1 for c in all_claims
            if c["verdict"] in {v.value for v in Verdict if v.is_abstention}
            or c["selected_score"] < ceiling
        )
        detection = detected / len(violations) if violations else 0.0
        fp_rate = fp_hard / len(hard_negatives) if hard_negatives else 0.0
        citation = cited / detected if detected else 0.0
        abstain_rate = abstains / len(all_claims) if all_claims else 0.0
        curve.append((ceiling, detection, fp_rate, citation))
        marker = "  <- calibrated" if abs(ceiling - calibrated_ceiling) < 1e-6 else ""
        print(f"  {ceiling:7.3f}  {detection:9.3f}  {fp_rate:8.3f}  {fp_easy:8d}  "
              f"{citation:10.3f}  {abstain_rate:7.3f}{marker}")

    print()
    target_fp = 0.02
    viable = [c for c in curve if c[2] <= target_fp]
    if viable:
        best = max(viable, key=lambda c: c[1])
        print(f"operating point at FP <= {target_fp:.2f} on hard negatives")
        print(f"  ceiling            {best[0]:.3f}")
        print(f"  detection rate     {best[1]:.3f}")
        print(f"  false positive     {best[2]:.3f}")
        print(f"  citation precision {best[3]:.3f}")
        print()
        print(f"SPEC section 11 band: {band(best[1])}")
    else:
        print(f"no ceiling achieves FP <= {target_fp:.2f} on hard negatives")

    print()
    print("claim type distribution (extraction, not recall)")
    types = Counter(c["claim_type"] for r in records for c in r["claims"])
    for name, count in sorted(types.items()):
        print(f"  {name:18} {count}")
    print("  recall by claim type needs per-claim ground truth, which this set")
    print("  does not carry. Recorded as a gap rather than estimated.")

    print()
    print("verdict distribution at the calibrated ceiling")
    dist = Counter()
    for r in records:
        for c in r["claims"]:
            v = c["verdict"]
            if c["selected_score"] < calibrated_ceiling and v in {
                Verdict.SUPPORTED.value, Verdict.CONTRADICTED.value
            }:
                v = Verdict.RETRIEVAL_BELOW_CONFIDENCE.value
            dist[v] += 1
    for name, count in sorted(dist.items()):
        print(f"  {name:30} {count}")

    print()
    print(f"evidence chain verifies    {log.verify()}")
    print(f"spans written              {len(log.spans)}")
    print(f"total tokens               {tokens}")
    print(f"estimated cost usd         {cost:.4f}")
    per_call = cost / max(1, len(records)) * 25
    print(f"projected cost per 100 call campaign  {per_call * 100:.2f} usd "
          f"(25 turns per call)")


def band(detection: float) -> str:
    if detection > 0.90:
        return "above 90 percent, commercially viable as scoped"
    if detection >= 0.80:
        return "80 to 90 percent, viable with human review in the loop"
    if detection >= 0.70:
        return "70 to 80 percent, retrieval is the bottleneck"
    return "below 70 percent, reconsider the corpus or restructure the claim approach"


if __name__ == "__main__":
    raise SystemExit(main())
