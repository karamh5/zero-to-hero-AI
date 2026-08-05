"""Contextual adaptation: risk level in, polling interval out.

The idea is that a node should not sample at a fixed rate. When the
surrounding context says conditions are dangerous, poll as fast as the
hardware allows; when nothing is happening, back off and save power and sensor
wear. On a solar-powered node the difference between a 2s and a 60s cadence is
the difference between surviving the night and not.

The external data source is mocked (a real deployment would call a fire-danger
API, a weather service, or a satellite hotspot feed), but the *mechanism*
around it is real and running: providers are swappable behind one interface,
and `PollingPolicy` is what the pipeline actually asks for its sleep duration
every single cycle.

The one hard rule: the interval is always clamped to the active sensor's
`min_interval_s`. A config or an over-excited risk provider must never be able
to poll a DHT22 faster than its 2-second floor.
"""

from __future__ import annotations

import abc
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum

from core.contracts import Event

log = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Ordered risk bands. Values match the keys used in `config.yaml`."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

    @classmethod
    def ordered(cls) -> list["RiskLevel"]:
        return [cls.LOW, cls.MODERATE, cls.HIGH, cls.EXTREME]

    @property
    def rank(self) -> int:
        return RiskLevel.ordered().index(self)

    @classmethod
    def from_rank(cls, rank: int) -> "RiskLevel":
        levels = cls.ordered()
        return levels[min(max(rank, 0), len(levels) - 1)]

    @classmethod
    def parse(cls, value: str | "RiskLevel") -> "RiskLevel":
        if isinstance(value, RiskLevel):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            log.warning("Unknown risk level %r; treating as 'moderate'", value)
            return cls.MODERATE


@dataclass(frozen=True)
class RiskAssessment:
    """A risk reading, with enough provenance to display and debug it."""

    level: RiskLevel
    #: 0.0-1.0 continuous score, used for the dashboard gauge needle.
    score: float
    source: str
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "rank": self.level.rank,
            "score": round(self.score, 3),
            "source": self.source,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class BaseRiskProvider(abc.ABC):
    """Source of the current risk level.

    Swap the implementation, not the pipeline. A real provider would call an
    external service here; everything downstream stays identical.
    """

    name = "base"

    @abc.abstractmethod
    def assess(self, recent_events: list[Event] | None = None) -> RiskAssessment:
        """Return the current risk. Must never raise or block for long."""


class StaticRiskProvider(BaseRiskProvider):
    """Fixed risk from config. Useful for pinning a demo to one cadence."""

    name = "static"

    def __init__(self, level: str = "moderate") -> None:
        self.level = RiskLevel.parse(level)

    def assess(self, recent_events: list[Event] | None = None) -> RiskAssessment:
        return RiskAssessment(
            level=self.level,
            score=(self.level.rank + 0.5) / len(RiskLevel.ordered()),
            source=self.name,
            reason="fixed level from config",
        )


