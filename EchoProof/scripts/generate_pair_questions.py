"""Generate retrieval questions for claim pairs, so the approach can be measured.

The extractor emits a `retrieval_question` per claim. To know whether that
actually helps, the same transformation has to be applied to the evaluation
pairs and scored. This script does exactly that, reusing the identical guidance
text the extractor uses, so what is measured here is what production runs.

Ground truth is copied across untouched. Only the query text changes.

Run:
    python scripts/generate_pair_questions.py
    python scripts/eval_retrieval.py --pairs fixtures/retrieval_pairs_generated.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import EXTRACT_MODEL, FIXTURES_DIR, load_settings  # noqa: E402
from engine.extract import RETRIEVAL_QUESTION_GUIDANCE  # noqa: E402
from models.client import ModelClient  # noqa: E402

SYSTEM_PROMPT = (
    "You turn a single statement made by an automated agent on a call into a "
    "search query for looking up which rule in a policy corpus governs it.\n\n"
    + RETRIEVAL_QUESTION_GUIDANCE
)

QUESTION_TOOL = {
    "type": "function",
    "function": {
        "name": "record_question",
        "description": "Record the retrieval question for this statement.",
        "parameters": {
            "type": "object",
            "properties": {"retrieval_question": {"type": "string"}},
            "required": ["retrieval_question"],
        },
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate retrieval questions for pairs.")
    parser.add_argument("--pairs", default=str(FIXTURES_DIR / "retrieval_pairs.jsonl"))
    parser.add_argument(
        "--out", default=str(FIXTURES_DIR / "retrieval_pairs_generated.jsonl")
    )
    args = parser.parse_args()

    client = ModelClient(load_settings())
    source = Path(args.pairs)
    rows = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    out_path = Path(args.out)
    cost = 0.0
    written = 0

    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            call = client.complete(
                model=EXTRACT_MODEL,
                system=SYSTEM_PROMPT,
                user=f"Statement:\n{row['query']}",
                tools=[QUESTION_TOOL],
                tool_choice={
                    "type": "function",
                    "function": {"name": "record_question"},
                },
                max_tokens=200,
            )
            cost += call.estimated_cost_usd
            payload = call.tool_arguments or {}
            question = str(payload.get("retrieval_question", "")).strip()
            if not question:
                # Falling back to the claim keeps the pair in the denominator.
                # Dropping it would quietly measure an easier problem.
                question = row["query"]

            handle.write(
                json.dumps(
                    {
                        "pair_id": row["pair_id"],
                        "query": question,
                        "expected_section_id": row["expected_section_id"],
                        "source_claim": row["query"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
            print(f"{row['pair_id']}  {question}")

    print()
    print(f"wrote {written} pairs to {out_path}")
    print(f"estimated cost usd {cost:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
