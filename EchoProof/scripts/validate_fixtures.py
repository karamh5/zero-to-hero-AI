"""Structural validation of the fixture set.

Checks only what can be checked without scoring: schema, uniqueness, split
disjointness, and that every cited section actually exists in the policy pack.
A ground_truth section_id that does not exist in the corpus makes an item
unscoreable, and finding that out during a scoring run wastes the run.

This reads the held-out file's IDENTIFIERS AND SECTIONS ONLY. It never prints
held-out turn text and never scores anything, so the split stays sealed per
CLAUDE.md decision 10.

Run:
    python scripts/validate_fixtures.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import FIXTURES_DIR  # noqa: E402
from core.contracts import Verdict  # noqa: E402
from core.packs import load_policy_pack  # noqa: E402

VALID_CATEGORIES = {"seeded_violation", "hard_negative", "easy_negative"}


def load(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    pack = load_policy_pack("reg_f")
    known = {s.section_id for s in pack.sections}

    dev = load(FIXTURES_DIR / "fixtures.jsonl")
    held = load(FIXTURES_DIR / "heldout.jsonl")
    problems: list[str] = []

    for label, rows in (("dev", dev), ("heldout", held)):
        for row in rows:
            fid = row.get("fixture_id", "<missing id>")
            if row.get("category") not in VALID_CATEGORIES:
                problems.append(f"{label} {fid}: bad category {row.get('category')!r}")
            if not str(row.get("turn_text", "")).strip():
                problems.append(f"{label} {fid}: empty turn_text")

            truth = row.get("ground_truth") or {}
            try:
                verdict = Verdict(truth.get("verdict"))
            except ValueError:
                problems.append(f"{label} {fid}: bad verdict {truth.get('verdict')!r}")
                continue

            section = truth.get("section_id")
            if verdict in (Verdict.SUPPORTED, Verdict.CONTRADICTED):
                if not section:
                    problems.append(f"{label} {fid}: {verdict.value} needs a section_id")
                elif section not in known:
                    problems.append(
                        f"{label} {fid}: section {section} is not in the policy pack"
                    )
            elif section is not None:
                problems.append(
                    f"{label} {fid}: {verdict.value} should not name a section"
                )

    dev_ids = [r["fixture_id"] for r in dev]
    held_ids = [r["fixture_id"] for r in held]
    overlap = set(dev_ids) & set(held_ids)
    if overlap:
        problems.append(f"split overlap, held-out is contaminated: {sorted(overlap)}")

    for label, ids in (("dev", dev_ids), ("heldout", held_ids)):
        dupes = [i for i, n in Counter(ids).items() if n > 1]
        if dupes:
            problems.append(f"{label}: duplicate fixture_ids {dupes}")

    print(f"policy pack sections   {len(known)}")
    print(f"development items      {len(dev)}")
    print(f"held-out items         {len(held)}  (sealed, not scored)")
    print(f"total                  {len(dev) + len(held)}")
    print()
    print("category distribution")
    for label, rows in (("dev", dev), ("heldout", held)):
        counts = Counter(r.get("category") for r in rows)
        line = "  ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        print(f"  {label:9} {line}")
    print()
    print("verdict distribution")
    for label, rows in (("dev", dev), ("heldout", held)):
        counts = Counter((r.get("ground_truth") or {}).get("verdict") for r in rows)
        line = "  ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        print(f"  {label:9} {line}")
    print()
    hard_negatives = sum(1 for r in dev if r.get("category") == "hard_negative")
    print(f"false positive denominator (dev hard negatives) {hard_negatives}")
    print(
        f"one false positive therefore costs {1 / hard_negatives:.3f} on the rate, "
        "against a 0.02 target"
    )
    print()
    distinct = {
        (r.get("ground_truth") or {}).get("section_id")
        for r in dev + held
        if (r.get("ground_truth") or {}).get("section_id")
    }
    print(f"distinct sections exercised {len(distinct)} of {len(known)} in the corpus")

    print()
    if problems:
        print(f"FAILED with {len(problems)} problem(s):")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("PASSED: schema, verdicts, section references, uniqueness, split disjoint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
