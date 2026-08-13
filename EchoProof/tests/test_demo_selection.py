"""Tests for demo shortlist selection and the recorded clip.

The demo must not be able to drift into presenting a rule nobody has evidence
for, or a clip that is longer than the window it fills.
"""

from __future__ import annotations

import json

from core.config import PROJECT_ROOT

SHORTLIST = PROJECT_ROOT / "demo" / "shortlist.json"
CLIP = PROJECT_ROOT / "demo" / "backup" / "rerun_clip.json"
LATENCY = PROJECT_ROOT / "demo" / "latency.json"


def test_every_shortlist_entry_has_recorded_evidence() -> None:
    """No rule reaches the stage without a finding in a real run behind it."""
    data = json.loads(SHORTLIST.read_text(encoding="utf-8"))
    entries = data["shortlist"]
    assert entries, "shortlist is empty"
    for entry in entries:
        assert entry["observed_findings"] >= 1
        assert entry["observed_in_runs"], f"{entry['section_id']} cites no run"


def test_shortlist_carries_the_rule_text() -> None:
    """The slide shows the rule, so the shortlist has to contain it."""
    data = json.loads(SHORTLIST.read_text(encoding="utf-8"))
    for entry in data["shortlist"]:
        assert entry["rule_text"].strip()
        assert entry["section_id"].startswith("1006.")


def test_shortlist_is_pinned_to_a_policy_version() -> None:
    data = json.loads(SHORTLIST.read_text(encoding="utf-8"))
    assert data["policy_pack_version"]


def test_clip_fits_inside_the_measured_dead_time() -> None:
    """A clip longer than the wait it fills leaves dead air at the end."""
    clip = json.loads(CLIP.read_text(encoding="utf-8"))
    latency = json.loads(LATENCY.read_text(encoding="utf-8"))
    assert clip["duration_seconds"] <= latency["worst_total"]


def test_clip_is_replayed_from_a_real_run() -> None:
    """The footage must be real output, never a re-enactment."""
    clip = json.loads(CLIP.read_text(encoding="utf-8"))
    assert "fix-and-rerun" in clip["source"]
    assert clip["frames"]


def test_latency_is_reported_as_a_distribution() -> None:
    """A single sample is not a measurement."""
    latency = json.loads(LATENCY.read_text(encoding="utf-8"))
    assert len(latency["samples"]) >= 2
    assert latency["worst_total"] >= latency["median_total"]
