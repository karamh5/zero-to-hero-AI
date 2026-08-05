"""Shared, thread-safe state that the pipeline writes and the dashboard reads.

The pipeline runs on one thread, federation on another, and uvicorn serves
requests on others, so every mutation goes through a lock. Everything is a
bounded `deque`: a node left running for a week must not grow without limit.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from core.contracts import Event, Reading

#: Points kept for the chart. At the DHT22's 2s floor this is ~20 minutes.
MAX_READINGS = 600
#: Events kept for the scrolling log.
MAX_EVENTS = 200


class DashboardState:
    """Bounded, lock-guarded snapshot of everything the UI displays."""

    def __init__(self, max_readings: int = MAX_READINGS, max_events: int = MAX_EVENTS) -> None:
        self._lock = threading.Lock()
        self._readings: deque[dict[str, Any]] = deque(maxlen=max_readings)
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._risk: dict[str, Any] = {}
        self._federation: dict[str, Any] = {"enabled": False}
        self._cloud: dict[str, Any] = {}
        self._detector: dict[str, Any] = {}
        self._runtime: dict[str, Any] = {}
        self._poll_interval_s: float = 0.0
        self._started_at = time.time()
        self._reading_count = 0
        self._event_count = 0

    # -- writes ------------------------------------------------------------

    def add_reading(self, reading: Reading) -> None:
        with self._lock:
            self._readings.append(
                {
                    "timestamp": reading.timestamp,
                    "temperature_c": reading.temperature_c,
                    "humidity_pct": reading.humidity_pct,
                }
            )
            self._reading_count += 1

    def add_event(self, event: Event) -> None:
        with self._lock:
            self._events.append(event.to_dict())
            self._event_count += 1

    def set_risk(self, risk: dict[str, Any], poll_interval_s: float) -> None:
        with self._lock:
            self._risk = dict(risk)
            self._poll_interval_s = float(poll_interval_s)

    def set_federation(self, status: dict[str, Any]) -> None:
        with self._lock:
            self._federation = dict(status)

    def set_cloud(self, status: dict[str, Any]) -> None:
        with self._lock:
            self._cloud = dict(status)

    def set_detector(self, status: dict[str, Any]) -> None:
        with self._lock:
            self._detector = dict(status)

    def set_runtime(self, info: dict[str, Any]) -> None:
        with self._lock:
            self._runtime = dict(info)

    def reset(self) -> None:
        with self._lock:
            self._readings.clear()
            self._events.clear()
            self._reading_count = 0
            self._event_count = 0
            self._started_at = time.time()

    # -- reads -------------------------------------------------------------

    def snapshot(self, reading_limit: int = 240, event_limit: int = 50) -> dict[str, Any]:
        """Everything the page needs, in one JSON-serialisable dict."""
        with self._lock:
            readings = list(self._readings)[-reading_limit:]
            events = list(self._events)[-event_limit:]
            return {
                "runtime": dict(self._runtime),
                "uptime_s": round(time.time() - self._started_at, 1),
                "counters": {
                    "readings": self._reading_count,
                    "events": self._event_count,
                },
                "poll_interval_s": self._poll_interval_s,
                "risk": dict(self._risk),
                "detector": dict(self._detector),
                "federation": dict(self._federation),
                "cloud": dict(self._cloud),
                "readings": readings,
                # Newest first: the log scrolls downward from the top.
                "events": list(reversed(events)),
            }


#: Shared instance. The pipeline writes to it and the FastAPI app reads from
#: it, which keeps the two from having to know about each other.
STATE = DashboardState()
