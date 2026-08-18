"""Tests for the Supabase metadata store.

No network. These pin the boundary that matters: metadata leaves, content does
not, and a missing or broken store never fails a run.
"""

from __future__ import annotations

from core.config import Settings
from store.supabase_store import StoreResult, SupabaseStore, _metadata_only

CONTENT_FIELDS = {
    "transcript": "Pay today and I will delete your credit report entry.",
    "rule_text": "A debt collector must not ...",
    "rationale": "The rule prohibits ...",
    "claim_text": "I can have this removed",
    "raw_response": "{...}",
    "prompt_hash": "abc",
    "audio_bytes": b"RIFF",
}

FINDING = {
    "claim_id": "t01-c00",
    "scenario_id": "sc-01",
    "verdict": "contradicted",
    "severity": "critical",
    "section_id": "1006.18(c)(1)",
    "selected_score": 0.61,
    "entry_hash": "deadbeef",
    "audio_clip_ref": "sha256:abc",
    **CONTENT_FIELDS,
}


def settings(with_supabase: bool) -> Settings:
    return Settings(
        mistral_api_key="k",
        mistral_base_url="https://example.invalid/v1",
        supabase_url="https://example.supabase.co" if with_supabase else None,
        supabase_key="key" if with_supabase else None,
        deepgram_api_key=None,
    )


def test_projection_keeps_metadata() -> None:
    row = _metadata_only(FINDING, "run-1")
    assert row["run_id"] == "run-1"
    assert row["verdict"] == "contradicted"
    assert row["section_id"] == "1006.18(c)(1)"
    assert row["entry_hash"] == "deadbeef"


def test_projection_drops_every_content_field() -> None:
    """ARCHITECTURE.md decision 11: evidence content never reaches Supabase."""
    row = _metadata_only(FINDING, "run-1")
    for field in CONTENT_FIELDS:
        assert field not in row, f"{field} leaked into the metadata row"


def test_projection_is_an_allowlist_not_a_denylist() -> None:
    """A new content field must not leak simply because nobody denied it."""
    finding = dict(FINDING)
    finding["some_future_content_field"] = "the agent said something sensitive"
    row = _metadata_only(finding, "run-1")
    assert "some_future_content_field" not in row


def test_store_is_disabled_without_credentials() -> None:
    store = SupabaseStore(settings(with_supabase=False))
    assert store.enabled is False
    result = store.write_run({"run_id": "r"}, [FINDING])
    assert result.enabled is False
    assert result.error is None
    assert "disabled" in result.describe()


def test_a_broken_store_never_raises() -> None:
    """An optional index must not be able to fail a campaign."""
    store = SupabaseStore(settings(with_supabase=True))
    result = store.write_run({"run_id": "r"}, [FINDING])
    assert isinstance(result, StoreResult)
    assert result.enabled is True
    # Either it failed to reach the invalid host, or the SDK is absent. Both are
    # reported rather than raised.
    assert result.error is not None
    assert "run is unaffected" in result.describe()
