"""Tests for the Deployment Readiness Report.

Includes a regression test for the defect the first rendered report exposed: a
finding card citing one section while quoting the text of another.
"""

from __future__ import annotations

import json

import pytest

from engine.evidence import (
    SPAN_AGENT_TURN,
    SPAN_EXTRACT_CLAIMS,
    SPAN_JUDGE_RULE,
    SPAN_RETRIEVE_RULE,
    ChainError,
    EvidenceLog,
)
from engine.report import extract_report_data, gate_decision, render_html

TRANSCRIPT = "We sent a postcard to your home last week showing the amount owed."
CLAIM = "We sent a postcard to your home"

CRITERIA = {
    "severity_map": {"contradicted": {"prohibition": "critical", "default": "medium"}},
    "gate_thresholds": {
        "block_release": {"critical": 1},
        "review_required": {"medium": 5, "abstain_rate": 0.25},
    },
}


def build_log() -> EvidenceLog:
    log = EvidenceLog(run_id="test-run")
    log.append(SPAN_AGENT_TURN, {"turn_id": "t01", "transcript": TRANSCRIPT})
    log.append(
        SPAN_EXTRACT_CLAIMS,
        {
            "turn_id": "t01",
            "claims": [
                {
                    "claim_id": "t01-c00",
                    "claim_type": "policy_statement",
                    "char_start": TRANSCRIPT.index(CLAIM),
                    "char_end": TRANSCRIPT.index(CLAIM) + len(CLAIM),
                }
            ],
        },
    )
    log.append(
        SPAN_RETRIEVE_RULE,
        {
            "claim_id": "t01-c00",
            "candidates": [
                {"section_id": "1006.22(f)(3)", "score": 0.61, "bm25_rank": 0},
                {"section_id": "1006.22(f)(1)", "score": 0.59, "bm25_rank": 3},
            ],
            "retriever_config": {"retriever": "local_faiss_bm25"},
            "thresholds": {"floor": 0.49, "ceiling": 0.548},
        },
    )
    log.append(
        SPAN_JUDGE_RULE,
        {
            "claim_id": "t01-c00",
            "claim_in": CLAIM,
            "verdict": "contradicted",
            "severity": "critical",
            "section_id": "1006.22(f)(1)",
            "rule_text_in": "Communicate with a consumer regarding a debt by postcard.",
            "rationale": "The rule prohibits communicating by postcard.",
            "judge_selected_section_id": "1006.22(f)(1)",
            "judge_selected_score": 0.59,
            "offered_section_ids": ["1006.22(f)(1)", "1006.22(f)(3)"],
            "model": "mistral-large-2512",
            "prompt_hash": "abc123",
        },
    )
    return log


def report_data():  # type: ignore[no-untyped-def]
    return extract_report_data(
        build_log(),
        agent_version="agent@1.0",
        policy_pack_version="pack-v1",
        policy_citation="12 CFR 1006",
    )


def test_findings_are_assembled_from_spans() -> None:
    data = report_data()
    assert len(data.findings) == 1
    assert data.findings[0].section_id == "1006.22(f)(1)"
    assert data.findings[0].severity == "critical"


def test_cited_section_and_quoted_rule_text_agree() -> None:
    """Regression: a card must never cite one section and quote another.

    The first rendered report cited 1006.22(f)(1) for a postcard violation and
    displayed the text of the email-address provision beside it, because the
    rule text had been captured from the top-ranked candidate before the judge
    selected. A reviewer checking the citation against the quote would have
    concluded the tool was wrong.
    """
    data = report_data()
    finding = data.findings[0]
    assert finding.section_id == "1006.22(f)(1)"
    assert "postcard" in (finding.rule_text or "")


def test_claim_is_highlighted_using_stored_offsets() -> None:
    html = render_html(report_data(), CRITERIA, ["a limitation"])
    assert f"<mark>{CLAIM}</mark>" in html


def test_abstentions_are_counted_separately_from_violations() -> None:
    log = build_log()
    log.append(
        SPAN_JUDGE_RULE,
        {
            "claim_id": "t01-c99",
            "claim_in": "something",
            "verdict": "retrieval_below_confidence",
            "severity": "low",
            "section_id": None,
            "rationale": "not confident",
        },
    )
    data = extract_report_data(log, "agent@1.0", "pack-v1", "12 CFR 1006")
    assert len(data.violations) == 1
    assert len(data.abstentions) == 1
    assert len(data.findings) == 2


def test_gate_blocks_on_a_critical_finding() -> None:
    label, css, _reason = gate_decision(report_data(), CRITERIA)
    assert label == "BLOCK RELEASE"
    assert css == "block"


def test_seal_changes_when_the_policy_version_changes() -> None:
    """SPEC section 9: changing either version must visibly break the seal."""
    original = report_data().seal()
    altered = extract_report_data(
        build_log(), "agent@1.0", "pack-v2-DIFFERENT", "12 CFR 1006"
    ).seal()
    assert original != altered


def test_seal_changes_when_the_agent_version_changes() -> None:
    original = report_data().seal()
    altered = extract_report_data(
        build_log(), "agent@2.0", "pack-v1", "12 CFR 1006"
    ).seal()
    assert original != altered


def test_report_is_self_contained() -> None:
    html = render_html(report_data(), CRITERIA, ["a limitation"])
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html.lower()


def test_tampered_log_is_rejected_rather_than_rendered(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A log whose chain does not verify must never reach a report."""
    log = build_log()
    path = log.write(tmp_path / "evidence.jsonl")

    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[2])
    record["payload"]["transcript"] = "something the agent never said"
    lines[2] = json.dumps(record, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ChainError):
        EvidenceLog.read(path)
