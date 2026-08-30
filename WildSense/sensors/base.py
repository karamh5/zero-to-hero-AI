"""The sensor interface every pack implements.

A pack must answer three questions:
  * what is your name (for logs and Reading.source)?
  * how fast are you *physically* allowed to be read (`min_interval_s`)?
  * give me a Reading, or raise SensorReadError.

`min_interval_s` is the important one. The DHT22 cannot be read faster than
once every two seconds; the contextual-adaptation module must never be able to
request a faster poll than the hardware allows, so the pipeline clamps its
interval against this value rather than trusting config.
"""

from __future__ import annotations

import abc
import logging
import time

from core.contracts import Reading

log = logging.getLogger(__name__)


class SensorError(Exception):
    """Base class for sensor failures."""


class SensorReadError(SensorError):
    """A read failed after all permitted retries.

    The pipeline treats this as "skip this cycle", never as fatal.
    """


class BaseSensor(abc.ABC):
    """Abstract environmental sensor.

    Subclasses implement `_read_once`; this class provides the shared
    minimum-interval enforcement and the open/close lifecycle.
    """

    #: Config-facing name; also written into `Reading.source`.
    name: str = "base"

    def __init__(self, min_interval_s: float = 0.0) -> None:
        self._min_interval_s = float(min_interval_s)
        self._last_read_monotonic: float | None = None
        self._opened = False

    # -- lifecycle ---------------------------------------------------------

    @property
    def min_interval_s(self) -> float:
        """Shortest interval this hardware can be polled at, in seconds."""
        return self._min_interval_s

    def open(self) -> None:
        """Acquire hardware resources. Idempotent."""
        self._opened = True

    def close(self) -> None:
        """Release hardware resources. Idempotent and must never raise."""
        self._opened = False

    def __enter__(self) -> "BaseSensor":
        self.open()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- reading -----------------------------------------------------------

    @abc.abstractmethod
    def _read_once(self) -> Reading:
        """Perform a single read. Raise SensorReadError on failure."""

    def read(self) -> Reading:
        """Read the sensor, waiting first if we would violate min_interval_s.

        Every pack gets this protection for free, so no caller can accidentally
        hammer a device faster than its datasheet permits.
        """
        if not self._opened:
            self.open()
        self._respect_min_interval()
        reading = self._read_once()
        self._last_read_monotonic = time.monotonic()
        return reading

    def _respect_min_interval(self) -> None:
        if self._min_interval_s <= 0 or self._last_read_monotonic is None:
            return
        elapsed = time.monotonic() - self._last_read_monotonic
        remaining = self._min_interval_s - elapsed
        if remaining > 0:
            log.debug("%s: waiting %.2fs to respect min read interval", self.name, remaining)
            time.sleep(remaining)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} name={self.name!r} min_interval_s={self._min_interval_s}>"
