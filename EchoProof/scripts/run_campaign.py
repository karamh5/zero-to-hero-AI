"""Run the campaign: six scenarios, three runs each (SPEC section 10).

Run:
    python scripts/run_campaign.py
    python scripts/run_campaign.py --runs 1 --turns 2     # quick smoke
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

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
from engine.retrieval.base import RetrievalConfig  # noqa: E402
from engine.retrieval.cache import CachingRetriever  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402
from engine.runner import ScenarioResult, aggregate_policy_gaps, run_call  # noqa: E402
from models.client import ModelClient  # noqa: E402

BASE_SEED = 20260812


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the EchoProof campaign.")
    parser.add_argument("--run-id", default="campaign")
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument("--scenarios", default="", help="comma separated ids to limit to")
    args = parser.parse_args()

    settings = load_settings()
    pack = load_policy_pack(args.pack)
    criteria = load_criteria("criteria")
    thresholds = load_criteria("thresholds")["thresholds"]
    scenarios = load_scenarios()
    personas = load_personas()

    if args.scenarios:
        wanted = {s.strip() for s in args.scenarios.split(",")}
        scenarios = [s for s in scenarios if s["scenario_id"] in wanted]

    config = RetrievalConfig(
        floor=float(thresholds["floor"]),
        # Phase 1's measured operating point at 2 percent false positives.
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
    log = EvidenceLog(run_id=args.run_id)
    run_dir = RUNS_DIR / args.run_id

    results: list[ScenarioResult] = []
    started = time.perf_counter()
    total_cost = 0.0

    for scenario in scenarios:
        persona = personas[scenario["persona_id"]]
        scenario_result = ScenarioResult(
            scenario_id=scenario["scenario_id"],
            persona_id=persona["persona_id"],
            expected_section_id=(scenario.get("ground_truth") or {}).get("section_id"),
            is_control=scenario.get("seeded_violation") is None,
        )
        print(f"\n=== {scenario['scenario_id']}  persona {persona['persona_id']} ===")

        for run_index in range(1, args.runs + 1):
            call = run_call(
                client=client,
                retriever=retriever,
                config=config,
                scenario=scenario,
                persona=persona,
                run_index=run_index,
                # Same seed for every run of a scenario, per SPEC section 10.
                seed=BASE_SEED,
                log=log,
                criteria=criteria,
                obligations=obligations,
                turns=args.turns,
            )
            scenario_result.calls.append(call)
            total_cost += call.cost_usd

            caught = call.caught(scenario_result.expected_section_id)
            state = "valid" if call.valid else "DRIFTED (retained)"
            print(f"  run {run_index}: {len(call.findings)} finding(s), "
                  f"caught={caught}, {state}")
            if not call.valid and call.drift is not None:
                for reason in call.drift.reasons[:2]:
                    print(f"      drift: {reason}")

        results.append(scenario_result)

    elapsed = time.perf_counter() - started
    log.write(run_dir / "evidence.jsonl")

    print()
    print("=" * 78)
    print("CAMPAIGN RESULTS")
    print("=" * 78)
    print(f"{'scenario':<20} {'persona':<16} {'caught':<10} {'pass@3':<8} "
          f"{'pass^3':<8} {'drift':<6}")
    for r in results:
        flags = "".join("Y" if f else "n" for f in r.caught_flags) or "-"
        print(f"{r.scenario_id:<20} {r.persona_id:<16} {flags:<10} "
              f"{str(r.pass_at_3):<8} {str(r.pass_cubed):<8} {r.drifted:<6}")

    graded = [r for r in results if not r.is_control]
    control = [r for r in results if r.is_control]
    print()
    print(f"scenarios with a seeded violation  {len(graded)}")
    print(f"  pass@3   {sum(r.pass_at_3 for r in graded)}/{len(graded)}")
    print(f"  pass^3   {sum(r.pass_cubed for r in graded)}/{len(graded)}")
    for r in control:
        print(f"control scenario {r.scenario_id}: "
              f"{r.false_positive_calls}/{len(r.valid_calls)} call(s) produced a finding")

    gaps = aggregate_policy_gaps(results)
    print()
    print(f"policy gap list entries {len(gaps)}")
    for gap in gaps[:5]:
        print(f"  {gap['scenario_id']}: {gap['claim'][:90]}")

    drifted = sum(r.drifted for r in results)
    print()
    print(f"calls run       {sum(len(r.calls) for r in results)}")
    print(f"calls drifted   {drifted} (retained, not discarded)")
    print(f"retrieval cache {retriever.stats()}")
    print(f"wall clock      {elapsed / 60:.1f} min")
    print(f"cost            ${total_cost:.4f}")
    print(f"spans           {len(log.spans)}")
    print(f"chain verifies  {log.verify()}")

    summary = {
        "run_id": args.run_id,
        "runs_per_scenario": args.runs,
        "turns_per_call": args.turns,
        "scenarios": [
            {
                "scenario_id": r.scenario_id,
                "persona_id": r.persona_id,
                "expected_section_id": r.expected_section_id,
                "is_control": r.is_control,
                "caught": r.caught_flags,
                "pass_at_3": r.pass_at_3,
                "pass_cubed": r.pass_cubed,
                "drifted": r.drifted,
                "false_positive_calls": r.false_positive_calls,
            }
            for r in results
        ],
        "policy_gaps": gaps,
        "cache": retriever.stats(),
        "cost_usd": round(total_cost, 4),
        "wall_clock_min": round(elapsed / 60, 2),
    }
    (run_dir / "campaign.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"summary         {run_dir / 'campaign.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
