"""Claim extraction via tool calling, producing character offsets (SPEC 3).

A stored claim is a `char_start` and `char_end` into the transcript, never
restated text. Two reasons, both load-bearing:

1. An offset is verifiable. A paraphrase is not: if the model rewords the claim,
   it cannot be checked against what was actually said, and a finding quoting a
   sentence the agent never uttered is worse than no finding.
2. SPEC section 8's audio citation maps these offsets onto Nova-3 word tokens to
   slice the exact sentence out of the call recording. A paraphrase has no
   position, so there is nothing to slice.

DEVIATION FROM ARCHITECTURE.md DECISION 4, FLAGGED RATHER THAN MADE SILENTLY.

Decision 4 says the tool call returns character offsets. It was implemented that
way first and it does not work. Asked to return integer offsets directly,
mistral-large-2512 produced spans like 'overy' and 'lance' on a 184 character
turn: every span was misaligned, so every downstream verdict adjudicated a
fragment. This is a known limitation of language models rather than a prompt
defect. They do not count characters.

What is implemented instead: the model returns the claim as an exact verbatim
quote, and this module locates that quote in the transcript IN CODE to derive
the offsets. The stored claim is still an offset and still never a paraphrase.
The guarantee is in fact stronger than the original design, because a
model-supplied integer cannot be validated at all, whereas a quote that fails to
appear verbatim in the transcript is detected and rejected here. A paraphrasing
model loses its claim rather than corrupting one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.config import EXTRACT_MODEL
from core.contracts import Claim, ClaimType
from models.client import ModelCall, ModelClient

RETRIEVAL_QUESTION_GUIDANCE = """\
Write each as a short, neutral question about what a rule says on this subject, \
in the register a rulebook would use. Describe the conduct or subject matter. \
Do not name a specific section, statute, or regulation. Do not state whether \
the conduct is allowed or forbidden, and do not answer the question.

Give two or three questions that approach the claim from GENUINELY DIFFERENT \
angles, because one statement can be governed by several unrelated rules. Vary \
the angle, not the wording. Two questions that differ only in phrasing are \
worth nothing. Useful angles include: the subject matter the claim is about, \
the manner or channel of what was done, whether the statement itself was \
accurate or could be delivered, and any obligation the statement triggers.

Examples of the required form:
  claim:    "I'll try you again tonight around ten thirty."
  questions:
    - "At what times of day may an agent contact a person?"
    - "How often may an agent attempt to contact a person?"

  claim:    "I can have this removed from your credit report entirely."
  questions:
    - "What limits apply to reporting information to a credit reporting agency?"
    - "May an agent state that it will take an action it cannot legally take?"
    - "May an agent make a promise about an outcome it does not control?"

  claim:    "You disputed this in writing, but we are continuing anyway."
  questions:
    - "What is required after receiving a written dispute?"
    - "May activity continue while a dispute is unresolved?"
"""

SYSTEM_PROMPT = (
    """\
You extract factual claims from a single turn spoken by an automated agent on a \
recorded call.

A claim is anything the agent asserts as fact, commits to doing, or states as \
policy. Return every one of them.

Claim types:
- numeric: any monetary amount, count, percentage, or other figure
- date: any date, deadline, or time period
- commitment: something the agent promises will happen
- policy_statement: an assertion about what is required, permitted or prohibited
- implicit: something asserted by implication rather than stated outright, such \
as implying a consequence that was never named

For every claim, return `quote`: the claim copied out of the transcript exactly, \
character for character. Copy it verbatim. Do not rewrite, paraphrase, \
summarise, correct spelling, fix grammar, expand contractions, or change \
punctuation, capitalisation or spacing. The quote must appear in the transcript \
exactly as you write it.

Keep each quote to the span that carries the claim, normally one clause or one \
sentence. Do not return the whole turn as a single quote.

If the same wording appears more than once in the turn, set `occurrence` to \
which one you mean, counting from 1.

If you cannot copy a claim exactly, omit it rather than approximating it.

For every claim also return `retrieval_questions`. These are search queries, \
not the claim. They are used to look up which rules in a policy corpus govern \
the claim, and they are never shown to anyone as the claim itself.

