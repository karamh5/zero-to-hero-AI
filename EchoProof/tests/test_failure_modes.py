"""Broken input must abstain or reject cleanly. It must never crash.

A compliance tool that throws on a malformed turn does not merely lose that
turn: the campaign stops, the evidence chain ends mid-run, and the report comes
out silently short. These are the offline cases; scripts/failure_drill.py runs
the same shapes through the live pipeline.
"""

from __future__ import annotations

import json

import pytest

from core.contracts import Claim, ClaimType, RetrievalCandidate, RetrievalResult
from engine.agreement import score_agreement
from engine.audio import AudioError, build_transcript, map_offsets_to_words
from engine.deterministic import check_amount, check_date, normalize_number
from engine.drift import validate_call
from engine.evidence import ChainError, EvidenceLog
from engine.extract import resolve_claim
from engine.rerun import diff_runs
from engine.retrieval.base import RetrievalConfig, ThresholdError, adjudicate, merge

TRANSCRIPT = "Your balance is $4,500 and I can remove it."


# ---------------------------------------------------------------------------
# Claim offsets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "quote",
    ["", "   ", "text that is definitely not present in the transcript at all"],
)
def test_bad_quotes_are_rejected_not_repaired(quote: str) -> None:
    result = resolve_claim(
        {"claim_type": "numeric", "quote": quote}, TRANSCRIPT, "c0"
    )
    assert isinstance(result, str)


def test_reversed_and_out_of_range_offsets_are_invalid() -> None:
    for start, end in ((10, 5), (-4, 6), (0, 9999), (5, 5)):
        claim = Claim(
            claim_id="c", claim_type=ClaimType.NUMERIC, char_start=start, char_end=end
        )
        assert not claim.is_valid_span(TRANSCRIPT)


def test_malformed_tool_items_do_not_raise() -> None:
    for item in (None, 42, [], {"quote": "x"}, {"claim_type": "nope", "quote": "Your"}):
        assert isinstance(resolve_claim(item, TRANSCRIPT, "c0"), str)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def test_empty_candidate_list_abstains() -> None:
    config = RetrievalConfig(floor=0.4, ceiling=0.6)
    result = adjudicate("a query", [], config)
    assert result.selected_section_id is None
    assert not result.cleared_floor


def test_merging_nothing_abstains() -> None:
    config = RetrievalConfig(floor=0.4, ceiling=0.6)
    assert merge([], config).selected_section_id is None


def test_thresholds_that_collapse_are_rejected_at_construction() -> None:
    """Merging floor and ceiling turns a retrieval miss into a false gap claim."""
    with pytest.raises(ThresholdError):
        RetrievalConfig(floor=0.6, ceiling=0.6)
    with pytest.raises(ThresholdError):
        RetrievalConfig(floor=0.7, ceiling=0.5)


def test_shortlist_of_an_empty_result_is_empty() -> None:
    result = RetrievalResult(
        query="q", candidates=[], selected_section_id=None,
        cleared_floor=False, cleared_ceiling=False,
    )
    assert result.shortlist(10) == []
    assert result.top_score == 0.0


def test_shortlist_deduplicates_by_section() -> None:
    def candidate(chunk_id: str, section_id: str) -> RetrievalCandidate:
        return RetrievalCandidate(
            section_id=section_id, chunk_id=chunk_id, text="t", score=0.5
        )

    result = RetrievalResult(
        query="q",
        candidates=[
            candidate("a#0", "1006.1"),
            candidate("a#1", "1006.1"),
            candidate("b", "1006.2"),
        ],
        selected_section_id="1006.1",
        cleared_floor=True,
        cleared_ceiling=True,
    )
    assert [c.section_id for c in result.shortlist(10)] == ["1006.1", "1006.2"]


# ---------------------------------------------------------------------------
# Deterministic layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("junk", ["", "   ", "!!!", "\x00\x01", "eleventy seven"])
def test_unparseable_amounts_are_never_reported_as_mismatches(junk: str) -> None:
    """An amount that could not be read is not an amount that was wrong."""
    from decimal import Decimal

    check = check_amount(junk, Decimal("100"))
    assert check.result.value == "unparseable"


def test_unparseable_dates_are_never_mismatches() -> None:
    from datetime import date

    check = check_date("whenever", date(2026, 8, 12), date(2026, 8, 12))
    assert check.result.value == "unparseable"


def test_control_characters_do_not_crash_normalisation() -> None:
    from engine.deterministic import NumberParseError

    with pytest.raises(NumberParseError):
        normalize_number("\x00\x1f\x7f")


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------


def test_empty_word_list_produces_an_empty_transcript() -> None:
    transcript, tokens = build_transcript([])
    assert transcript == ""
    assert tokens == []


def test_words_missing_fields_are_skipped_not_fatal() -> None:
    transcript, tokens = build_transcript(
        [{"punctuated_word": "Hello"}, {}, {"word": "there"}]
    )
    assert transcript == "Hello there"
    assert len(tokens) == 2


def test_offsets_outside_the_token_range_map_to_nothing() -> None:
    _transcript, tokens = build_transcript(
        [{"punctuated_word": "Hello", "start": 0, "end": 1, "confidence": 0.9}]
    )
    assert map_offsets_to_words(tokens, 900, 950) == []


def test_clip_bounds_on_no_tokens_raises_a_typed_error() -> None:
    from engine.audio import clip_bounds

    with pytest.raises(AudioError):
        clip_bounds([])


# ---------------------------------------------------------------------------
# Evidence, drift, rerun, agreement
# ---------------------------------------------------------------------------


def test_reading_an_empty_log_raises_a_typed_error(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ChainError):
        EvidenceLog.read(path)


def test_a_spliced_log_is_rejected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    log = EvidenceLog(run_id="r")
    log.append("a", {"n": 1})
    log.append("a", {"n": 2})
    log.append("a", {"n": 3})
    path = log.write(tmp_path / "e.jsonl")

    lines = path.read_text(encoding="utf-8").splitlines()
    del lines[2]  # remove a middle entry, leaving the rest intact
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ChainError):
        EvidenceLog.read(path)


def test_drift_validation_on_no_turns_is_valid_not_a_crash() -> None:
    assert validate_call([], {"must_mention_any": ["x"]}).valid


def test_rerun_diff_on_two_empty_runs() -> None:
    delta = diff_runs("sc", 1, [], [])
    assert not delta.closed and not delta.persisted and not delta.new
    assert delta.improved is False


def test_agreement_on_disjoint_label_sets() -> None:
    result = score_agreement({"a": "supported"}, {"b": "supported"})
    assert result.total == 0
    assert result.raw_agreement == 0.0


def test_report_extraction_survives_a_log_with_no_judge_spans() -> None:
    from engine.report import extract_report_data

    log = EvidenceLog(run_id="r")
    log.append("agent.turn", {"turn_id": "t", "transcript": "hello"})
    data = extract_report_data(log, "agent@1", "pack@1", "citation")
    assert data.findings == []
    assert data.seal()


def test_report_renders_with_no_findings() -> None:
    from engine.report import extract_report_data, render_html

    log = EvidenceLog(run_id="r")
    log.append("agent.turn", {"turn_id": "t", "transcript": "hello"})
    html = render_html(extract_report_data(log, "a", "p", "c"), {}, [])
    assert "Deployment Readiness Report" in html
    assert json.dumps  # imported for the module, not the assertion
