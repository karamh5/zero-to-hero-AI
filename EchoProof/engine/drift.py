"""Persona drift validation (SPEC section 10).

A synthetic caller that improvises outside its specification invalidates the
call: the scenario tested is no longer the scenario that was written. The
validator checks each persona turn against the rules its pack declares.

**A drifted call is tagged invalid and retained, then re-run. It is never
discarded.** SPEC section 10 is explicit about this, and the reason is that a
drifted call is often the most informative artifact in a campaign. If the
persona keeps abandoning a cease-communication stance, that is a finding about
the persona specification, and deleting the evidence would hide it.

The rules are pack data. Nothing here knows what a debt is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DriftResult:
    """Outcome of validating one persona turn, or a whole call."""

    valid: bool
    reasons: list[str] = field(default_factory=list)
    turn_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "reasons": list(self.reasons),
            "turn_index": self.turn_index,
        }


def _contains_any(text: str, phrases: list[str]) -> str | None:
    lowered = text.lower()
    for phrase in phrases:
        if phrase.lower() in lowered:
            return phrase
    return None


def validate_turn(
    text: str, rules: dict[str, Any], turn_index: int, is_first_turn: bool
) -> DriftResult:
    """Validate one persona utterance against its drift rules."""
    reasons: list[str] = []

    max_words = int(rules.get("max_words", 0) or 0)
    word_count = len(re.findall(r"\S+", text))
    if max_words and word_count > max_words:
        reasons.append(f"turn ran to {word_count} words, over the {max_words} limit")

    forbidden = list(rules.get("must_not_mention_any", []))
    hit = _contains_any(text, forbidden)
    if hit:
        reasons.append(f"said {hit!r}, which the persona must never say")

    # The required stance is checked on the opening turn only. Later turns are
    # allowed to answer a direct question without restating the trigger, and
    # demanding the phrase every time would flag natural conversation as drift.
    if is_first_turn:
        required = list(rules.get("must_mention_any", []))
        if required and _contains_any(text, required) is None:
            reasons.append(
                "opening turn did not state the persona's statutory trigger"
            )

    if not text.strip():
        reasons.append("empty turn")

    return DriftResult(valid=not reasons, reasons=reasons, turn_index=turn_index)


def validate_call(
    persona_turns: list[str], rules: dict[str, Any]
) -> DriftResult:
    """Validate a whole call. Invalid if any turn drifted."""
    all_reasons: list[str] = []
    first_bad: int | None = None

    for index, text in enumerate(persona_turns):
        result = validate_turn(text, rules, index, is_first_turn=(index == 0))
        if not result.valid:
            if first_bad is None:
                first_bad = index
            all_reasons.extend(f"turn {index}: {r}" for r in result.reasons)

    return DriftResult(
        valid=not all_reasons, reasons=all_reasons, turn_index=first_bad
    )
