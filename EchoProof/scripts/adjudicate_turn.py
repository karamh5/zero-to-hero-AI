"""Adjudicate a single agent turn and print the trace.

The smallest end-to-end exercise of the pipeline: one turn in, verdicts with
citations out, evidence chain written and verified.

Run:
    python scripts/adjudicate_turn.py --text "Your balance is $4,500."
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import RUNS_DIR, load_settings  # noqa: E402
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

DEFAULT_TURN = (
    "Hello, this is Jordan calling from Meridian Recovery. Your outstanding "
    "balance is $4,500, and if you pay the full amount today I can have this "
    "removed from your credit report entirely."
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Adjudicate one agent turn.")
    parser.add_argument("--text", default=DEFAULT_TURN)
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--run-id", default="smoke")
    parser.add_argument("--call-date", default="2026-08-12")
    args = parser.parse_args()

    settings = load_settings()
    pack = load_policy_pack(args.pack)
    thresholds = load_criteria("thresholds")["thresholds"]
    criteria = load_criteria("criteria")

    config = RetrievalConfig(
        floor=thresholds["floor"],
        ceiling=thresholds["ceiling"],
        conflict_margin=thresholds["conflict_margin"],
        top_k=thresholds["top_k"],
    )

    retriever = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    retriever.index(build_chunks(pack.sections))

    obligations = {s.section_id: s.obligation_type.value for s in pack.sections}
    log = EvidenceLog(run_id=args.run_id)

    result = adjudicate_turn(
        client=ModelClient(settings),
        retriever=retriever,
        config=config,
        transcript=args.text,
        turn_id="t01",
        call_date=date.fromisoformat(args.call_date),
        log=log,
        criteria=criteria,
        section_obligations=obligations,
    )

    print(f"transcript ({len(args.text)} chars)")
    print(f"  {args.text}")
    print()
    print(f"claims extracted     {len(result.claims)}")
    print(f"claims rejected      {len(result.rejected_claims)}")
    for rejected in result.rejected_claims:
        print(f"    rejected {rejected['claim_id']}: {rejected['reason']}")
    print()

    for judgement in result.judgements:
        adjudication = judgement.adjudication
        claim = next(c for c in result.claims if c.claim_id == adjudication.claim_id)
        span = claim.text(args.text)
        print(f"[{adjudication.claim_id}] {claim.claim_type.value}")
        print(f"  span      [{claim.char_start}:{claim.char_end}] {span!r}")
        print(f"  verdict   {adjudication.verdict.value}")
        print(f"  section   {adjudication.section_id or '-'}")
        print(f"  by        {adjudication.decided_by}")
        print(f"  score     {judgement.inputs.retrieval_top_score:.3f}"
              f"  floor={judgement.inputs.cleared_floor}"
              f"  ceiling={judgement.inputs.cleared_ceiling}")
        print(f"  rationale {adjudication.rationale}")
        print()

    path = log.write(RUNS_DIR / args.run_id / "evidence.jsonl")
    reloaded = EvidenceLog.read(path)

    print(f"spans written        {len(log.spans)}")
    print(f"chain head           {log.head[:16]}")
    print(f"chain verifies       {log.verify()}")
    print(f"reloaded head match  {reloaded.head == log.head}")
    print(f"tokens               {result.total_tokens}")
    print(f"estimated cost usd   {result.cost_usd:.6f}")
    print(f"evidence log         {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
