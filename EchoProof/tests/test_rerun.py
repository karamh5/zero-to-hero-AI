"""Tests for the fix-and-rerun diff."""

from __future__ import annotations

from engine.rerun import diff_runs, keys_from_findings


def f(section_id, verdict="contradicted", claim_id="c0"):  # type: ignore[no-untyped-def]
    return {"section_id": section_id, "verdict": verdict, "claim_id": claim_id}


def test_a_fixed_issue_is_closed() -> None:
    delta = diff_runs("sc-01", 1, [f("1006.6(c)(1)")], [])
    assert [k.section_id for k in delta.closed] == ["1006.6(c)(1)"]
    assert not delta.persisted and not delta.new
    assert delta.improved


def test_an_unfixed_issue_persists() -> None:
    delta = diff_runs("sc-01", 1, [f("1006.6(c)(1)")], [f("1006.6(c)(1)")])
    assert [k.section_id for k in delta.persisted] == ["1006.6(c)(1)"]
    assert not delta.closed
    assert not delta.improved


def test_a_regression_is_reported_as_new() -> None:
    delta = diff_runs("sc-01", 1, [], [f("1006.14(g)")])
    assert [k.section_id for k in delta.new] == ["1006.14(g)"]
    assert not delta.improved


def test_a_fix_that_introduces_a_new_issue_is_not_an_improvement() -> None:
    """Closing one issue while opening another is not a fix."""
    delta = diff_runs("sc-01", 1, [f("1006.6(c)(1)")], [f("1006.14(g)")])
    assert delta.closed and delta.new
    assert delta.improved is False


def test_identity_survives_a_changed_claim_id() -> None:
    """A fix changes what the agent says, so claim ids move between runs.

    Keying on claim_id would report the same issue as both closed and new.
    """
    delta = diff_runs(
        "sc-01",
        1,
        [f("1006.6(c)(1)", claim_id="t01-c00")],
        [f("1006.6(c)(1)", claim_id="t02-c03")],
    )
    assert delta.persisted and not delta.closed and not delta.new


def test_findings_without_a_section_are_not_tracked() -> None:
    """An untraceable finding would look closed on every rerun."""
    assert keys_from_findings([{"verdict": "contradicted"}]) == set()
    assert keys_from_findings([{"section_id": "1006.1", "verdict": None}]) == set()


def test_same_section_different_verdict_is_a_different_issue() -> None:
    delta = diff_runs(
        "sc-01",
        1,
        [f("1006.6(c)(1)", verdict="contradicted")],
        [f("1006.6(c)(1)", verdict="supported")],
    )
    assert delta.closed and delta.new
    assert not delta.persisted


def test_counts_are_raw_finding_counts_not_key_counts() -> None:
    delta = diff_runs(
        "sc-01", 1, [f("1006.6(c)(1)"), f("1006.6(c)(1)", claim_id="c1")], []
    )
    assert delta.before_count == 2
    assert len(delta.closed) == 1
