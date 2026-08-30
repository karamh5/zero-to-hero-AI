"""Detector tests -- statistics, adaptivity, and graceful degradation.

Every test here runs with zero hardware attached.
"""

from __future__ import annotations

import math
import random

import pytest

from core.contracts import EventType, Reading
from detectors.baseline import EwmaBaseline
from detectors.env_anomaly import EnvAnomalyDetector
from sensors.synthetic import SyntheticEnvSensor


def reading(temperature: float, humidity: float = 50.0, timestamp: float = 0.0) -> Reading:
    return Reading(
        timestamp=timestamp, temperature_c=temperature, humidity_pct=humidity, source="test"
    )


def feed(detector: EnvAnomalyDetector, temperature: float, humidity: float, count: int,
         noise: float = 0.3, seed: int = 0) -> None:
    """Push `count` quiet readings around a given operating point."""
    rng = random.Random(seed)
    for index in range(count):
        detector.update(
            reading(
                temperature + rng.gauss(0.0, noise),
                humidity + rng.gauss(0.0, noise),
                timestamp=float(index),
            )
        )


def statistics_only_detector(**overrides) -> EnvAnomalyDetector:
    """A detector with no model, so the statistical path is what is under test."""
    options = {
        "alpha": 0.05,
        "z_threshold": 3.5,
        "warmup_samples": 40,
        "window_size": 32,
        "model_path": None,
    }
    options.update(overrides)
    return EnvAnomalyDetector(**options)


# ---------------------------------------------------------------------------
# EwmaBaseline
# ---------------------------------------------------------------------------


class TestEwmaBaseline:
    def test_first_observation_seeds_the_mean(self):
        baseline = EwmaBaseline(alpha=0.1)
        assert baseline.observe(20.0) == 0.0
        assert baseline.mean == 20.0
        assert baseline.count == 1

    def test_mean_tracks_a_shifted_stream(self):
        baseline = EwmaBaseline(alpha=0.2)
        for _ in range(200):
            baseline.observe(30.0)
        assert baseline.mean == pytest.approx(30.0, abs=1e-6)

    def test_variance_is_learned_from_the_stream(self):
        baseline = EwmaBaseline(alpha=0.05, min_std=0.01)
        rng = random.Random(3)
        for _ in range(4000):
            baseline.observe(rng.gauss(10.0, 2.0))
        # EWMA variance is noisy by construction; a wide band is the honest check.
        assert 1.2 < baseline.std < 3.0

    def test_z_score_is_computed_before_absorbing_the_value(self):
        """An anomaly must not be allowed to dilute the baseline it is scored against."""
        baseline = EwmaBaseline(alpha=0.3, min_std=0.1)
        for _ in range(50):
            baseline.observe(20.0)
        mean_before = baseline.mean

        z = baseline.observe(30.0)
        expected = (30.0 - mean_before) / max(math.sqrt(baseline.var), 0.1)

        # The returned z reflects the pre-update baseline, so it is large...
        assert z > 50
        # ...and strictly larger than what the post-update baseline would give.
        assert z > expected

    def test_min_std_prevents_division_blowups_on_a_flat_stream(self):
        baseline = EwmaBaseline(alpha=0.1, min_std=0.2)
        for _ in range(100):
            baseline.observe(20.0)
        assert baseline.std == 0.2
        assert baseline.z_score(20.1) == pytest.approx(0.5)

    def test_clipping_bounds_how_far_one_reading_moves_the_baseline(self):
        """Winsorising: an anomaly must not poison the statistics detecting it.

        Regression test. Without this, a single large spike inflates the
        variance by more than an order of magnitude and the detector goes
        blind for a hundred-plus samples afterwards.
        """
        clipped = EwmaBaseline(alpha=0.1, min_std=0.2, clip_z=3.0)
        unclipped = EwmaBaseline(alpha=0.1, min_std=0.2, clip_z=None)
        for baseline in (clipped, unclipped):
            for _ in range(100):
                baseline.observe(20.0)

        clipped.observe(100.0)
        unclipped.observe(100.0)

        assert clipped.std < unclipped.std / 10
        assert abs(clipped.mean - 20.0) < abs(unclipped.mean - 20.0) / 10

    def test_clipping_does_not_dampen_the_reported_z_score(self):
        """Detection stays at full sensitivity; only the *update* is bounded."""
        clipped = EwmaBaseline(alpha=0.1, min_std=0.2, clip_z=3.0)
        unclipped = EwmaBaseline(alpha=0.1, min_std=0.2, clip_z=None)
        for baseline in (clipped, unclipped):
            for _ in range(100):
                baseline.observe(20.0)

        assert clipped.observe(100.0) == pytest.approx(unclipped.observe(100.0))

    def test_rejects_invalid_parameters(self):
        with pytest.raises(ValueError):
            EwmaBaseline(alpha=0.0)
        with pytest.raises(ValueError):
            EwmaBaseline(alpha=1.5)
        with pytest.raises(ValueError):
            EwmaBaseline(min_std=0.0)

    def test_reset_clears_state(self):
        baseline = EwmaBaseline()
        for _ in range(20):
            baseline.observe(15.0)
        baseline.reset()
        assert baseline.count == 0
        assert baseline.mean == 0.0


