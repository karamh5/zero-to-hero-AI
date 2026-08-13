"""Structural regression check.

Compares the deterministic parts of the system against a stored baseline: the
policy pack's shape and hash, the chunking output, the identifier schemes, and
the criteria thresholds.

**Model output is deliberately not part of the baseline.** Run to run variance
has been measured at roughly one fixture in six on Regulation F, so a baseline
containing verdicts would fail constantly and teach everyone to ignore it. A
regression check that cries wolf is worse than none, because it trains people to
skip the one time it is right.

What this does catch is the class of change that silently invalidates every
scored number: a corpus rebuild that alters the pack hash, a chunking change
that shifts what gets indexed, a threshold edit, or a pack losing its identifier
scheme.

Run:
    python scripts/regression_check.py --update    # write the baseline
    python scripts/regression_check.py             # check against it
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import PROJECT_ROOT  # noqa: E402
from core.hashing import hash_object  # noqa: E402
from core.packs import load_criteria, load_policy_pack  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402

BASELINE = PROJECT_ROOT / "tests" / "regression_baseline.json"
PACKS = ["reg_f", "synth_telecom"]


def snapshot() -> dict[str, Any]:
    """Everything deterministic that a scored number depends on."""
    state: dict[str, Any] = {"packs": {}}

    for pack_id in PACKS:
        pack = load_policy_pack(pack_id)
        chunks = build_chunks(pack.sections)
        state["packs"][pack_id] = {
            "section_count": len(pack.sections),
            "policy_pack_version": pack.version,
            "hierarchy_separators": list(pack.hierarchy_separators),
            "chunk_count": len(chunks),
            # Hash of what actually gets indexed. A chunking change that alters
            # context without changing the chunk count still moves this.
            "embed_text_digest": hash_object(
                [c.embed_text for c in chunks]
            ),
            "obligation_counts": pack.manifest.get("obligation_counts", {}),
        }

    thresholds = load_criteria("thresholds")["thresholds"]
    state["thresholds"] = {
        k: thresholds[k] for k in sorted(thresholds) if k != "note"
    }

    criteria = load_criteria("criteria")
    state["severity_labels"] = criteria.get("severity_labels", [])
    state["abstain_routing"] = {
        k: v for k, v in criteria.get("abstain_routing", {}).items() if k != "note"
    }
    return state


def diff(expected: Any, actual: Any, path: str = "") -> list[str]:
    problems: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            problems.extend(
                diff(expected.get(key), actual.get(key), f"{path}.{key}" if path else key)
            )
    elif expected != actual:
        problems.append(f"{path}: expected {expected!r}, got {actual!r}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Structural regression check.")
    parser.add_argument("--update", action="store_true", help="write the baseline")
    args = parser.parse_args()

    current = snapshot()

    if args.update or not BASELINE.exists():
        BASELINE.write_text(json.dumps(current, indent=2), encoding="utf-8")
        action = "updated" if args.update else "created"
        print(f"baseline {action}: {BASELINE}")
        for pack_id, info in current["packs"].items():
            print(f"  {pack_id:16} {info['section_count']:4} sections, "
                  f"{info['chunk_count']:4} chunks, sep={info['hierarchy_separators']}")
        return 0

    expected = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems = diff(expected, current)

    for pack_id, info in current["packs"].items():
        print(f"{pack_id:16} {info['section_count']:4} sections, "
              f"{info['chunk_count']:4} chunks, "
              f"version {str(info['policy_pack_version'])[:16]}")
    print(f"thresholds       {current['thresholds']}")
    print()

    if problems:
        print(f"REGRESSION: {len(problems)} difference(s) from the baseline")
        for problem in problems:
            print(f"  {problem}")
        print()
        print("If the change was intended, re-run with --update and say in the")
        print("commit why every previously scored number is now incomparable.")
        return 1

    print("PASS: structural state matches the baseline")
    print("Model output is not part of this baseline. Run to run variance is")
    print("roughly one fixture in six, so including verdicts would cry wolf.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
