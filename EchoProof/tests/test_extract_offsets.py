"""Tests for claim offset resolution.

No model is called. These test the part that decides whether the model actually
copied verbatim, which is the guarantee that replaced trusting model-supplied
integer offsets.
"""

from __future__ import annotations

from core.contracts import Claim
from engine.extract import resolve_claim

TRANSCRIPT = (
    "Hello, this is Jordan calling from Meridian Recovery. Your outstanding "
    "balance is $4,500, and if you pay the full amount today I can have this "
    "removed from your credit report entirely."
)


def _resolve(quote: str, claim_type: str = "numeric", **extra):  # type: ignore[no-untyped-def]
    return resolve_claim(
        {"claim_type": claim_type, "quote": quote, **extra}, TRANSCRIPT, "c00"
    )


def test_exact_quote_resolves_to_correct_offsets() -> None:
    claim = _resolve("Your outstanding balance is $4,500")
    assert isinstance(claim, Claim)
    assert claim.text(TRANSCRIPT) == "Your outstanding balance is $4,500"
    assert TRANSCRIPT[claim.char_start : claim.char_end] == "Your outstanding balance is $4,500"


def test_offsets_are_a_real_span_of_the_transcript() -> None:
    """The failure that motivated this design returned spans like 'overy'."""
    claim = _resolve("removed from your credit report entirely")
    assert isinstance(claim, Claim)
    assert claim.is_valid_span(TRANSCRIPT)
    assert claim.text(TRANSCRIPT).startswith("removed from")


def test_paraphrase_is_rejected_not_repaired() -> None:
    """A reworded claim loses its claim rather than corrupting one."""
    reason = _resolve("The balance owed is four thousand five hundred dollars")
    assert isinstance(reason, str)
    assert "not found verbatim" in reason


def test_whitespace_variation_still_matches() -> None:
    """A doubled space in the quote must not discard a genuine claim."""
    claim = _resolve("Your  outstanding   balance is $4,500")
    assert isinstance(claim, Claim)
    assert claim.text(TRANSCRIPT) == "Your outstanding balance is $4,500"


def test_occurrence_selects_the_right_repetition() -> None:
    transcript = "Pay today. Pay today."
    first = resolve_claim(
        {"claim_type": "commitment", "quote": "Pay today", "occurrence": 1},
        transcript,
        "c00",
    )
    second = resolve_claim(
        {"claim_type": "commitment", "quote": "Pay today", "occurrence": 2},
        transcript,
        "c01",
    )
    assert isinstance(first, Claim) and isinstance(second, Claim)
    assert first.char_start == 0
    assert second.char_start == 11


def test_retrieval_questions_are_parsed_and_deduplicated() -> None:
    claim = _resolve(
        "Your outstanding balance is $4,500",
        retrieval_questions=[
            "What must a notice state about the amount owed?",
            "what must a notice state about the amount owed?",
            "  ",
            "May an agent state a balance that is not accurate?",
        ],
    )
    assert isinstance(claim, Claim)
    assert claim.retrieval_questions == (
        "What must a notice state about the amount owed?",
        "May an agent state a balance that is not accurate?",
    )


def test_single_string_question_form_is_tolerated() -> None:
    """The older single-question shape must not lose the whole claim."""
    claim = _resolve(
        "Your outstanding balance is $4,500",
        retrieval_questions="What rules govern stating a balance?",
    )
    assert isinstance(claim, Claim)
    assert claim.retrieval_questions == ("What rules govern stating a balance?",)


def test_missing_questions_leave_the_claim_usable() -> None:
    """A missing search hint is not worth discarding a real claim over."""
    claim = _resolve("Your outstanding balance is $4,500")
    assert isinstance(claim, Claim)
    assert claim.retrieval_questions == ()


def test_missing_and_malformed_items_are_rejected() -> None:
    assert isinstance(resolve_claim({"quote": "x"}, TRANSCRIPT, "c00"), str)
    assert isinstance(resolve_claim({"claim_type": "numeric"}, TRANSCRIPT, "c00"), str)
    assert isinstance(
        resolve_claim({"claim_type": "nonsense", "quote": "Hello"}, TRANSCRIPT, "c00"), str
    )
    assert isinstance(resolve_claim("not an object", TRANSCRIPT, "c00"), str)
    assert isinstance(
        resolve_claim({"claim_type": "numeric", "quote": "   "}, TRANSCRIPT, "c00"), str
    )
