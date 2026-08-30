"""Synthetic environmental sensor -- the fallback that makes everything testable.

This module is the single source of truth for what a WildSense anomaly *looks
like*. Both of these use the shapes defined here:

  * `SyntheticEnvSensor`, which streams live-ish readings for demos and tests
  * `detectors/train.py`, which builds labelled windows to train the classifier

Keeping one definition means the model is trained on the same phenomena the
demo produces -- if you change what a "spike" means, both sides move together.

The generator is deterministic given a seed, which is what lets the detector
and federation tests assert on exact behaviour with zero hardware attached.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, replace
from typing import Iterator

from core.contracts import EventType, Reading
from core.registry import register_sensor
from sensors.base import BaseSensor

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Climate profiles
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClimateProfile:
    """The 'personality' of a location's weather.

    Federated nodes each get a different profile, which is the whole reason
    federation is interesting: a 34 C reading is unremarkable in `arid` and
    alarming in `alpine`, so each node's local baseline differs while the
    shared model still learns a transferable notion of "spike".
    """

    name: str = "temperate"
    base_temp_c: float = 21.0
    base_humidity_pct: float = 55.0
    #: Peak-to-trough swing of the daily temperature cycle.
    diurnal_amplitude_c: float = 5.0
    #: Std-dev of the per-sample sensor/turbulence noise.
    temp_noise_c: float = 0.18
    humidity_noise_pct: float = 0.55
    #: Std-dev of the slow random walk that makes the series non-stationary.
    temp_walk_c: float = 0.05
    humidity_walk_pct: float = 0.15
    #: Seconds of simulated time per sample (drives the diurnal phase).
    seconds_per_sample: float = 2.0


#: Profiles used by the federated simulation. Deliberately spread out so the
#: averaged model has to generalise rather than memorise one climate.
CLIMATE_PROFILES: dict[str, ClimateProfile] = {
    "temperate": ClimateProfile(
        name="temperate", base_temp_c=21.0, base_humidity_pct=58.0, diurnal_amplitude_c=5.0
    ),
    "coastal": ClimateProfile(
        name="coastal",
        base_temp_c=16.5,
        base_humidity_pct=78.0,
        diurnal_amplitude_c=3.0,
        humidity_noise_pct=0.9,
    ),
    "arid": ClimateProfile(
        name="arid",
        base_temp_c=33.0,
        base_humidity_pct=18.0,
        diurnal_amplitude_c=11.0,
        temp_noise_c=0.30,
    ),
    "alpine": ClimateProfile(
        name="alpine",
        base_temp_c=6.0,
        base_humidity_pct=64.0,
        diurnal_amplitude_c=7.5,
        temp_noise_c=0.22,
    ),
    "boreal": ClimateProfile(
        name="boreal", base_temp_c=12.0, base_humidity_pct=70.0, diurnal_amplitude_c=6.0
    ),
}


def get_profile(name: str) -> ClimateProfile:
    """Look up a named climate profile, defaulting to `temperate`."""
    if name not in CLIMATE_PROFILES:
        log.warning("Unknown climate profile '%s'; falling back to 'temperate'", name)
        return CLIMATE_PROFILES["temperate"]
    return CLIMATE_PROFILES[name]


# ---------------------------------------------------------------------------
# Anomaly shapes -- shared by the live sensor and the training data generator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnomalyEpisode:
    """A scripted excursion applied on top of the baseline series.

    `kind`      which EventType this episode represents
    `channel`   which measurement drives it ("temperature" or "humidity")
    `magnitude` full-scale offset in that channel's units
    `length`    how many samples the episode lasts
    """

    kind: EventType
    channel: str
    magnitude: float
    length: int


def episode_offsets(episode: AnomalyEpisode, step: int) -> tuple[float, float]:
    """Return (delta_temperature_c, delta_humidity_pct) at `step` of an episode.

    Shapes, chosen to look like the real phenomena:

      SPIKE/DROP -- a fast rising edge (`frac ** 0.6`) reaching full magnitude
                    at the final sample. We model the *rising* edge because
                    that is the part a detector sees while the event unfolds.
      DRIFT      -- a straight linear ramp across the whole episode, which is
                    what a slow-moving front or a smouldering fire looks like.

    Temperature and humidity are anti-correlated in real air: hot air holds
    less relative humidity. The cross-channel terms below encode that, which
    also gives the classifier a second, corroborating signal.
    """
    if episode.length <= 1:
        frac = 1.0
    else:
        frac = step / (episode.length - 1)
    frac = min(max(frac, 0.0), 1.0)

    if episode.kind is EventType.DRIFT:
        shape = frac
    else:
        shape = frac**0.6

    amount = shape * episode.magnitude

    if episode.channel == "temperature":
        if episode.kind is EventType.DROP:
            # Cold front: temperature falls, humidity climbs.
            return -amount, +0.55 * amount
        # Heat spike or warming drift: temperature rises, humidity falls off.
        return +amount, -0.45 * amount

    # Humidity-driven episode (e.g. a moisture surge rolling in).
    if episode.kind is EventType.DROP:
        return +0.10 * amount, -amount
    return -0.10 * amount, +amount


def sample_episode(rng: random.Random, kind: EventType, length: int | None = None) -> AnomalyEpisode:
    """Draw a random episode of the requested kind.

    Magnitudes are picked to be clearly detectable but not cartoonish, and are
    expressed in absolute units so they stay meaningful across climates.
    """
    channel = "temperature" if rng.random() < 0.65 else "humidity"

    if kind is EventType.SPIKE:
        span = length or rng.randint(4, 10)
        magnitude = rng.uniform(6.0, 14.0) if channel == "temperature" else rng.uniform(16.0, 32.0)
    elif kind is EventType.DROP:
        span = length or rng.randint(4, 10)
        magnitude = rng.uniform(5.0, 11.0) if channel == "temperature" else rng.uniform(14.0, 28.0)
    elif kind is EventType.DRIFT:
        # Drift is slow: small per-step change, large total change.
        span = length or rng.randint(18, 34)
        magnitude = rng.uniform(4.0, 9.0) if channel == "temperature" else rng.uniform(12.0, 24.0)
    else:  # EventType.NONE -- a no-op episode, used to keep call sites uniform.
        return AnomalyEpisode(EventType.NONE, channel, 0.0, length or 1)

    return AnomalyEpisode(kind, channel, magnitude, span)


# ---------------------------------------------------------------------------
# The baseline series generator
# ---------------------------------------------------------------------------


class ClimateSeries:
    """Deterministic baseline temperature/humidity walk for one profile.

    Separated from the sensor so `train.py` can generate thousands of samples
    without going through the sensor lifecycle.
    """

    def __init__(self, profile: ClimateProfile, seed: int = 0) -> None:
        self.profile = profile
        self._rng = random.Random(seed)
        self._step = 0
        self._temp_walk = 0.0
        self._humidity_walk = 0.0

    @property
    def rng(self) -> random.Random:
        return self._rng

    def next(self) -> tuple[float, float]:
        """Advance one sample and return (temperature_c, humidity_pct)."""
        p = self.profile

        # Slow random walk, mean-reverting so it cannot wander off forever.
        self._temp_walk = 0.97 * self._temp_walk + self._rng.gauss(0.0, p.temp_walk_c)
        self._humidity_walk = 0.97 * self._humidity_walk + self._rng.gauss(
            0.0, p.humidity_walk_pct
        )

        # Daily cycle. One full period per simulated 24h.
        seconds = self._step * p.seconds_per_sample
        phase = 2.0 * math.pi * (seconds / 86_400.0)
        diurnal = 0.5 * p.diurnal_amplitude_c * math.sin(phase)

        temperature = (
            p.base_temp_c + diurnal + self._temp_walk + self._rng.gauss(0.0, p.temp_noise_c)
        )
        # Humidity moves opposite to the daily temperature swing.
        humidity = (
            p.base_humidity_pct
            - 1.6 * diurnal
            + self._humidity_walk
            + self._rng.gauss(0.0, p.humidity_noise_pct)
        )

        self._step += 1
        return temperature, clamp_humidity(humidity)


def clamp_humidity(value: float) -> float:
    """Relative humidity is a percentage; the DHT22 cannot report outside 0-100."""
    return min(max(value, 0.0), 100.0)


def clamp_temperature(value: float) -> float:
    """DHT22 measurement range, per datasheet."""
    return min(max(value, -40.0), 80.0)


# ---------------------------------------------------------------------------
# The sensor pack
# ---------------------------------------------------------------------------


@register_sensor("synthetic")
class SyntheticEnvSensor(BaseSensor):
    """Generates a believable temperature/humidity stream with injected anomalies.

    Two clocks are in play and it matters which is which:

      * `Reading.timestamp` is always real wall-clock time, exactly as it
        would be on hardware. Everything downstream (risk escalation windows,
        the dashboard chart, S3 key paths) can therefore treat synthetic and
        real readings identically.
      * `seconds_per_sample` is *simulated* time and only drives the diurnal
        cycle, so a demo can show a day's temperature swing in a minute.

    `min_interval_s` (default 0) is wall-clock pacing. Left at 0 the sensor
    returns instantly, so a 500-sample test finishes in milliseconds; the
    pipeline handles its own sleep between cycles.

    Anomalies are injected as episodes: once one starts, it plays out over
    several consecutive samples, exactly like a real front moving through.

    Args:
        profile: name of a `CLIMATE_PROFILES` entry.
        seed: makes the whole stream reproducible.
        anomaly_probability: per-sample chance of starting a new episode
            while none is active.
        quiet_samples: minimum number of normal samples after an episode ends
            before another can start, so the baseline has time to settle.
        min_interval_s: wall-clock pacing; keep at 0 for tests.
    """

    name = "synthetic"

    def __init__(
        self,
        profile: str = "temperate",
        seed: int = 1337,
        anomaly_probability: float = 0.02,
        quiet_samples: int = 25,
        seconds_per_sample: float | None = None,
        min_interval_s: float = 0.0,
    ) -> None:
        super().__init__(min_interval_s=min_interval_s)

        base_profile = get_profile(profile)
        if seconds_per_sample is not None:
            base_profile = replace(base_profile, seconds_per_sample=float(seconds_per_sample))

        self.profile = base_profile
        self.seed = int(seed)
        self.anomaly_probability = float(anomaly_probability)
        self.quiet_samples = int(quiet_samples)

        self._series = ClimateSeries(base_profile, seed=self.seed)
        self._rng = random.Random(self.seed + 9001)

        self._episode: AnomalyEpisode | None = None
        self._episode_step = 0
        self._cooldown = self.quiet_samples

    # -- introspection used by tests and the dashboard ---------------------

    @property
    def active_episode(self) -> AnomalyEpisode | None:
        """The episode currently playing, if any. Ground truth for tests."""
        return self._episode

    def force_episode(self, kind: EventType, length: int | None = None) -> AnomalyEpisode:
        """Start a specific anomaly right now.

        Used by tests and by `run.py --demo` so a screen recording is
        guaranteed to contain each event type rather than waiting on chance.
        """
        episode = sample_episode(self._rng, kind, length)
        self._episode = episode
        self._episode_step = 0
        return episode

    # -- BaseSensor --------------------------------------------------------

    def _read_once(self) -> Reading:
        temperature, humidity = self._series.next()

        # Decide whether to start an episode, then apply whichever is running.
        self._maybe_start_episode()
        label = EventType.NONE

        if self._episode is not None:
            d_temp, d_humidity = episode_offsets(self._episode, self._episode_step)
            temperature += d_temp
            humidity += d_humidity
            label = self._episode.kind

            self._episode_step += 1
            if self._episode_step >= self._episode.length:
                log.debug("Synthetic episode finished: %s", self._episode.kind.value)
                self._episode = None
                self._episode_step = 0
                self._cooldown = self.quiet_samples
        elif self._cooldown > 0:
            self._cooldown -= 1

        return Reading.now(
            temperature_c=round(clamp_temperature(temperature), 2),
            humidity_pct=round(clamp_humidity(humidity), 2),
            source=f"{self.name}:{self.profile.name}",
            metadata={
                # Ground-truth label. Real hardware obviously cannot provide
                # this; it exists so tests and demos can score the detector.
                "truth_label": label.value,
                "climate": self.profile.name,
            },
        )

    def _maybe_start_episode(self) -> None:
        if self._episode is not None or self._cooldown > 0:
            return
        if self._rng.random() >= self.anomaly_probability:
            return
        kind = self._rng.choice([EventType.SPIKE, EventType.DROP, EventType.DRIFT])
        self._episode = sample_episode(self._rng, kind)
        self._episode_step = 0
        log.debug(
            "Synthetic episode starting: %s on %s (magnitude %.1f, %d samples)",
            self._episode.kind.value,
            self._episode.channel,
            self._episode.magnitude,
            self._episode.length,
        )

    # -- convenience -------------------------------------------------------

    def stream(self, count: int) -> Iterator[Reading]:
        """Yield `count` readings. Handy in tests and training data generation."""
        for _ in range(count):
            yield self.read()
