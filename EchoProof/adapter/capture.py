"""Turning captured exchanges into evidence, out of band.

The proxy's job is to return the upstream response and get out of the way.
Everything expensive happens here instead, on a worker thread, after the client
already has its answer.

That separation is the product argument, not an optimisation. The brief is
explicit that EchoProof must never become a production availability dependency:
the first dropped call attributable to the tool loses the account. So the
capture queue is bounded and drops rather than blocks when full. Losing an
adjudication is a gap in a pre-deployment report; blocking a live call is an
outage.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from core.hashing import hash_text
from engine.evidence import SPAN_AGENT_TURN, EvidenceLog

# Bounded on purpose. An unbounded queue turns a slow judge into unbounded
# memory growth in the client's own process.
QUEUE_MAXSIZE = 256


@dataclass
class CapturedTurn:
    """One agent turn observed by the proxy or submitted as a transcript."""

    turn_id: str
    transcript: str
    source: str  # "proxy" | "transcript_ingest"
    session_id: str = "default"
    request_model: str = ""
    audio_ref: str | None = None
    received_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    call_date: str = field(default_factory=lambda: date.today().isoformat())

    def to_span_payload(self) -> dict[str, Any]:
        """The agent.turn span from SPEC section 7.

        word_timings and stt_confidence are null here and populated by the audio
        stage when there is audio. A text-only turn genuinely has neither, and
        inventing empty values would make an absent measurement look like a
        measured zero.
        """
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "source": self.source,
            "transcript": self.transcript,
            "transcript_hash": hash_text(self.transcript),
            "audio_ref": self.audio_ref,
            "word_timings": None,
            "stt_confidence": None,
            "request_model": self.request_model,
            "received_at": self.received_at,
            "call_date": self.call_date,
        }


class CaptureQueue:
    """Bounded queue plus a worker thread that adjudicates captured turns."""

    def __init__(
        self,
        handler: Callable[[CapturedTurn], None] | None = None,
        maxsize: int = QUEUE_MAXSIZE,
    ) -> None:
        self._queue: queue.Queue[CapturedTurn | None] = queue.Queue(maxsize=maxsize)
        self._handler = handler
        self._worker: threading.Thread | None = None
        self._stopping = threading.Event()
        self.captured = 0
        self.dropped = 0
        self.processed = 0
        self.failed = 0

    def submit(self, turn: CapturedTurn) -> bool:
        """Enqueue without blocking. Returns False if the turn was dropped."""
        try:
            self._queue.put_nowait(turn)
        except queue.Full:
            self.dropped += 1
            return False
        self.captured += 1
        return True

    def start(self) -> None:
        if self._worker is not None:
            return
        self._worker = threading.Thread(target=self._run, name="echoproof-capture", daemon=True)
        self._worker.start()

    def _run(self) -> None:
        while not self._stopping.is_set():
            item = self._queue.get()
            if item is None:
                break
            try:
                if self._handler is not None:
                    self._handler(item)
                self.processed += 1
            except Exception as exc:  # noqa: BLE001 - a bad turn must not kill the worker
                self.failed += 1
                print(f"[capture] adjudication failed for {item.turn_id}: {exc}")
            finally:
                self._queue.task_done()

    def drain(self, timeout: float | None = None) -> None:
        """Block until the queue is empty. For scripts and tests, not serving."""
        self._queue.join()
        _ = timeout

    def stop(self) -> None:
        self._stopping.set()
        self._queue.put(None)
        if self._worker is not None:
            self._worker.join(timeout=5.0)
            self._worker = None

    def stats(self) -> dict[str, int]:
        return {
            "captured": self.captured,
            "processed": self.processed,
            "dropped": self.dropped,
            "failed": self.failed,
            "pending": self._queue.qsize(),
        }


def record_turn(log: EvidenceLog, turn: CapturedTurn) -> None:
    """Write the agent.turn span. Declared in Phase 1, first emitted here."""
    log.append(SPAN_AGENT_TURN, turn.to_span_payload())


def extract_agent_text(response_payload: dict[str, Any]) -> str:
    """Pull the agent's spoken text out of an OpenAI-shaped response.

    Tolerant by design. The proxy sits in front of somebody else's stack, and a
    response shape it does not recognise should cost one capture, not the call.
    """
    try:
        choices = response_payload.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return str(message.get("content") or "").strip()
    except AttributeError:
        return ""
