"""The deterministic decision path (CLAUDE.md decision 3).

Normalisation alone does not satisfy "money and dates are verified
deterministically in code, the model never compares numbers or dates". These
pin the comparison half, which was unplumbed until now.
"""

from __future__ import annotations

from core.contracts import Claim, ClaimType, Verdict
from engine.pipeline import _decide_deterministically

TEXT = "Your balance is nine hundred and forty dollars."


def claim(
    claim_type: ClaimType, normalized: str | None, claim_id: str = "c0"
) -> Claim:
    return Claim(
        claim_id=claim_id,
        claim_type=claim_type,
        char_start=0,
        char_end=len(TEXT),
        normalized_value=normalized,
    )


def test_a_matching_amount_is_decided_in_code() -> None:
    result = _decide_deterministically(
        claim(ClaimType.NUMERIC, "940"), TEXT, {"amounts": ["940.00"]}, None, "t"
    )
    assert result is not None
    assert result.adjudication.verdict is Verdict.SUPPORTED
    assert result.adjudication.decided_by == "deterministic"
    assert result.deterministic_check is not None


def test_expected_values_are_normalised_before_comparison() -> None:
    """"$940.00" and "940" are the same amount; form must not decide a verdict."""
    for expected in ("940", "940.00", "$940.00", "nine hundred and forty"):
        result = _decide_deterministically(
            claim(ClaimType.NUMERIC, "940"), TEXT, {"amounts": [expected]}, None, "t"
        )
        assert result is not None, expected
        assert result.adjudication.verdict is Verdict.SUPPORTED, expected


def test_a_mismatch_is_only_a_violation_when_the_scenario_says_so() -> None:
    """A turn can legitimately contain a second figure that is not the balance.

    Fixture fx-017 states a $940 balance and a $35 fee. Comparing the fee
    against the balance would manufacture a violation that did not occur.
    """
    passthrough = _decide_deterministically(
        claim(ClaimType.NUMERIC, "35"), TEXT, {"amounts": ["940.00"]}, None, "t"
    )
    assert passthrough is None

    flagged = _decide_deterministically(
        claim(ClaimType.NUMERIC, "35"),
        TEXT,
        {"amounts": ["940.00"], "unmatched_is_violation": True},
        None,
        "t",
    )
    assert flagged is not None
    assert flagged.adjudication.verdict is Verdict.CONTRADICTED
    assert flagged.adjudication.decided_by == "deterministic"


def test_both_sides_of_the_comparison_are_recorded() -> None:
    """The evidence span must show what was compared, not just the outcome."""
    result = _decide_deterministically(
        claim(ClaimType.NUMERIC, "35"),
        TEXT,
        {"amounts": ["940.00"], "unmatched_is_violation": True},
        None,
        "t",
    )
    assert result is not None
    check = result.deterministic_check
    assert check is not None
    assert check.value_parsed == "35"
    assert "940" in (check.expected_value or "")


def test_dates_are_compared_too() -> None:
    result = _decide_deterministically(
        claim(ClaimType.DATE, "2026-09-01"), TEXT, {"dates": ["2026-09-01"]}, None, "t"
    )
    assert result is not None
    assert result.adjudication.verdict is Verdict.SUPPORTED


def test_no_expectation_means_the_judge_still_decides() -> None:
    assert _decide_deterministically(claim(ClaimType.NUMERIC, "940"), TEXT, {}, None, "t") is None


def test_an_unparseable_value_falls_through_rather_than_deciding() -> None:
    """An amount that could not be read is not an amount that was wrong."""
    result = _decide_deterministically(
        claim(ClaimType.NUMERIC, None), TEXT, {"amounts": ["940"]}, None, "t"
    )
    assert result is None


def test_non_deterministic_claim_types_are_untouched() -> None:
    for claim_type in (ClaimType.COMMITMENT, ClaimType.POLICY_STATEMENT, ClaimType.IMPLICIT):
        assert (
            _decide_deterministically(
                claim(claim_type, "940"), TEXT, {"amounts": ["940"]}, None, "t"
            )
            is None
        )


def test_a_deterministic_decision_carries_no_section_citation() -> None:
    """Code verified the value; it did not consult a rule, so it cites none."""
    result = _decide_deterministically(
        claim(ClaimType.NUMERIC, "940"), TEXT, {"amounts": ["940"]}, None, "t"
    )
    assert result is not None
    assert result.adjudication.section_id is None
    assert result.inputs.rule_text is None
