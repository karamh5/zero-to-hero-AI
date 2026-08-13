"""Score a completed blind labelling sheet against the judge (SPEC section 11).

Run:
    python scripts/score_agreement.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import PROJECT_ROOT  # noqa: E402
from engine.agreement import score_agreement  # noqa: E402

VALID = {
    "supported",
    "contradicted",
    "no_governing_rule",
    "retrieval_below_confidence",
    "conflicting_sections",
}

ITEM_RE = re.compile(r"`([^`\n]+:[^`\n]+)`")
VERDICT_RE = re.compile(r"^VERDICT:\s*(.*)$", re.MULTILINE)


def parse_sheet(text: str) -> tuple[dict[str, str], list[str]]:
    """Read claim_id and verdict pairs out of the filled sheet."""
    blocks = text.split("## Item ")[1:]
    labels: dict[str, str] = {}
    problems: list[str] = []

    for block in blocks:
        id_match = ITEM_RE.search(block)
        verdict_match = VERDICT_RE.search(block)
        if not id_match:
            continue
        claim_id = id_match.group(1).strip()
        raw = (verdict_match.group(1).strip() if verdict_match else "").lower()
        raw = raw.strip("`* ")

        if not raw:
            problems.append(f"{claim_id}: no verdict written")
            continue
        if raw not in VALID:
            problems.append(f"{claim_id}: {raw!r} is not one of the five verdicts")
            continue
        labels[claim_id] = raw

    return labels, problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Score judge-human agreement.")
    parser.add_argument("--sheet", default=str(PROJECT_ROOT / "labels" / "blind_sheet.md"))
    parser.add_argument("--key", default=str(PROJECT_ROOT / "labels" / "answer_key.jsonl"))
    parser.add_argument("--floor", type=float, default=0.85)
    args = parser.parse_args()

    sheet_path, key_path = Path(args.sheet), Path(args.key)
    if not sheet_path.exists() or not key_path.exists():
        print("sheet or answer key missing; run scripts/build_label_sheet.py first")
        return 1

    human, problems = parse_sheet(sheet_path.read_text(encoding="utf-8"))
    judge = {
        json.loads(line)["claim_id"]: json.loads(line)["judge_verdict"]
        for line in key_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    if problems:
        print(f"{len(problems)} item(s) could not be read:")
        for problem in problems[:10]:
            print(f"  {problem}")
        print()

    if not human:
        print("No verdicts found in the sheet. Nothing to score.")
        print("Judge-human agreement is NOT ESTABLISHED. The report must say so")
        print("rather than substituting a number.")
        return 2

    result = score_agreement(judge, human, floor=args.floor)

    print(f"items labelled      {result.total} of {len(judge)}")
    print(f"agreements          {result.matched}")
    print(f"raw agreement       {result.raw_agreement:.3f}")
    print(f"cohens kappa        {result.kappa:.3f}")
    print(f"floor               {result.floor:.2f}")
    print(f"meets floor         {result.meets_floor}")
    print()
    print(result.positioning)

    if result.by_verdict:
        print()
        print("by judge verdict")
        for verdict, counts in sorted(result.by_verdict.items()):
            total = counts["agreed"] + counts["disagreed"]
            rate = counts["agreed"] / total if total else 0.0
            print(f"  {verdict:30} {counts['agreed']}/{total} ({rate:.2f})")

    if result.disagreements:
        print()
        print("disagreements")
        for row in result.disagreements:
            print(f"  {row['claim_id']:34} judge={row['judge']:28} human={row['human']}")

    out = PROJECT_ROOT / "labels" / "agreement.json"
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    print()
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