"""
    + RETRIEVAL_QUESTION_GUIDANCE
)

EXTRACT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "record_claims",
        "description": "Record every claim found in the agent turn, quoted verbatim.",
        "parameters": {
            "type": "object",
            "properties": {
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim_type": {
                                "type": "string",
                                "enum": [t.value for t in ClaimType],
                            },
                            "quote": {
                                "type": "string",
                                "description": "The claim, copied verbatim from the transcript.",
                            },
                            "occurrence": {
                                "type": "integer",
                                "description": "Which occurrence of this wording, counting from 1.",
                            },
                            "retrieval_questions": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 3,
                                "items": {"type": "string"},
                                "description": (
                                    "Two or three short neutral questions, each "
                                    "approaching the claim from a different angle, "
                                    "used only to search the policy corpus. Never "
                                    "displayed as the claim."
                                ),
                            },
                        },
                        "required": ["claim_type", "quote", "retrieval_questions"],
                    },
                }
            },
            "required": ["claims"],
        },
    },
}


@dataclass(frozen=True)
class ExtractionResult:
    """Extracted claims plus everything rejected, and why."""

    claims: list[Claim]
    rejected: list[dict[str, Any]]
    call: ModelCall

    def to_dict(self) -> dict[str, Any]:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "rejected": self.rejected,
            "model": self.call.model,
            "prompt_hash": self.call.prompt_hash,
            "raw_response": self.call.raw_response,
        }


def extract_claims(
    client: ModelClient, transcript: str, turn_id: str = "turn"
) -> ExtractionResult:
    """Extract claims from one agent turn."""
    user = (
        "Agent turn transcript, character offsets are into this exact string:\n\n"
        f"{transcript}"
    )
    call = client.complete(
        model=EXTRACT_MODEL,
        system=SYSTEM_PROMPT,
        user=user,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_claims"}},
    )

    payload = call.tool_arguments or {}
    raw_claims = payload.get("claims", []) if isinstance(payload, dict) else []

    claims: list[Claim] = []
    rejected: list[dict[str, Any]] = []

    for index, item in enumerate(raw_claims):
        claim_id = f"{turn_id}-c{index:02d}"
        resolved = resolve_claim(item, transcript, claim_id)
        if isinstance(resolved, str):
            rejected.append({"claim_id": claim_id, "raw": item, "reason": resolved})
            continue
        claims.append(resolved)

    return ExtractionResult(claims=claims, rejected=rejected, call=call)


def resolve_claim(item: Any, transcript: str, claim_id: str) -> Claim | str:
    """Turn one raw tool item into a Claim, or return a rejection reason.

    Locating the quote is done here, in code, with an exact string search. That
    is the whole point: the model supplies text it claims to have copied, and
    this function is what decides whether it actually did.
    """
    if not isinstance(item, dict):
        return "not an object"
    for key in ("claim_type", "quote"):
        if key not in item:
            return f"missing {key}"
    try:
        claim_type = ClaimType(item["claim_type"])
    except ValueError:
        return f"unknown claim_type {item['claim_type']!r}"

    quote = str(item["quote"])
    if not quote.strip():
        return "quote is empty"

    try:
        occurrence = max(1, int(item.get("occurrence", 1)))
    except (TypeError, ValueError):
        occurrence = 1

    span = _locate(transcript, quote, occurrence)
    if span is None:
        return f"quote not found verbatim in transcript: {quote[:60]!r}"

    start, end = span
    return Claim(
        claim_id=claim_id,
        claim_type=claim_type,
        char_start=start,
        char_end=end,
        # Absent or empty is tolerated rather than fatal. The pipeline falls back
        # to the claim text, which is worse retrieval but still a real query, and
        # losing a whole claim over a missing search hint would be a bad trade.
        retrieval_questions=_questions(item),
    )


def _questions(item: dict[str, Any]) -> tuple[str, ...]:
    """Read the retrieval questions, tolerating the older single-string form."""
    raw = item.get("retrieval_questions")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raw = [item.get("retrieval_question", "")]

    seen: set[str] = set()
    out: list[str] = []
    for entry in raw:
        text = str(entry or "").strip()
        # Deduplicate case-insensitively. The model sometimes returns the same
        # question twice with different capitalisation, and paying for the same
        # retrieval twice buys nothing.
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    return tuple(out)


def _locate(transcript: str, quote: str, occurrence: int) -> tuple[int, int] | None:
    """Find the nth occurrence of `quote`, exactly then whitespace-tolerantly.

    The exact pass is the guarantee. The whitespace-tolerant pass exists because
    transcripts contain runs of spaces and newlines that a model reproduces
    inconsistently, and rejecting a genuinely verbatim quote over a doubled space
    would discard real claims. It still matches the actual characters in order,
    so it cannot admit a paraphrase.
    """
    stripped = quote.strip()

    start = -1
    for _ in range(occurrence):
        start = transcript.find(stripped, start + 1)
        if start == -1:
            break
    if start != -1:
        return start, start + len(stripped)

    # Whitespace-tolerant: match the quote's non-space characters in order,
    # allowing any run of whitespace wherever the quote had whitespace.
    pattern = r"\s+".join(re.escape(token) for token in stripped.split())
    if not pattern:
        return None
    matches = list(re.finditer(pattern, transcript))
    if not matches:
        return None
    match = matches[min(occurrence, len(matches)) - 1]
    return match.start(), match.end()