class MockExternalRiskProvider(BaseRiskProvider):
    """Stands in for an external fire-danger feed, with local event feedback.

    Two inputs combine into one score:

      * a slow ambient cycle, standing in for a regional forecast that drifts
        over hours rather than seconds
      * an escalation term driven by what this node has actually detected
        recently -- a node that just saw three heat spikes should not be
        waiting 60 seconds for its next reading

    The event-feedback half is genuinely closed-loop: detections raise the
    risk, the raised risk shortens the polling interval, and the shorter
    interval produces more readings. That loop is the part worth demonstrating;
    only the ambient forecast is fake.

    Args:
        cycle_seconds: period of the ambient cycle.
        event_window_s: how far back detections count toward escalation.
        events_for_escalation: detections within the window needed to add one
            full risk band.
        seed: reproducible jitter.
        base_level: floor for the ambient cycle.
    """

    name = "mock_external"

    def __init__(
        self,
        cycle_seconds: float = 120.0,
        event_window_s: float = 90.0,
        events_for_escalation: int = 2,
        base_level: str = "low",
        seed: int = 7,
        clock: object | None = None,
    ) -> None:
        self.cycle_seconds = max(1.0, float(cycle_seconds))
        self.event_window_s = float(event_window_s)
        self.events_for_escalation = max(1, int(events_for_escalation))
        self.base_rank = RiskLevel.parse(base_level).rank
        self._rng = random.Random(seed)
        self._clock = clock if callable(clock) else time.time
        self._origin = self._clock()

    def assess(self, recent_events: list[Event] | None = None) -> RiskAssessment:
        elapsed = self._clock() - self._origin

        # Ambient forecast: a slow sawtooth over the bands above `base_rank`,
        # plus a little jitter so the demo does not look scripted.
        span = len(RiskLevel.ordered()) - self.base_rank
        phase = (elapsed % self.cycle_seconds) / self.cycle_seconds
        ambient_rank = self.base_rank + int(phase * span)
        jitter = self._rng.uniform(-0.15, 0.15)

        # Escalation from this node's own recent detections.
        now = self._clock()
        recent = [
            event
            for event in (recent_events or [])
            if now - event.timestamp <= self.event_window_s
        ]
        escalation = len(recent) // self.events_for_escalation

        rank = min(ambient_rank + escalation, len(RiskLevel.ordered()) - 1)
        level = RiskLevel.from_rank(rank)
        score = min(1.0, max(0.0, (rank + 0.5) / len(RiskLevel.ordered()) + jitter))

        reason = f"forecast band {RiskLevel.from_rank(ambient_rank).value}"
        if escalation:
            reason += f", escalated +{escalation} by {len(recent)} recent detections"

        return RiskAssessment(level=level, score=score, source=self.name, reason=reason)


def build_risk_provider(kind: str, options: dict | None = None) -> BaseRiskProvider:
    """Construct a provider by config name."""
    options = dict(options or {})
    if kind == "static":
        return StaticRiskProvider(**options)
    if kind == "mock_external":
        return MockExternalRiskProvider(**options)
    raise ValueError(
        f"unknown risk provider '{kind}'; expected 'static' or 'mock_external'"
    )


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


#: Sensible defaults if config omits the mapping. High risk polls at the
#: DHT22's floor; low risk backs right off.
DEFAULT_INTERVALS: dict[RiskLevel, float] = {
    RiskLevel.LOW: 60.0,
    RiskLevel.MODERATE: 30.0,
    RiskLevel.HIGH: 5.0,
    RiskLevel.EXTREME: 2.0,
}


class PollingPolicy:
    """Turns a risk level into a legal polling interval.

    Args:
        intervals: risk level name -> seconds. Missing levels use the defaults.
        sensor_min_interval_s: the active sensor's hardware floor. This is the
            clamp that makes the whole mechanism safe.
        max_interval_s: upper bound, so a misconfiguration cannot silence a node.
    """

    def __init__(
        self,
        intervals: dict[str, float] | None = None,
        sensor_min_interval_s: float = 0.0,
        max_interval_s: float = 300.0,
    ) -> None:
        self.sensor_min_interval_s = float(sensor_min_interval_s)
        self.max_interval_s = float(max_interval_s)

        self.intervals: dict[RiskLevel, float] = dict(DEFAULT_INTERVALS)
        for name, seconds in (intervals or {}).items():
            self.intervals[RiskLevel.parse(name)] = float(seconds)

        clamped = {
            level.value: self.interval_for(level) for level in RiskLevel.ordered()
        }
        log.info("Polling policy (seconds by risk): %s", clamped)

    def interval_for(self, level: RiskLevel) -> float:
        """Legal polling interval for a risk level, in seconds."""
        requested = self.intervals.get(level, DEFAULT_INTERVALS[level])
        floor = max(self.sensor_min_interval_s, 0.0)
        return min(max(requested, floor), self.max_interval_s)

    def interval_for_assessment(self, assessment: RiskAssessment) -> float:
        return self.interval_for(assessment.level)