# ---------------------------------------------------------------------------
# EnvAnomalyDetector
# ---------------------------------------------------------------------------


class TestWarmup:
    def test_no_events_before_warmup_completes(self):
        detector = statistics_only_detector(warmup_samples=40)
        # Wild swings, but the detector has not earned the right to an opinion.
        events = [
            detector.update(reading(20.0 + (40.0 if index % 2 else 0.0), 50.0, index))
            for index in range(39)
        ]
        assert all(event is None for event in events)
        assert detector.is_warm is False

    def test_becomes_warm_after_enough_readings(self):
        detector = statistics_only_detector(warmup_samples=40)
        feed(detector, 20.0, 50.0, count=40)
        assert detector.is_warm is True


class TestAdaptiveThreshold:
    """The headline property: 'hot' is defined by recent history, not a constant."""

    def test_same_reading_is_an_event_in_one_climate_and_not_in_another(self):
        cool = statistics_only_detector()
        feed(cool, temperature=20.0, humidity=50.0, count=120, seed=1)

        hot = statistics_only_detector()
        feed(hot, temperature=30.0, humidity=50.0, count=120, seed=1)

        probe = reading(30.0, 50.0, timestamp=999.0)

        cool_event = cool.update(probe)
        hot_event = hot.update(probe)

        assert cool_event is not None, "30 C should be an event for a 20 C baseline"
        assert hot_event is None, "30 C should be unremarkable for a 30 C baseline"

    def test_baseline_migrates_so_a_new_normal_stops_firing(self):
        detector = statistics_only_detector()
        feed(detector, 20.0, 50.0, count=120, seed=2)

        # A step change fires at first...
        assert detector.update(reading(28.0, 50.0, 500.0)) is not None

        # ...but once 28 C is simply what this place is like, it goes quiet.
        feed(detector, 28.0, 50.0, count=300, seed=3)
        assert detector.update(reading(28.0, 50.0, 900.0)) is None

    def test_quiet_stream_produces_no_false_positives(self):
        detector = statistics_only_detector()
        feed(detector, 21.0, 55.0, count=60, seed=4)

        rng = random.Random(99)
        events = [
            detector.update(reading(21.0 + rng.gauss(0, 0.3), 55.0 + rng.gauss(0, 0.5), i))
            for i in range(600)
        ]
        fired = [event for event in events if event is not None]
        assert len(fired) <= 5, f"too many false positives: {len(fired)}/600"


class TestOutlierRobustness:
    """Regression tests for the bug where one spike blinded the detector."""

    def test_a_spike_does_not_blow_up_the_baseline_variance(self):
        detector = statistics_only_detector()
        feed(detector, 20.0, 50.0, count=150, seed=20)
        std_before = detector.status()["temperature_baseline"]["std"]

        detector.update(reading(45.0, 50.0, 500.0))  # a 25 C excursion
        std_after = detector.status()["temperature_baseline"]["std"]

        assert std_after < std_before * 2.0, (
            f"one spike inflated std from {std_before} to {std_after}"
        )

    def test_the_detector_still_sees_the_next_event_after_a_big_one(self):
        detector = statistics_only_detector()
        feed(detector, 20.0, 50.0, count=150, seed=21)

        first = detector.update(reading(45.0, 50.0, 500.0))
        assert first is not None

        # A short quiet gap, then a second excursion. This is the case that
        # used to fail: the first spike left the variance so large that the
        # second one scored well under the threshold.
        feed(detector, 20.0, 50.0, count=15, seed=22)
        second = detector.update(reading(35.0, 50.0, 600.0))

        assert second is not None, "detector went blind after the first event"


