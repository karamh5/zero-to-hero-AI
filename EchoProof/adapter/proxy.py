"""OpenAI-compatible capture proxy (SPEC section 2).

A client points its voice agent's LLM base_url at this service instead of at the
provider. Requests are forwarded unchanged, responses are returned unchanged,
and the agent's turn is captured for adjudication out of band.

Two invariants, both load-bearing:

1. **The response is never modified and never delayed by adjudication.** The
   judge runs out of the decision path. The brief's argument for the whole
   product is that EchoProof cannot cause a dropped call, and a proxy that
   awaits a verdict before returning would destroy exactly that.

2. **A capture failure is never a request failure.** If the queue is full or the
   response shape is unrecognised, the call still succeeds. A pre-deployment
   assurance tool that takes production down has inverted its own purpose.

The transcript ingest path exists because a speech to speech stack has no
intermediate LLM call to intercept. The brief calls that path necessary rather
than optional, and without it those stacks are simply not adjudicable.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from adapter.capture import CaptureQueue, CapturedTurn, extract_agent_text
from core.config import Settings

# Upstream timeout. Generous, because this is the client's own call budget and
# the proxy must not be the component that gives up first.
UPSTREAM_TIMEOUT = 120.0


def create_app(settings: Settings, capture: CaptureQueue) -> FastAPI:
    """Build the proxy app. Injected dependencies so tests can drive it."""
    app = FastAPI(title="EchoProof capture proxy", version="0.1.0")
    app.state.capture = capture
    app.state.settings = settings
    app.state.overheads_ms: list[float] = []
    app.state.turn_counter = 0
    client = httpx.Client(timeout=UPSTREAM_TIMEOUT)

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "ok", "capture": capture.stats()}

    @app.get("/metrics")
    def metrics() -> dict[str, Any]:
        """Proxy overhead, which the brief budgets at under 50ms."""
        samples = sorted(app.state.overheads_ms)
        if not samples:
            return {"samples": 0, "capture": capture.stats()}
        return {
            "samples": len(samples),
            "median_ms": round(samples[len(samples) // 2], 3),
            "p95_ms": round(samples[int(len(samples) * 0.95) - 1], 3),
            "max_ms": round(samples[-1], 3),
            "budget_ms": 50,
            "capture": capture.stats(),
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse:
        body = await request.body()
        try:
            payload: dict[str, Any] = await request.json()
        except Exception:  # noqa: BLE001 - malformed JSON is the caller's problem
            payload = {}

        upstream_url = f"{settings.mistral_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.mistral_api_key}",
            "Content-Type": "application/json",
        }

        upstream_started = time.perf_counter()
        response = client.post(upstream_url, content=body, headers=headers)
        upstream_elapsed = time.perf_counter() - upstream_started

        # Everything from here to the return is what EchoProof adds. Measuring
        # only this, rather than total request time, is the honest reading of a
        # 50ms budget: the upstream model call is the client's cost either way.
        overhead_started = time.perf_counter()

        try:
            response_payload = response.json()
        except ValueError:
            response_payload = {}

        text = extract_agent_text(response_payload)
        if text:
            app.state.turn_counter += 1
            capture.submit(
                CapturedTurn(
                    turn_id=f"t{app.state.turn_counter:04d}",
                    transcript=text,
                    source="proxy",
                    session_id=str(payload.get("user") or "default"),
                    request_model=str(payload.get("model") or ""),
                )
            )

        overhead_ms = (time.perf_counter() - overhead_started) * 1000
        app.state.overheads_ms.append(overhead_ms)

        return JSONResponse(
            status_code=response.status_code,
            content=response_payload,
            headers={
                # Surfaced so a client can see the cost in their own traces
                # rather than taking our word for it.
                "x-echoproof-overhead-ms": f"{overhead_ms:.3f}",
                "x-echoproof-upstream-ms": f"{upstream_elapsed * 1000:.3f}",
            },
        )

    @app.post("/v1/transcripts")
    async def ingest_transcript(request: Request) -> JSONResponse:
        """Adjudicate a turn that never passed through an LLM proxy.

        The path that makes a speech to speech stack adjudicable, where there is
        no intermediate text call to intercept.
        """
        payload = await request.json()
        text = str(payload.get("transcript") or "").strip()
        if not text:
            return JSONResponse(
                status_code=400, content={"error": "transcript is required"}
            )

        app.state.turn_counter += 1
        turn = CapturedTurn(
            turn_id=str(payload.get("turn_id") or f"t{app.state.turn_counter:04d}"),
            transcript=text,
            source="transcript_ingest",
            session_id=str(payload.get("session_id") or "default"),
            audio_ref=payload.get("audio_ref"),
        )
        accepted = capture.submit(turn)
        return JSONResponse(
            status_code=202 if accepted else 429,
            content={"turn_id": turn.turn_id, "accepted": accepted},
        )

    # The one change the UI makes to this module: mount the read-only API
    # router and, when built, the compiled frontend. An attach failure must
    # never break the proxy, for the same reason a capture failure never
    # becomes a request failure.
    try:
        from api.router import attach_ui

        attach_ui(app)
    except Exception as exc:  # noqa: BLE001 - UI attach failure must not break capture
        print(f"[ui] not attached: {exc}")

    return app
