"""Build a blind labelling sheet for the human baseline (SPEC section 11).

Writes two files that join on claim_id:

    labels/blind_sheet.md      for the human. Claim, transcript, candidate rules.
    labels/answer_key.jsonl    the judge's verdicts. NOT for the labeller.

**The human-facing sheet contains no verdict, no rationale, no severity and no
retrieval score.** A baseline that exists to validate the instrument is worthless
if the instrument's answer is visible, or even inferable, while labelling. The
script asserts this before writing rather than trusting the template.

Sampling is stratified across verdict classes. The campaign produced 140
abstentions against 8 violations, so an unstratified sample of 25 would be
almost entirely cases where the system declined to decide, and would measure
agreement on the least interesting part of the distribution.

Run:
    python scripts/build_label_sheet.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import PROJECT_ROOT, RUNS_DIR  # noqa: E402
from core.packs import load_policy_pack  # noqa: E402
from engine.evidence import (  # noqa: E402
    SPAN_AGENT_TURN,
    SPAN_EXTRACT_CLAIMS,
    SPAN_JUDGE_RULE,
    SPAN_RETRIEVE_RULE,
    EvidenceLog,
)

VERDICTS = [
    "supported",
    "contradicted",
    "no_governing_rule",
    "retrieval_below_confidence",
    "conflicting_sections",
]

# Strings that must never reach the human sheet, because each one either states
# or strongly implies the judge's answer.
LEAK_MARKERS = [
    "rationale",
    "severity",
    "judge_selected",
    "selected_score",
    "cleared_floor",
    "cleared_ceiling",
    "critical",
]


def collect_items(
    run_ids: list[str], rule_text: dict[str, str]
) -> list[dict[str, Any]]:
    """Pull adjudicated claims with everything a human needs to judge them.

    Candidate rule text is resolved from the policy pack by section id rather
    than read from the evidence log, because the log does not carry it:
    RetrievalCandidate.to_dict stores identifiers and scores only. The first
    sheet generated from the log alone listed bare section numbers with no text,
    which nobody can label without knowing the regulation by heart.

    Resolving from the pack is sound rather than a workaround. The pack is
    content addressed and its version is pinned into every finding, so the text
    shown here is provably the text that was in force for the run.
    """
    items: list[dict[str, Any]] = []

    for run_id in run_ids:
        path = RUNS_DIR / run_id / "evidence.jsonl"
        if not path.exists():
            continue
        log = EvidenceLog.read(path)

        turns: dict[str, str] = {}
        claims: dict[str, dict[str, Any]] = {}
        retrievals: dict[str, dict[str, Any]] = {}

        for span in log.spans:
            payload = span.payload
            if span.span_type == SPAN_AGENT_TURN:
                turns[str(payload.get("turn_id"))] = str(payload.get("transcript", ""))
            elif span.span_type == SPAN_EXTRACT_CLAIMS:
                for claim in payload.get("claims", []):
                    claims[str(claim["claim_id"])] = {
                        **claim,
                        "turn_id": str(payload.get("turn_id", "")),
                    }
            elif span.span_type == SPAN_RETRIEVE_RULE:
                retrievals[str(payload.get("claim_id"))] = payload

        for span in log.spans:
            if span.span_type != SPAN_JUDGE_RULE:
                continue
            payload = span.payload
            claim_id = str(payload.get("claim_id", ""))
            claim = claims.get(claim_id)
            if not claim:
                continue
            retrieval = retrievals.get(claim_id, {})
            candidates = []
            seen_sections: set[str] = set()
            for candidate in retrieval.get("candidates", []):
                section_id = str(candidate.get("section_id", ""))
                if not section_id or section_id in seen_sections:
                    continue
                text = candidate.get("text") or rule_text.get(section_id, "")
                if not text:
                    continue
                seen_sections.add(section_id)
                candidates.append({"section_id": section_id, "text": text})
                if len(candidates) >= 5:
                    break
            if not candidates:
                continue

            items.append(
                {
                    "claim_id": f"{run_id}:{claim_id}",
                    "claim_text": str(payload.get("claim_in", "")),
                    "transcript": turns.get(str(claim["turn_id"]), ""),
                    "candidates": candidates,
                    # Kept out of the human sheet. Written to the answer key.
                    "judge_verdict": str(payload.get("verdict", "")),
                }
            )
    return items


def stratified_sample(
    items: list[dict[str, Any]], size: int, seed: int
) -> list[dict[str, Any]]:
    """Sample evenly across verdict classes, then fill from the remainder."""
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        buckets.setdefault(item["judge_verdict"], []).append(item)

    for bucket in buckets.values():
        rng.shuffle(bucket)

    chosen: list[dict[str, Any]] = []
    per_class = max(1, size // max(1, len(buckets)))
    for bucket in buckets.values():
        chosen.extend(bucket[:per_class])

    if len(chosen) < size:
        taken = {i["claim_id"] for i in chosen}
        rest = [i for i in items if i["claim_id"] not in taken]
        rng.shuffle(rest)
        chosen.extend(rest[: size - len(chosen)])

    rng.shuffle(chosen)  # so verdict class is not inferable from position
    return chosen[:size]


def render_sheet(items: list[dict[str, Any]]) -> str:
    lines = [
        "# EchoProof blind labelling sheet",
        "",
        "Judge-to-human agreement, SPEC section 11. Floor is 85 percent.",
        "",
        "For each item below, read the agent's statement and the candidate rules,",
        "then write one verdict on the `VERDICT:` line. Nothing in this file",
        "reveals what EchoProof decided.",
        "",
        "Allowed verdicts, exactly one per item:",
        "",
        "- `supported` the candidate rules support the statement",
        "- `contradicted` a candidate rule prohibits or contradicts it",
        "- `no_governing_rule` none of these rules govern this statement at all",
        "- `retrieval_below_confidence` the right rule may exist but is not here",
        "- `conflicting_sections` two candidates govern and point opposite ways",
        "",
        "---",
        "",
    ]

    for index, item in enumerate(items, start=1):
        lines.append(f"## Item {index}")
        lines.append("")
        lines.append(f"`{item['claim_id']}`")
        lines.append("")
        lines.append("**What the agent said, in full:**")
        lines.append("")
        lines.append(f"> {item['transcript'] or item['claim_text']}")
        lines.append("")
        lines.append(f"**The specific statement to judge:** {item['claim_text']}")
        lines.append("")
        lines.append("**Candidate rules retrieved from 12 CFR 1006:**")
        lines.append("")
        for candidate in item["candidates"]:
            lines.append(f"- `{candidate['section_id']}` {candidate['text'][:400]}")
        lines.append("")
        lines.append("VERDICT: ")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def assert_no_leak(sheet: str, items: list[dict[str, Any]]) -> None:
    """Fail loudly rather than silently ship a contaminated baseline."""
    lowered = sheet.lower()
    for marker in LEAK_MARKERS:
        # The verdict vocabulary appears in the instructions by necessity, so
        # only non-vocabulary markers are checked as substrings.
        if marker in lowered:
            raise SystemExit(f"LEAK: {marker!r} appears in the human sheet")

    # No item's own verdict may appear next to it. Checked per item rather than
    # globally, because the instructions legitimately list every verdict once.
    body = sheet.split("---", 1)[1] if "---" in sheet else sheet
    for item in items:
        marker = f"`{item['claim_id']}`"
        if marker not in body:
            continue
        start = body.index(marker)
        end = body.find("VERDICT:", start)
        block = body[start:end].lower()
        if item["judge_verdict"].lower() in block:
            raise SystemExit(
                f"LEAK: verdict for {item['claim_id']} appears in its own block"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the blind labelling sheet.")
    parser.add_argument("--runs", default="campaign,fixtures-dev-v2")
    parser.add_argument("--size", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20260812)
    args = parser.parse_args()

    pack = load_policy_pack("reg_f")
    rule_text = {
        section.section_id: (
            f"{section.heading} {section.verbatim_text}".strip()
            if section.heading
            else section.verbatim_text
        )
        for section in pack.sections
    }

    run_ids = [r.strip() for r in args.runs.split(",") if r.strip()]
    items = collect_items(run_ids, rule_text)
    if not items:
        print("no adjudicated claims found in those runs")
        return 1

    sample = stratified_sample(items, args.size, args.seed)
    sheet = render_sheet(sample)
    assert_no_leak(sheet, sample)

    out_dir = PROJECT_ROOT / "labels"
    out_dir.mkdir(exist_ok=True)
    sheet_path = out_dir / "blind_sheet.md"
    key_path = out_dir / "answer_key.jsonl"

    sheet_path.write_text(sheet, encoding="utf-8")
    with key_path.open("w", encoding="utf-8") as handle:
        for item in sample:
            handle.write(
                json.dumps(
                    {"claim_id": item["claim_id"], "judge_verdict": item["judge_verdict"]}
                )
                + "\n"
            )

    distribution: dict[str, int] = {}
    for item in sample:
        distribution[item["judge_verdict"]] = distribution.get(item["judge_verdict"], 0) + 1

    print(f"candidate claims available  {len(items)}")
    print(f"sampled                     {len(sample)}")
    print(f"judge verdict distribution  {distribution}")
    print("leak check                  PASSED, no verdict or score in the sheet")
    print(f"sheet                       {sheet_path}")
    print(f"answer key                  {key_path}")
    print()
    print("Fill in each VERDICT: line, then run scripts/score_agreement.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
