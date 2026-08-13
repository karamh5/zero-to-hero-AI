"""Start the EchoProof capture proxy.

Point a voice agent's LLM base_url at this and every agent turn is adjudicated
out of band, with no change to the agent and no manual feed.

Run:
    python scripts/run_proxy.py
    python scripts/run_proxy.py --no-adjudicate    # measure proxy cost alone
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

from adapter.capture import CaptureQueue, CapturedTurn, record_turn  # noqa: E402
from adapter.proxy import create_app  # noqa: E402
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


def build_handler(run_id: str, pack_id: str):  # type: ignore[no-untyped-def]
    """Load the adjudication stack once and return a per-turn handler."""
    settings = load_settings()
    pack = load_policy_pack(pack_id)
    criteria = load_criteria("criteria")
    thresholds = load_criteria("thresholds")["thresholds"]

    config = RetrievalConfig(
        floor=float(thresholds["floor"]),
        # The operating point measured on the fixtures in Phase 1, not the value
        # calibrated on retrieval pairs. The pair-calibrated ceiling of 0.740
        # exceeds every score observed in a fixture run and would abstain on
        # everything.
        ceiling=0.548,
        conflict_margin=float(thresholds["conflict_margin"]),
        top_k=int(thresholds.get("top_k", 50)),
        first_stage_k=int(thresholds.get("first_stage_k", 50)),
        rerank_k=int(thresholds.get("rerank_k", 50)),
        judge_candidates=int(thresholds.get("judge_candidates", 10)),
    )

    retriever = LocalHybridRetriever(
        cache_dir=policy_index_dir(pack_id), reranker=CrossEncoderReranker()
    )
    retriever.index(build_chunks(pack.sections))
    obligations = {s.section_id: s.obligation_type.value for s in pack.sections}
    client = ModelClient(settings)
    log = EvidenceLog(run_id=run_id)
    out_path = RUNS_DIR / run_id / "evidence.jsonl"

    def handler(turn: CapturedTurn) -> None:
        record_turn(log, turn)
        result = adjudicate_turn(
            client=client,
            retriever=retriever,
            config=config,
            transcript=turn.transcript,
            turn_id=turn.turn_id,
            call_date=date.fromisoformat(turn.call_date),
            log=log,
            criteria=criteria,
            section_obligations=obligations,
        )
        log.write(out_path)
        findings = len(result.findings)
        print(
            f"[adjudicated] {turn.turn_id} via {turn.source}: "
            f"{len(result.claims)} claim(s), {findings} finding(s), "
            f"{len(result.abstentions)} abstention(s)"
        )
        for judgement in result.findings:
            print(
                f"    FINDING {judgement.adjudication.verdict.value} "
                f"@ {judgement.adjudication.section_id}"
            )

    return handler, log, out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the EchoProof capture proxy.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8077)
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--run-id", default="proxy-live")
    parser.add_argument(
        "--no-adjudicate",
        action="store_true",
        help="capture without judging, to measure proxy cost in isolation",
    )
    args = parser.parse_args()

    if args.no_adjudicate:
        seen: list[str] = []

        def handler(turn: CapturedTurn) -> None:
            seen.append(turn.turn_id)
            print(f"[captured] {turn.turn_id} ({len(turn.transcript)} chars)")

        capture = CaptureQueue(handler=handler)
    else:
        print("loading adjudication stack (embeddings and reranker) ...")
        handler, _log, out_path = build_handler(args.run_id, args.pack)
        capture = CaptureQueue(handler=handler)
        print(f"evidence will be written to {out_path}")

    capture.start()
    app = create_app(load_settings(), capture)
    print(f"proxy listening on http://{args.host}:{args.port}")
    print("point an agent's base_url at it, or run scripts/drive_proxy.py")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
