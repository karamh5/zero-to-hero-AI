"""Tests for the persona drift validator."""

from __future__ import annotations

from engine.drift import validate_call, validate_turn

RULES = {
    "must_mention_any": ["stop contacting", "cease"],
    "must_not_mention_any": ["I will pay", "let's set up a payment"],
    "max_words": 30,
}


def test_compliant_opening_turn_is_valid() -> None:
    result = validate_turn(
        "I sent you a written request to stop contacting me about this.",
        RULES,
        turn_index=0,
        is_first_turn=True,
    )
    assert result.valid


def test_opening_turn_missing_the_trigger_is_drift() -> None:
    result = validate_turn(
        "Who is this exactly?", RULES, turn_index=0, is_first_turn=True
    )
    assert not result.valid
    assert "statutory trigger" in result.reasons[0]


def test_later_turn_need_not_restate_the_trigger() -> None:
    """Demanding the phrase every turn would flag natural conversation."""
    result = validate_turn(
        "No, I am not interested in discussing that.",
        RULES,
        turn_index=2,
        is_first_turn=False,
    )
    assert result.valid


def test_forbidden_phrase_is_drift() -> None:
    result = validate_turn(
        "Fine, I will pay it today.", RULES, turn_index=1, is_first_turn=False
    )
    assert not result.valid
    assert "must never say" in result.reasons[0]


def test_overlong_turn_is_drift() -> None:
    result = validate_turn(
        "stop contacting me " + "and ".join(["blah"] * 40),
        RULES,
        turn_index=0,
        is_first_turn=True,
    )
    assert not result.valid
    assert any("over the" in r for r in result.reasons)


def test_empty_turn_is_drift() -> None:
    result = validate_turn("", RULES, turn_index=1, is_first_turn=False)
    assert not result.valid


def test_call_is_invalid_when_any_turn_drifts() -> None:
    call = validate_call(
        [
            "I sent a written request to stop contacting me.",
            "I said stop calling.",
            "Alright, I will pay it.",
        ],
        RULES,
    )
    assert not call.valid
    assert call.turn_index == 2
    assert len(call.reasons) == 1


def test_fully_compliant_call_is_valid() -> None:
    call = validate_call(
        [
            "I sent a written request to stop contacting me.",
            "Please cease all contact.",
        ],
        RULES,
    )
    assert call.valid
    assert call.turn_index is None
