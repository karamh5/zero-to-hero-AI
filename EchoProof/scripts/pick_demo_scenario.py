"""Choose the demo shortlist from recorded evidence, not from taste.

The single worst thing that can happen to this demo is a rule being chosen
because it felt good in rehearsal. So the shortlist is a query over every
evidence log already on disk: which rules has EchoProof actually produced a
finding against, how often, and across how many separate runs.

Measured detection is 0.348 at the operating point, so a rule picked freely on
stage fails roughly two times in three. Offering the observer a genuine choice
among rules with a recorded track record keeps the moment honest while removing
most of that risk. The slide says the shortlist came from measured runs.

Run:
    python scripts/pick_demo_scenario.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import PROJECT_ROOT, RUNS_DIR  # noqa: E402
from core.packs import load_policy_pack  # noqa: E402
from engine.evidence import SPAN_JUDGE_RULE, EvidenceLog  # noqa: E402

CONTRADICTED = "contradicted"


def mine_runs(run_dirs: list[Path]) -> dict[str, dict[str, Any]]:
    """Count findings per cited section across every recorded run."""
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"findings": 0, "runs": set(), "claims": []}
    )

    for run_dir in run_dirs:
        path = run_dir / "evidence.jsonl"
        if not path.exists():
            continue
        try:
            log = EvidenceLog.read(path)
        except Exception as exc:  # noqa: BLE001 - a bad log skips, never blocks
            print(f"  skipped {run_dir.name}: {exc}")
            continue

        for span in log.spans:
            if span.span_type != SPAN_JUDGE_RULE:
                continue
            payload = span.payload
            if payload.get("verdict") != CONTRADICTED:
                continue
            section_id = payload.get("section_id")
            if not section_id:
                continue
            entry = stats[str(section_id)]
            entry["findings"] += 1
            entry["runs"].add(run_dir.name)
            claim = str(payload.get("claim_in", ""))[:110]
            if claim and claim not in entry["claims"]:
                entry["claims"].append(claim)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Pick the demo shortlist.")
    parser.add_argument("--top", type=int, default=4)
    parser.add_argument("--min-runs", type=int, default=1)
    args = parser.parse_args()

    run_dirs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    print(f"mining {len(run_dirs)} recorded run(s)")
    stats = mine_runs(run_dirs)
    if not stats:
        print("no findings recorded in any run; cannot build a shortlist")
        return 1

    pack = load_policy_pack("reg_f")
    text_by_id = {s.section_id: s for s in pack.sections}

    ranked = sorted(
        stats.items(),
        # Distinct runs first, then raw finding count. A rule caught once in
        # each of three separate runs is a far safer stage bet than one caught
        # three times inside a single run, which may be one lucky transcript.
        key=lambda kv: (len(kv[1]["runs"]), kv[1]["findings"]),
        reverse=True,
    )

    print()
    print(f"{'section':<26} {'findings':<9} {'runs':<6} rule")
    for section_id, entry in ranked[:15]:
        section = text_by_id.get(section_id)
        heading = (section.heading if section else "")[:46]
        print(f"{section_id:<26} {entry['findings']:<9} {len(entry['runs']):<6} {heading}")

    shortlist = []
    for section_id, entry in ranked:
        if len(entry["runs"]) < args.min_runs:
            continue
        section = text_by_id.get(section_id)
        if section is None:
            continue
        shortlist.append(
            {
                "section_id": section_id,
                "heading": section.heading,
                "rule_text": section.verbatim_text[:400],
                "obligation_type": section.obligation_type.value,
                "observed_findings": entry["findings"],
                "observed_in_runs": sorted(entry["runs"]),
                "example_claims": entry["claims"][:3],
            }
        )
        if len(shortlist) >= args.top:
            break

    out_dir = PROJECT_ROOT / "demo"
    out_dir.mkdir(exist_ok=True)
    payload = {
        "note": (
            "Shortlist derived from recorded evidence logs, not chosen by hand. "
            "Each entry is a rule EchoProof produced a finding against in at "
            "least one real run. The observer picks from these on stage."
        ),
        "policy_pack_version": pack.version,
        "shortlist": shortlist,
    }
    (out_dir / "shortlist.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print()
    print(f"shortlist of {len(shortlist)}, written to {out_dir / 'shortlist.json'}")
    for entry in shortlist:
        print(f"  {entry['section_id']:<24} {entry['observed_findings']} finding(s) "
              f"across {len(entry['observed_in_runs'])} run(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
