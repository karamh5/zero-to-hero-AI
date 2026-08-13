"""Tests for judge-to-human agreement scoring."""

from __future__ import annotations

import pytest

from engine.agreement import cohens_kappa, score_agreement


def test_perfect_agreement() -> None:
    judge = {"a": "contradicted", "b": "supported"}
    result = score_agreement(judge, dict(judge))
    assert result.raw_agreement == 1.0
    assert result.meets_floor


def test_total_disagreement() -> None:
    result = score_agreement(
        {"a": "contradicted", "b": "supported"},
        {"a": "supported", "b": "contradicted"},
    )
    assert result.raw_agreement == 0.0
    assert not result.meets_floor
    assert "triage layer" in result.positioning


def test_kappa_on_a_known_table() -> None:
    """20 items, 16 agreements, balanced marginals.

    observed = 0.80. Judge is 10 yes / 10 no, human is 10 yes / 10 no, so
    expected = 0.5*0.5 + 0.5*0.5 = 0.5, and kappa = (0.8-0.5)/(1-0.5) = 0.6.
    """
    pairs = (
        [("yes", "yes")] * 8
        + [("no", "no")] * 8
        + [("yes", "no")] * 2
        + [("no", "yes")] * 2
    )
    assert cohens_kappa(pairs) == pytest.approx(0.6)


def test_a_labeller_who_always_says_the_same_thing_scores_zero_kappa() -> None:
    """The failure mode kappa exists to catch.

    With a skewed distribution, answering one label every time earns high raw
    agreement while carrying no information.
    """
    judge = {str(i): "retrieval_below_confidence" for i in range(18)}
    judge.update({"18": "contradicted", "19": "supported"})
    human = {k: "retrieval_below_confidence" for k in judge}

    result = score_agreement(judge, human)
    assert result.raw_agreement == pytest.approx(0.9)
    assert result.meets_floor  # raw agreement clears the floor
    assert result.kappa == pytest.approx(0.0)  # and kappa says it means nothing


def test_degenerate_single_label_does_not_report_kappa_of_one() -> None:
    pairs = [("x", "x")] * 10
    assert cohens_kappa(pairs) == 0.0


def test_only_shared_items_are_scored() -> None:
    result = score_agreement(
        {"a": "supported", "b": "supported"}, {"a": "supported", "c": "supported"}
    )
    assert result.total == 1


def test_disagreements_are_itemised() -> None:
    result = score_agreement(
        {"a": "contradicted"}, {"a": "no_governing_rule"}
    )
    assert result.disagreements == [
        {"claim_id": "a", "judge": "contradicted", "human": "no_governing_rule"}
    ]


def test_empty_input_is_not_a_crash() -> None:
    result = score_agreement({}, {})
    assert result.total == 0
    assert result.raw_agreement == 0.0
    assert not result.meets_floor