class TestEventDebouncing:
    """One ongoing condition is one event, not one per reading."""

    def test_a_sustained_condition_does_not_emit_every_cycle(self):
        detector = statistics_only_detector(refractory_samples=15)
        feed(detector, 20.0, 50.0, count=150, seed=40)

        # Hold a strong excursion for 40 consecutive readings.
        events = [detector.update(reading(45.0, 50.0, 700.0 + i)) for i in range(40)]
        fired = [event for event in events if event is not None]

        assert events[0] is not None, "the leading edge must always fire"
        assert 2 <= len(fired) <= 4, (
            f"40 readings of one condition produced {len(fired)} events"
        )

    def test_a_long_condition_still_re_reports_periodically(self):
        """Debouncing must not mean going silent on something still happening."""
        detector = statistics_only_detector(refractory_samples=10)
        feed(detector, 20.0, 50.0, count=150, seed=41)

        events = [detector.update(reading(45.0, 50.0, 700.0 + i)) for i in range(60)]
        fired = [event for event in events if event is not None]
        assert len(fired) >= 3

    def test_a_new_episode_after_a_quiet_gap_fires_immediately(self):
        detector = statistics_only_detector(refractory_samples=15)
        feed(detector, 20.0, 50.0, count=150, seed=42)

        assert detector.update(reading(45.0, 50.0, 700.0)) is not None
        feed(detector, 20.0, 50.0, count=40, seed=43)  # condition clears

        # A fresh excursion is a fresh leading edge, not a refractory tail.
        assert detector.update(reading(45.0, 50.0, 800.0)) is not None

    def test_refractory_can_be_disabled(self):
        detector = statistics_only_detector(refractory_samples=0)
        feed(detector, 20.0, 50.0, count=150, seed=44)

        events = [detector.update(reading(45.0, 50.0, 700.0 + i)) for i in range(10)]
        assert all(event is not None for event in events)


class TestDriftDetection:
    """A gradual ramp is invisible to a single fast baseline -- hence two."""

    def test_a_gradual_ramp_is_detected_as_drift(self):
        detector = statistics_only_detector(warmup_samples=60)
        feed(detector, 20.0, 50.0, count=500, seed=30)

        # 0.04 C per sample: slow enough that the fast baseline tracks it and
        # no single reading looks anomalous, but the slow baseline does not.
        events = [
            detector.update(reading(20.0 + 0.04 * step, 50.0, 2000.0 + step))
            for step in range(100)
        ]
        fired = [event for event in events if event is not None]

        assert fired, "a sustained ramp must eventually fire"
        assert any(event.event_type is EventType.DRIFT for event in fired), (
            f"expected a drift, got {[e.event_type.value for e in fired]}"
        )

    def test_a_ramp_that_slow_enough_stays_quiet_at_first(self):
        """Drift takes time to establish -- it must not fire on sample two."""
        detector = statistics_only_detector(warmup_samples=60)
        feed(detector, 20.0, 50.0, count=500, seed=31)

        early = [
            detector.update(reading(20.0 + 0.04 * step, 50.0, 2000.0 + step))
            for step in range(5)
        ]
        assert all(event is None for event in early)

    def test_a_flat_stream_does_not_trigger_the_slow_baseline(self):
        detector = statistics_only_detector(warmup_samples=60)
        feed(detector, 20.0, 50.0, count=400, seed=32)

        rng = random.Random(77)
        events = [
            detector.update(reading(20.0 + rng.gauss(0, 0.3), 50.0 + rng.gauss(0, 0.5), i))
            for i in range(800)
        ]
        fired = [event for event in events if event is not None]
        assert len(fired) <= 8, f"slow baseline caused {len(fired)} false positives"


