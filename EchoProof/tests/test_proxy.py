"""Proxy tests, driven against a fake upstream. No network.

Two invariants carry the product argument and both are tested here: the response
is returned unmodified and never delayed by adjudication, and a capture failure
never becomes a request failure. A pre-deployment assurance tool that takes
production down has inverted its own purpose.
"""

from __future__ import annotations

import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from adapter.capture import CaptureQueue, CapturedTurn, extract_agent_text
from adapter.proxy import create_app
from core.config import Settings

UPSTREAM_BODY: dict[str, Any] = {
    "id": "chatcmpl-1",
    "model": "mistral-large-2512",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Your balance is $4,500."},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
}


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise ValueError("not json")
        return self._payload


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        mistral_api_key="k",
        mistral_base_url="https://upstream.invalid/v1",
        supabase_url=None,
        supabase_key=None,
        deepgram_api_key=None,
    )


def build(settings: Settings, payload: Any, status_code: int = 200):  # type: ignore[no-untyped-def]
    capture = CaptureQueue()
    app = create_app(settings, capture)

    # Replace the upstream client so no network call happens.
    class FakeClient:
        def post(self, *_args: Any, **_kwargs: Any) -> FakeResponse:
            return FakeResponse(payload, status_code)

    for route in app.router.routes:
        pass
    app.dependency_overrides = {}
    import adapter.proxy as proxy_module

    proxy_module.httpx.Client = lambda *a, **k: FakeClient()  # type: ignore[assignment]
    app_rebuilt = create_app(settings, capture)
    return TestClient(app_rebuilt), capture


def test_response_is_returned_unmodified(settings: Settings) -> None:
    client, _capture = build(settings, UPSTREAM_BODY)
    response = client.post("/v1/chat/completions", json={"model": "m", "messages": []})
    assert response.status_code == 200
    assert response.json() == UPSTREAM_BODY


def test_overhead_header_is_present_and_small(settings: Settings) -> None:
    client, _capture = build(settings, UPSTREAM_BODY)
    response = client.post("/v1/chat/completions", json={"model": "m", "messages": []})
    overhead = float(response.headers["x-echoproof-overhead-ms"])
    assert overhead < 50.0


def test_the_agent_turn_is_captured(settings: Settings) -> None:
    client, capture = build(settings, UPSTREAM_BODY)
    client.post("/v1/chat/completions", json={"model": "m", "messages": []})
    assert capture.stats()["captured"] == 1


def test_an_upstream_error_is_passed_through_untouched(settings: Settings) -> None:
    """Swallowing a 429 would hide a real condition from the client's retry."""
    client, _capture = build(settings, {"error": "rate limited"}, status_code=429)
    response = client.post("/v1/chat/completions", json={"model": "m", "messages": []})
    assert response.status_code == 429
    assert response.json() == {"error": "rate limited"}


def test_an_unparseable_upstream_body_does_not_fail_the_request(
    settings: Settings,
) -> None:
    client, capture = build(settings, ValueError("boom"))
    response = client.post("/v1/chat/completions", json={"model": "m", "messages": []})
    assert response.status_code == 200
    assert capture.stats()["captured"] == 0


def test_an_unrecognised_response_shape_costs_one_capture_not_the_call(
    settings: Settings,
) -> None:
    client, capture = build(settings, {"unexpected": "shape"})
    response = client.post("/v1/chat/completions", json={"model": "m", "messages": []})
    assert response.status_code == 200
    assert capture.stats()["captured"] == 0


def test_transcript_ingest_accepts_a_turn(settings: Settings) -> None:
    client, capture = build(settings, UPSTREAM_BODY)
    response = client.post(
        "/v1/transcripts", json={"transcript": "We sent a postcard.", "turn_id": "t1"}
    )
    assert response.status_code == 202
    assert capture.stats()["captured"] == 1


def test_transcript_ingest_rejects_an_empty_transcript(settings: Settings) -> None:
    client, _capture = build(settings, UPSTREAM_BODY)
    assert client.post("/v1/transcripts", json={"transcript": "  "}).status_code == 400


def test_a_full_queue_drops_rather_than_blocks() -> None:
    """Losing an adjudication is a gap in a report. Blocking is an outage."""
    capture = CaptureQueue(maxsize=2)
    started = time.perf_counter()
    accepted = [
        capture.submit(CapturedTurn(turn_id=str(i), transcript="t", source="proxy"))
        for i in range(5)
    ]
    elapsed = time.perf_counter() - started

    assert accepted[:2] == [True, True]
    assert accepted[2:] == [False, False, False]
    assert capture.stats()["dropped"] == 3
    assert elapsed < 1.0


def test_a_handler_that_raises_does_not_kill_the_worker() -> None:
    seen: list[str] = []

    def handler(turn: CapturedTurn) -> None:
        if turn.turn_id == "bad":
            raise RuntimeError("handler exploded")
        seen.append(turn.turn_id)

    capture = CaptureQueue(handler=handler)
    capture.start()
    for turn_id in ("good1", "bad", "good2"):
        capture.submit(CapturedTurn(turn_id=turn_id, transcript="t", source="proxy"))
    capture.drain()
    capture.stop()

    assert seen == ["good1", "good2"]
    assert capture.stats()["failed"] == 1


def test_extract_agent_text_tolerates_junk() -> None:
    assert extract_agent_text({}) == ""
    assert extract_agent_text({"choices": []}) == ""
    assert extract_agent_text({"choices": [{"message": {}}]}) == ""
    assert extract_agent_text(json.loads(json.dumps(UPSTREAM_BODY))) == (
        "Your balance is $4,500."
    )
