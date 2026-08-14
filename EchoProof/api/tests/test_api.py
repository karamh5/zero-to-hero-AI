"""The read-only API over stored runs, exercised against real artifacts.

These tests run against whatever is in runs/ and skip cleanly when a needed
run is absent, because runs/ is git-ignored and a fresh clone has none.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from adapter.capture import CaptureQueue  # noqa: E402
from adapter.proxy import create_app  # noqa: E402
from core.config import RUNS_DIR, Settings  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    settings = Settings(
        mistral_api_key="",
        mistral_base_url="http://127.0.0.1:9",
        supabase_url=None,
        supabase_key=None,
        deepgram_api_key=None,
    )
    app = create_app(settings, CaptureQueue(handler=None))
    return TestClient(app)


def _require_run(run_id: str) -> None:
    if not (RUNS_DIR / run_id / "evidence.jsonl").exists():
        pytest.skip(f"runs/{run_id} not on disk")


def test_proxy_routes_still_exist(client: TestClient) -> None:
    # Mounting the UI must not displace the proxy surface.
    assert client.get("/healthz").status_code == 200
    assert client.get("/metrics").status_code == 200


def test_runs_listing(client: TestClient) -> None:
    _require_run("demo-campaign")
    body = client.get("/api/runs").json()
    runs = {r["run_id"]: r for r in body["runs"]}
    assert "demo-campaign" in runs
    entry = runs["demo-campaign"]
    assert entry["chain_ok"] is True
    # Abstentions and violations are separate counts, never summed.
    assert "violations" in entry and "abstentions" in entry
    assert entry["seal_state"] in {"intact", "broken", "unsealed", "unverifiable"}


def test_findings_carry_offsets_and_rule_text(client: TestClient) -> None:
    _require_run("demo-campaign")
    body = client.get("/api/runs/demo-campaign/findings").json()
    assert body["findings"], "demo-campaign has adjudicated claims"
    for finding in body["findings"]:
        assert finding["verdict"] in {
            "supported",
            "contradicted",
            "no_governing_rule",
            "retrieval_below_confidence",
            "conflicting_sections",
        }
        # Offsets index the transcript included in the same payload, so the
        # client can slice rather than search.
        assert 0 <= finding["char_start"] <= finding["char_end"]
        assert finding["char_end"] <= len(finding["transcript"])
    contradicted = [f for f in body["findings"] if f["verdict"] == "contradicted"]
    for finding in contradicted:
        # The rule text shown must be the judge's selection (the Phase 3
        # defect this API must not reintroduce).
        assert finding["rule_text"], "contradicted finding without rule text"


def test_claim_detail_joins_spans(client: TestClient) -> None:
    _require_run("demo-campaign")
    findings = client.get("/api/runs/demo-campaign/findings").json()["findings"]
    claim_id = findings[0]["claim_id"]
    detail = client.get(f"/api/runs/demo-campaign/claims/{claim_id}").json()
    assert detail["finding"]["claim_id"] == claim_id
    assert detail["judge"] is not None
    assert detail["turn"] is not None
    # The judge span's rule_text_in belongs to the section the judge selected.
    judge = detail["judge"]["payload"]
    assert judge.get("judge_selected_section_id") or judge.get("section_id")


def test_clip_served_by_digest(client: TestClient) -> None:
    _require_run("demo-campaign")
    findings = client.get("/api/runs/demo-campaign/findings").json()["findings"]
    with_clip = [f for f in findings if f["audio_clip_ref"] and f["has_clip"]]
    if not with_clip:
        pytest.skip("no clips in demo-campaign")
    digest = with_clip[0]["audio_clip_ref"]
    response = client.get(f"/api/runs/demo-campaign/clips/{digest}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert client.get(
        "/api/runs/demo-campaign/clips/" + "0" * 64
    ).status_code == 404


def test_corpus_counts_come_from_the_pack(client: TestClient) -> None:
    packs = client.get("/api/corpus").json()["packs"]
    if not packs:
        pytest.skip("no policy pack built")
    for pack in packs:
        detail = client.get(f"/api/corpus/{pack['pack_id']}").json()
        assert len(detail["sections"]) == pack["record_count"]
        assert detail["hierarchy_separators"], "separator convention is pack data"


def test_measurements_traces_to_files(client: TestClient) -> None:
    body = client.get("/api/measurements").json()
    assert "detection" in body and "agreement" in body
    detection = body["detection"]
    if detection["low"] is not None:
        assert detection["low"] <= detection["high"]
        for run in detection["runs"]:
            assert run["source"].startswith("runs/")
    agreement = body["agreement"]
    assert agreement["self_graded"] is True


def test_missing_run_is_a_404_not_a_crash(client: TestClient) -> None:
    assert client.get("/api/runs/does-not-exist").status_code == 404
    assert client.get("/api/runs/does-not-exist/findings").status_code == 404
    assert client.get("/api/runs/does-not-exist/report").status_code == 404


def test_adjudicate_without_key_is_labelled_disabled(client: TestClient) -> None:
    availability = client.get("/api/adjudicate/availability").json()
    assert availability["available"] in (True, False)
    if not availability["available"]:
        assert "MISTRAL_API_KEY" in availability["reason"]
        response = client.post("/api/adjudicate", json={"transcript": "hello"})
        assert response.status_code == 503


def test_free_text_is_refused(client: TestClient) -> None:
    """The rig must not accept unlabelled text.

    Without speaker labels there is no way to guarantee that a consumer
    utterance is not extracted from and given a verdict, which is the whole
    point of the prepared library.
    """
    response = client.post(
        "/api/adjudicate",
        json={"transcript": "Customer: I disputed this. Agent: Pay today."},
    )
    assert response.status_code == 400
    assert "free text is not accepted" in response.json()["error"]


def test_adjudicate_requires_a_known_conversation(client: TestClient) -> None:
    assert client.post("/api/adjudicate", json={}).status_code == 400
    response = client.post(
        "/api/adjudicate",
        json={"pack_id": "reg_f", "conversation_id": "does-not-exist"},
    )
    assert response.status_code == 404


def test_conversation_library_is_role_labelled(client: TestClient) -> None:
    body = client.get("/api/conversations").json()
    if not body["packs"]:
        pytest.skip("no conversation packs built")
    for pack in body["packs"]:
        for group in pack["groups"]:
            for conversation in group["conversations"]:
                assert conversation["agent_turns"] >= 1
                roles = {t["role"].lower() for t in conversation["turns"]}
                assert roles <= {"agent", "assistant", "bot", "customer", "consumer", "user", "caller"}