class TestEventClassification:
    def test_upward_excursion_is_a_spike(self):
        detector = statistics_only_detector()
        feed(detector, 20.0, 50.0, count=120, seed=5)
        event = detector.update(reading(35.0, 50.0, 600.0))
        assert event is not None
        assert event.event_type is EventType.SPIKE
        assert event.z_temperature > 0

    def test_downward_excursion_is_a_drop(self):
        detector = statistics_only_detector()
        feed(detector, 20.0, 50.0, count=120, seed=6)
        event = detector.update(reading(5.0, 50.0, 600.0))
        assert event is not None
        assert event.event_type is EventType.DROP
        assert event.z_temperature < 0

    def test_humidity_surge_alone_is_enough_to_fire(self):
        detector = statistics_only_detector()
        feed(detector, 20.0, 50.0, count=120, seed=7)
        event = detector.update(reading(20.0, 90.0, 600.0))
        assert event is not None
        assert event.z_humidity > 0
        assert event.event_type is EventType.SPIKE

    def test_sustained_excursion_becomes_a_drift(self):
        # refractory_samples=0: this test is about the *label* a sustained
        # excursion gets, not about how often it is emitted. With debouncing on
        # (the shipped default) only the leading edge would fire, and the
        # detector would never reach the consecutive-run branch while emitting.
        detector = statistics_only_detector(sustained_samples=4, refractory_samples=0)
        feed(detector, 20.0, 50.0, count=120, seed=8)

        # A steadily climbing temperature, always ahead of the adapting baseline.
        events = []
        for step in range(12):
            events.append(detector.update(reading(24.0 + 3.0 * step, 50.0, 700.0 + step)))

        fired = [event for event in events if event is not None]
        assert fired, "a sustained climb should fire"
        assert any(event.event_type is EventType.DRIFT for event in fired)

    def test_confidence_grows_with_severity(self):
        mild = statistics_only_detector()
        feed(mild, 20.0, 50.0, count=120, seed=9)
        mild_event = mild.update(reading(21.5, 50.0, 600.0))

        wild = statistics_only_detector()
        feed(wild, 20.0, 50.0, count=120, seed=9)
        wild_event = wild.update(reading(60.0, 50.0, 600.0))

        assert mild_event is not None and wild_event is not None
        assert wild_event.confidence > mild_event.confidence
        assert 0.5 <= mild_event.confidence <= 1.0
        assert wild_event.confidence == pytest.approx(1.0)


class TestRobustness:
    def test_missing_model_degrades_instead_of_crashing(self):
        detector = EnvAnomalyDetector(
            warmup_samples=20, model_path="artifacts/does-not-exist.pt"
        )
        feed(detector, 20.0, 50.0, count=60, seed=10)
        event = detector.update(reading(40.0, 50.0, 600.0))

        assert event is not None
        assert detector.status()["model_ready"] is False
        assert "statistics" in event.detail

    def test_incomplete_readings_are_ignored(self):
        detector = statistics_only_detector(warmup_samples=5)
        partial = Reading(timestamp=0.0, temperature_c=25.0, humidity_pct=None, source="test")
        assert detector.update(partial) is None
        assert detector.status()["observed"] == 0

    def test_reset_returns_the_detector_to_cold(self):
        detector = statistics_only_detector()
        feed(detector, 20.0, 50.0, count=100, seed=11)
        assert detector.is_warm

        detector.reset()
        assert detector.is_warm is False
        assert detector.status()["observed"] == 0

    def test_events_carry_the_node_id_and_detector_name(self):
        detector = statistics_only_detector(node_id="node-under-test")
        feed(detector, 20.0, 50.0, count=120, seed=12)
        event = detector.update(reading(45.0, 50.0, 600.0))

        assert event is not None
        assert event.node_id == "node-under-test"
        assert event.detector == "env_anomaly"
        assert event.to_dict()["event_type"] in {"spike", "drop", "drift"}


class TestAgainstTheSyntheticSensor:
    """End-to-end sensor -> detector, still with no hardware."""

    def test_injected_episodes_are_detected(self):
        sensor = SyntheticEnvSensor(seed=42, anomaly_probability=0.0)
        detector = statistics_only_detector(warmup_samples=60)

        for _ in range(120):
            detector.update(sensor.read())

        sensor.force_episode(EventType.SPIKE, length=8)
        events = [detector.update(sensor.read()) for _ in range(8)]

        assert any(event is not None for event in events), "an injected spike must fire"

    def test_a_calm_synthetic_stream_stays_quiet(self):
        sensor = SyntheticEnvSensor(seed=7, anomaly_probability=0.0)
        detector = statistics_only_detector(warmup_samples=60)

        events = [detector.update(sensor.read()) for _ in range(500)]
        fired = [event for event in events if event is not None]
        assert len(fired) <= 8, f"anomaly-free stream fired {len(fired)} times"
