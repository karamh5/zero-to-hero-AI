"""Data contracts shared by every WildSense module.

These are the only types that cross module boundaries. A sensor pack produces
`Reading`s; a detector pack consumes `Reading`s and produces `Event`s. Nothing
else in the system needs to know how a sensor works or how a detector decides.

Keeping this file tiny and dependency-free is deliberate: it is the seam that
lets a future sensor pack (thermal camera, air quality, ...) drop in without
touching the core.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """The event classes the detector can report.

    Inherits from `str` so it serialises straight to JSON and compares cleanly
    against plain strings in configs and tests.

    NONE   -- reading is consistent with the recent baseline.
    SPIKE  -- sharp upward excursion (a heat spike, or a humidity surge).
    DROP   -- sharp downward excursion (a cold front, or humidity collapse).
    DRIFT  -- slow but sustained movement away from the baseline.
    """

    NONE = "none"
    SPIKE = "spike"
    DROP = "drop"
    DRIFT = "drift"

    @classmethod
    def ordered(cls) -> list["EventType"]:
        """Canonical class order used by the classifier's output layer.

        The index of each member here IS its integer label during training and
        inference. Never reorder this without retraining the model.
        """
        return [cls.NONE, cls.SPIKE, cls.DROP, cls.DRIFT]

    @classmethod
    def from_index(cls, index: int) -> "EventType":
        return cls.ordered()[index]

    @property
    def index(self) -> int:
        return EventType.ordered().index(self)


def utc_iso(timestamp: float) -> str:
    """Format a POSIX timestamp as an ISO-8601 UTC string."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


@dataclass(frozen=True)
class Reading:
    """One environmental sample from one sensor.

    `temperature_c` and `humidity_pct` are optional because a future sensor
    pack may only supply one of them (or neither -- a thermal camera pack
    would put its frame in `metadata`). Detectors must tolerate `None`.
    """

    timestamp: float
    temperature_c: float | None = None
    humidity_pct: float | None = None
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def now(cls, **kwargs: Any) -> "Reading":
        return cls(timestamp=time.time(), **kwargs)

    @property
    def is_complete(self) -> bool:
        """True when both environmental channels are present."""
        return self.temperature_c is not None and self.humidity_pct is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "iso_time": utc_iso(self.timestamp),
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class Event:
    """A detection: something in the environment deviated from its baseline.

    This is exactly the payload that gets snapshotted to S3, shown in the
    dashboard's event log, and asserted against in tests.
    """

    timestamp: float
    event_type: EventType
    confidence: float
    temperature_c: float | None = None
    humidity_pct: float | None = None
    z_temperature: float | None = None
    z_humidity: float | None = None
    node_id: str = "wildsense-node"
    detector: str = "unknown"
    # Human-readable one-liner explaining *why* this fired. Shown in the
    # dashboard log and invaluable when reviewing snapshots after the fact.
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "iso_time": utc_iso(self.timestamp),
            "event_type": self.event_type.value,
            "confidence": round(self.confidence, 4),
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "z_temperature": (
                None if self.z_temperature is None else round(self.z_temperature, 3)
            ),
            "z_humidity": (
                None if self.z_humidity is None else round(self.z_humidity, 3)
            ),
            "node_id": self.node_id,
            "detector": self.detector,
            "detail": self.detail,
        }
