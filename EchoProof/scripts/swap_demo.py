"""Pack swap demonstration (SPEC section 1).

Adjudicate against a corpus that is not Regulation F, is not debt collection,
and numbers its provisions differently, using the same engine.

The engine takes no argument saying which industry it is in. The only thing that
changes between this run and a Regulation F run is which pack directory is
loaded, which is exactly the claim CLAUDE.md makes and this script exists to
test rather than assert.

Run:
    python scripts/swap_demo.py --pack synth_telecom --fixtures synth_telecom.jsonl
    python scripts/swap_demo.py --pack reg_f --fixtures fixtures.jsonl --limit 3
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import FIXTURES_DIR, POLICY_DIR, RUNS_DIR, load_settings  # noqa: E402
from core.packs import (  # noqa: E402
    load_criteria,
    load_policy_pack,
    policy_index_dir,
)
from engine.evidence import EvidenceLog  # noqa: E402
from engine.pipeline import adjudicate_turn  # noqa: E402
from engine.retrieval.base import RetrievalConfig, is_within  # noqa: E402
from engine.retrieval.cache import CachingRetriever  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402
from models.client import ModelClient  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Pack swap demonstration.")
    parser.add_argument("--pack", default="synth_telecom")
    parser.add_argument("--fixtures", default="synth_telecom.jsonl")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    run_id = args.run_id or f"swap-{args.pack}"
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

    print(f"pack                 {pack.pack_id}")
    print(f"citation             {pack.citation}")
    print(f"sections             {len(pack.sections)}")
    print(f"id separators        {pack.hierarchy_separators}")
    print(f"policy_pack_version  {pack.version}")
    print()

    chunks = build_chunks(pack.sections)
    inner = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    inner.index(chunks)
    retriever = CachingRetriever(
        inner, POLICY_DIR / args.pack / "retrieval_cache", pack.version
    )
    obligations = {s.section_id: s.obligation_type.value for s in pack.sections}
    client = ModelClient(settings)
    log = EvidenceLog(run_id=run_id)

    rows = [
        json.loads(line)
        for line in (FIXTURES_DIR / args.fixtures).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        rows = rows[: args.limit]

    correct_citations = 0
    detected = 0
    violations = [r for r in rows if r["category"] == "seeded_violation"]
    false_positives = 0
    results = []

    for row in rows:
        result = adjudicate_turn(
            client=client,
            retriever=retriever,
            config=config,
            transcript=row["turn_text"],
            turn_id=row["fixture_id"],
            call_date=date.today(),
            log=log,
            criteria=criteria,
            section_obligations=obligations,
        )
        expected = row["ground_truth"]["section_id"]
        findings = result.findings
        cited = [j.adjudication.section_id for j in findings]
        hit = any(
            is_within(expected, c, pack.hierarchy_separators) for c in cited if c
        )

        if row["category"] == "seeded_violation":
            if findings:
                detected += 1
            if hit:
                correct_citations += 1
        elif findings:
            false_positives += 1

        marker = "FINDING" if findings else "       "
        print(f"{marker} {row['fixture_id']:8} {row['category']:17} "
              f"expected {expected:10} got {cited or '-'}")
        results.append(
            {
                "fixture_id": row["fixture_id"],
                "expected": expected,
                "cited": cited,
                "citation_correct": hit,
            }
        )

    path = log.write(RUNS_DIR / run_id / "evidence.jsonl")
    (RUNS_DIR / run_id / "swap.json").write_text(
        json.dumps({"pack": pack.pack_id, "results": results}, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"seeded violations    {len(violations)}")
    print(f"detected             {detected}")
    print(f"cited correctly      {correct_citations}")
    print(f"false positives      {false_positives}")
    print(f"chain verifies       {log.verify()}")
    print(f"evidence             {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
