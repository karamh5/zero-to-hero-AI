"""The detector interface every pack implements.

A detector is a stateful stream processor: you feed it `Reading`s one at a
time in order, and it returns an `Event` when it decides something happened,
or `None` when it does not.

Deliberately *not* a batch API. Edge nodes see one reading at a time and must
decide immediately, so the interface reflects that.
"""

from __future__ import annotations

import abc

from core.contracts import Event, Reading


class BaseDetector(abc.ABC):
    """Abstract streaming detector."""

    #: Config-facing name; also recorded on emitted Events.
    name: str = "base"

    @abc.abstractmethod
    def update(self, reading: Reading) -> Event | None:
        """Consume one reading and optionally emit an event."""

    @abc.abstractmethod
    def reset(self) -> None:
        """Clear all learned state. Used between tests and on reconfiguration."""

    @property
    def is_warm(self) -> bool:
        """True once enough history exists for detections to be trustworthy.

        Detectors must return `None` from `update()` until this is True.
        Firing on the first few readings would just be reporting noise.
        """
        return True

    def status(self) -> dict:
        """Introspection for the dashboard. Override to add pack-specific fields."""
        return {"name": self.name, "warm": self.is_warm}
