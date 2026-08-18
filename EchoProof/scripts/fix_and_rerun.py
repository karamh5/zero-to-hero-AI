"""Fix-and-rerun loop (SPEC section 12).

Run a scenario, apply a fix to the agent, run the same scenario with the same
seed, and record which findings closed, persisted, or are new.

The fix is applied to the AGENT, not to EchoProof. That is the loop a client
actually runs: EchoProof flags an issue, the agent vendor changes the agent, and
the rerun shows whether the change worked. Changing EchoProof instead would also
reopen a scored pipeline, which ARCHITECTURE.md decision 9 forbids for a run whose
numbers are already reported.

The corrected prompt lives in the scenario pack as `fixed_agent_system_prompt`,
so the fix is data rather than a code change.

Run:
    python scripts/fix_and_rerun.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import POLICY_DIR, RUNS_DIR, load_settings  # noqa: E402
from core.packs import (  # noqa: E402
    load_criteria,
    load_personas,
    load_policy_pack,
    load_scenarios,
    policy_index_dir,
)
from engine.evidence import EvidenceLog  # noqa: E402
from engine.rerun import diff_runs  # noqa: E402
from engine.retrieval.base import RetrievalConfig  # noqa: E402
from engine.retrieval.cache import CachingRetriever  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402
from engine.runner import run_call  # noqa: E402
from models.client import ModelClient  # noqa: E402

SEED = 20260812


def findings_of(call: Any) -> list[dict[str, Any]]:
    return [
        {
            "claim_id": j.adjudication.claim_id,
            "section_id": j.adjudication.section_id,
            "verdict": j.adjudication.verdict.value,
            "rationale": j.adjudication.rationale,
        }
        for j in call.findings
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix and rerun one scenario.")
    parser.add_argument("--scenario", default="sc-01-cease")
    parser.add_argument("--run-id", default="fix-and-rerun")
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--turns", type=int, default=3)
    args = parser.parse_args()

    settings = load_settings()
    pack = load_policy_pack(args.pack)
    criteria = load_criteria("criteria")
    thresholds = load_criteria("thresholds")["thresholds"]

    scenario = next(
        s for s in load_scenarios() if s["scenario_id"] == args.scenario
    )
    persona = load_personas()[scenario["persona_id"]]
    if not scenario.get("fixed_agent_system_prompt"):
        print(f"{args.scenario} has no fixed_agent_system_prompt in the pack")
        return 1

    config = RetrievalConfig(
        floor=float(thresholds["floor"]),
        ceiling=0.548,
        conflict_margin=float(thresholds["conflict_margin"]),
        top_k=int(thresholds.get("top_k", 50)),
        first_stage_k=int(thresholds.get("first_stage_k", 50)),
        rerank_k=int(thresholds.get("rerank_k", 50)),
        judge_candidates=int(thresholds.get("judge_candidates", 10)),
    )

    print("loading retrieval stack ...")
    inner = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    inner.index(build_chunks(pack.sections))
    retriever = CachingRetriever(
        inner, POLICY_DIR / args.pack / "retrieval_cache", pack.version
    )
    obligations = {s.section_id: s.obligation_type.value for s in pack.sections}
    client = ModelClient(settings)
    run_dir = RUNS_DIR / args.run_id
    log = EvidenceLog(run_id=args.run_id)

    print(f"\n=== BEFORE: {args.scenario} with the original agent prompt ===")
    before = run_call(
        client=client, retriever=retriever, config=config, scenario=scenario,
        persona=persona, run_index=1, seed=SEED, log=log, criteria=criteria,
        obligations=obligations, turns=args.turns,
    )
    before_findings = findings_of(before)
    for turn in before.agent_turns:
        print(f"  agent: {turn[:110]}")
    print(f"  findings: {len(before_findings)}")
    for f in before_findings:
        print(f"    {f['verdict']} @ {f['section_id']}")

    # The same scenario with the corrected agent. Same persona, same seed, same
    # judge, same thresholds: the only thing that changed is the agent.
    fixed_scenario = dict(scenario)
    fixed_scenario["agent_system_prompt"] = scenario["fixed_agent_system_prompt"]

    print(f"\n=== AFTER: same scenario and seed, agent prompt fixed ===")
    after = run_call(
        client=client, retriever=retriever, config=config, scenario=fixed_scenario,
        persona=persona, run_index=2, seed=SEED, log=log, criteria=criteria,
        obligations=obligations, turns=args.turns,
    )
    after_findings = findings_of(after)
    for turn in after.agent_turns:
        print(f"  agent: {turn[:110]}")
    print(f"  findings: {len(after_findings)}")
    for f in after_findings:
        print(f"    {f['verdict']} @ {f['section_id']}")

    delta = diff_runs(args.scenario, SEED, before_findings, after_findings)
    log.append("rerun.delta", delta.to_dict())
    log.write(run_dir / "evidence.jsonl")

    payload = {
        **delta.to_dict(),
        "before_agent_turns": before.agent_turns,
        "after_agent_turns": after.agent_turns,
        "before_findings": before_findings,
        "after_findings": after_findings,
    }
    (run_dir / "rerun.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print()
    print("=" * 70)
    print("FIX AND RERUN DELTA")
    print("=" * 70)
    print(f"findings before  {delta.before_count}")
    print(f"findings after   {delta.after_count}")
    print(f"closed           {[k.section_id for k in delta.closed] or 'none'}")
    print(f"persisted        {[k.section_id for k in delta.persisted] or 'none'}")
    print(f"new              {[k.section_id for k in delta.new] or 'none'}")
    print(f"improved         {delta.improved}")
    print(f"chain verifies   {log.verify()}")
    print(f"written          {run_dir / 'rerun.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
