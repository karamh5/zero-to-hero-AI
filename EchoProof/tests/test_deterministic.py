"""Tests for the deterministic money and date layer.

Deliberately imports nothing from the judge, the retriever, or the model client.
SPEC section 4 requires this suite to stay independent, because its whole purpose
is to be the part of the system whose correctness does not depend on a model
behaving well on the day.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from engine.deterministic import (
    CheckResult,
    DateParseError,
    NumberParseError,
    check_amount,
    check_date,
    normalize_date,
    normalize_number,
)

CALL_DATE = date(2026, 8, 12)  # a Wednesday


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$35.00", Decimal("35.00")),
        ("35", Decimal("35")),
        ("$4,500", Decimal("4500")),
        ("$4,500.00", Decimal("4500.00")),
        ("thirty-five", Decimal("35")),
        ("thirty five dollars", Decimal("35")),
        ("four thousand five hundred", Decimal("4500")),
        ("four thousand five hundred dollars", Decimal("4500")),
        ("twelve dollars and fifty cents", Decimal("12.50")),
        ("one hundred", Decimal("100")),
        ("nineteen", Decimal("19")),
        ("ninety nine", Decimal("99")),
        ("two million", Decimal("2000000")),
        ("$35 and 50 cents", Decimal("35.50")),
        ("zero", Decimal("0")),
    ],
)
def test_normalize_number(text: str, expected: Decimal) -> None:
    assert normalize_number(text) == expected


def test_spoken_and_written_forms_are_equal() -> None:
    """The whole point of canonicalisation: form must not change value."""
    assert normalize_number("thirty-five") == normalize_number("$35.00")
    assert normalize_number("four thousand five hundred") == normalize_number("$4,500")


def test_money_comparison_is_exact_not_floating_point() -> None:
    """Decimal, not float. 0.1 + 0.2 != 0.3 in binary floating point."""
    total = normalize_number("ten cents") + normalize_number("twenty cents")
    assert total == Decimal("0.30")


@pytest.mark.parametrize("text", ["", "no digits here", "eleventy"])
def test_normalize_number_rejects_junk(text: str) -> None:
    with pytest.raises(NumberParseError):
        normalize_number(text)


def test_check_amount_match_and_mismatch() -> None:
    match = check_amount("four thousand five hundred dollars", Decimal("4500"))
    assert match.result is CheckResult.MATCH
    assert match.value_parsed == "4500"

    mismatch = check_amount("four thousand six hundred dollars", Decimal("4500"))
    assert mismatch.result is CheckResult.MISMATCH
    # Both sides are retained so the evidence span can show the comparison.
    assert mismatch.value_parsed == "4600"
    assert mismatch.expected_value == "4500"


def test_check_amount_unparseable_does_not_become_a_mismatch() -> None:
    """An unreadable value must not be reported as a wrong value.

    Routing this to MISMATCH would emit a finding asserting the agent stated an
    incorrect amount, when in fact nothing was understood at all.
    """
    check = check_amount("some amount", Decimal("4500"))
    assert check.result is CheckResult.UNPARSEABLE
    assert check.value_parsed is None


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("today", date(2026, 8, 12)),
        ("tomorrow", date(2026, 8, 13)),
        ("yesterday", date(2026, 8, 11)),
        ("2026-09-01", date(2026, 9, 1)),
        ("9/1", date(2026, 9, 1)),
        ("9/1/2026", date(2026, 9, 1)),
        ("in 30 days", date(2026, 9, 11)),
        ("in thirty days", date(2026, 9, 11)),
        ("within two weeks", date(2026, 8, 26)),
        ("in one month", date(2026, 9, 12)),
        ("September 1", date(2026, 9, 1)),
        ("Sept 1", date(2026, 9, 1)),
        ("1 September", date(2026, 9, 1)),
        ("August 15th", date(2026, 8, 15)),
    ],
)
def test_normalize_date(text: str, expected: date) -> None:
    assert normalize_date(text, CALL_DATE) == expected


def test_next_weekday_skips_to_following_week() -> None:
    """"next Tuesday" from a Wednesday is six days out, not tomorrow."""
    assert normalize_date("next Tuesday", CALL_DATE) == date(2026, 8, 18)


def test_this_weekday_is_the_coming_one() -> None:
    assert normalize_date("this Friday", CALL_DATE) == date(2026, 8, 14)


def test_bare_month_day_resolves_forward_across_the_year_boundary() -> None:
    """A payment promise points forward, so "March 3" in November is next year."""
    november_call = date(2026, 11, 20)
    assert normalize_date("March 3", november_call) == date(2027, 3, 3)


def test_business_days_skip_the_weekend() -> None:
    """Five business days from a Wednesday is the following Wednesday."""
    assert normalize_date("in 5 business days", CALL_DATE) == date(2026, 8, 19)


def test_relative_dates_anchor_to_the_call_not_the_clock() -> None:
    """Reproducibility: the same phrase and anchor always give the same date.

    If this module read the system clock, a finding regenerated later would
    resolve to a different date and the recomputed hash would not match, which
    breaks the reproducibility property in SPEC section 7.
    """
    first = normalize_date("in 30 days", date(2026, 1, 15))
    second = normalize_date("in 30 days", date(2026, 1, 15))
    assert first == second == date(2026, 2, 14)


@pytest.mark.parametrize("text", ["", "sometime soon", "2026-13-45"])
def test_normalize_date_rejects_junk(text: str) -> None:
    with pytest.raises(DateParseError):
        normalize_date(text, CALL_DATE)


def test_check_date_match_and_mismatch() -> None:
    match = check_date("next Tuesday", date(2026, 8, 18), CALL_DATE)
    assert match.result is CheckResult.MATCH

    mismatch = check_date("next Tuesday", date(2026, 8, 19), CALL_DATE)
    assert mismatch.result is CheckResult.MISMATCH
    assert mismatch.value_parsed == "2026-08-18"
    assert mismatch.expected_value == "2026-08-19"


def test_check_date_unparseable_does_not_become_a_mismatch() -> None:
    check = check_date("at some point", date(2026, 8, 18), CALL_DATE)
    assert check.result is CheckResult.UNPARSEABLE
