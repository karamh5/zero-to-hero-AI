"""Run every prepared conversation and record what actually happened.

The demo library is only useful if its stated outcomes are the outcomes the
system really produces. This script adjudicates each conversation against its
corpus and writes the observed result back to
`packs/conversation/<pack>/verified.json`.

Nothing here edits the conversations themselves. If a conversation was authored
expecting `contradicted` and produces an abstention, that is what gets recorded,
and the UI shows the recorded outcome rather than the authored intent. A demo
library that claims outcomes it does not produce is worse than no library.

Run:
    python scripts/verify_conversations.py --pack reg_f
    python scripts/verify_conversations.py --pack reg_f --only rf-03-timebarred
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import PACKS_DIR, RUNS_DIR, load_settings  # noqa: E402
from core.packs import load_criteria, load_policy_pack, policy_index_dir  # noqa: E402
from engine.conversation import adjudicate_conversation, parse_turns  # noqa: E402
from engine.evidence import EvidenceLog  # noqa: E402
from engine.retrieval.base import RetrievalConfig  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402
from models.client import ModelClient  # noqa: E402

# The operating point the published numbers were measured at.
OPERATING_CEILING = 0.548


def load_conversations(pack_id: str) -> list[dict[str, Any]]:
    path = PACKS_DIR / "conversation" / pack_id / "conversations.jsonl"
    if not path.exists():
        raise SystemExit(f"no conversation pack at {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify prepared conversations.")
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--only", default=None, help="verify one conversation id")
    args = parser.parse_args()

    settings = load_settings()
    pack = load_policy_pack(args.pack)
    criteria = load_criteria("criteria")
    thresholds = load_criteria("thresholds")["thresholds"]

    config = RetrievalConfig(
        floor=float(thresholds["floor"]),
        ceiling=OPERATING_CEILING,
        conflict_margin=float(thresholds["conflict_margin"]),
        top_k=int(thresholds.get("top_k", 50)),
        first_stage_k=int(thresholds.get("first_stage_k", 50)),
        rerank_k=int(thresholds.get("rerank_k", 50)),
        judge_candidates=int(thresholds.get("judge_candidates", 10)),
    )

    print("loading the adjudication stack ...")
    retriever = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    retriever.index(build_chunks(pack.sections))
    obligations = {s.section_id: s.obligation_type.value for s in pack.sections}
    client = ModelClient(settings)

    conversations = load_conversations(args.pack)
    if args.only:
        conversations = [c for c in conversations if c["conversation_id"] == args.only]
        if not conversations:
            raise SystemExit(f"no conversation {args.only} in pack {args.pack}")

    verified: dict[str, Any] = {}
    out_path = PACKS_DIR / "conversation" / args.pack / "verified.json"
    if out_path.exists():
        verified = json.loads(out_path.read_text(encoding="utf-8"))

    for index, entry in enumerate(conversations, start=1):
        conversation_id = entry["conversation_id"]
        print(f"\n[{index}/{len(conversations)}] {conversation_id}  {entry['title']}")
        turns = parse_turns(entry["turns"])
        run_id = f"prepared-{args.pack}-{conversation_id}"
        log = EvidenceLog(run_id=run_id)

        result = adjudicate_conversation(
            client=client,
            retriever=retriever,
            config=config,
            turns=turns,
            conversation_id=conversation_id,
            title=entry["title"],
            call_date=date.today(),
            log=log,
            criteria=criteria,
            section_obligations=obligations,
            expectations=entry.get("deterministic") or {},
        )
        log.write(RUNS_DIR / run_id / "evidence.jsonl")

        verdicts: list[dict[str, Any]] = []
        for turn_result in result.turn_results:
            for judgement in turn_result.judgements:
                verdicts.append(
                    {
                        "claim_id": judgement.adjudication.claim_id,
                        "verdict": judgement.adjudication.verdict.value,
                        "section_id": judgement.adjudication.section_id,
                        "decided_by": judgement.adjudication.decided_by,
                    }
                )

        counts: dict[str, int] = {}
        for item in verdicts:
            counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1

        headline = (
            "contradicted"
            if counts.get("contradicted")
            else "supported"
            if counts.get("supported")
            else max(counts, key=lambda k: counts[k])
            if counts
            else "no_claims"
        )

        verified[conversation_id] = {
            "conversation_id": conversation_id,
            "title": entry["title"],
            "authored_category": entry.get("category"),
            "observed_headline": headline,
            "matches_authored": headline == entry.get("category"),
            "verdict_counts": counts,
            "claims": len(verdicts),
            "agent_turns": result.agent_turn_count,
            "customer_turns_skipped": result.customer_turn_count,
            "findings": [v for v in verdicts if v["verdict"] == "contradicted"],
            "verdicts": verdicts,
            "run_id": run_id,
            "cost_usd": round(result.cost_usd, 6),
            "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

        flag = "MATCHES" if headline == entry.get("category") else "DIFFERS FROM AUTHORED"
        print(f"    claims {len(verdicts)}  agent turns {result.agent_turn_count} "
              f"  customer turns skipped {result.customer_turn_count}")
        print(f"    observed {headline}  ({entry.get('category')} authored)  {flag}")
        for item in verdicts:
            print(f"      {item['claim_id']:28} {item['verdict']:28} {item['section_id']}")

        out_path.write_text(
            json.dumps(verified, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    matched = sum(1 for v in verified.values() if v["matches_authored"])
    print(f"\n{matched}/{len(verified)} conversations produced their authored outcome")
    print(f"written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
