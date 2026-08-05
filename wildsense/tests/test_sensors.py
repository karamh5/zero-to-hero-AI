"""Sensor tests.

The DHT22 tests inject fake `board` / `adafruit_dht` modules into `sys.modules`
so the real import path in `dht22.py` is exercised on a machine with no GPIO.
That is the point: the retry logic is the part most likely to be wrong, and it
is the part hardest to test on actual hardware (you cannot ask a real sensor to
fail on demand).
"""

from __future__ import annotations

import sys
import time
import types

import pytest

from core.contracts import EventType, Reading
from sensors.base import BaseSensor, SensorError, SensorReadError
from sensors.dht22 import DHT22_MIN_INTERVAL_S, DHT22Sensor
from sensors.synthetic import (
    CLIMATE_PROFILES,
    SyntheticEnvSensor,
    episode_offsets,
    get_profile,
    sample_episode,
)


# ---------------------------------------------------------------------------
# BaseSensor
# ---------------------------------------------------------------------------


class CountingSensor(BaseSensor):
    """Minimal pack used to test the shared BaseSensor behaviour."""

    name = "counting"

    def __init__(self, min_interval_s: float = 0.0) -> None:
        super().__init__(min_interval_s=min_interval_s)
        self.reads = 0
        self.opens = 0
        self.closes = 0

    def open(self) -> None:
        self.opens += 1
        super().open()

    def close(self) -> None:
        self.closes += 1
        super().close()

    def _read_once(self) -> Reading:
        self.reads += 1
        return Reading.now(temperature_c=20.0, humidity_pct=50.0, source=self.name)


class TestBaseSensor:
    def test_read_opens_the_sensor_lazily(self):
        sensor = CountingSensor()
        sensor.read()
        assert sensor.opens == 1

    def test_context_manager_opens_and_closes(self):
        sensor = CountingSensor()
        with sensor:
            sensor.read()
        assert sensor.opens >= 1
        assert sensor.closes == 1

    def test_minimum_interval_is_enforced_between_reads(self):
        sensor = CountingSensor(min_interval_s=0.25)
        sensor.read()
        started = time.monotonic()
        sensor.read()
        assert time.monotonic() - started >= 0.24

    def test_no_wait_when_the_interval_is_zero(self):
        sensor = CountingSensor(min_interval_s=0.0)
        started = time.monotonic()
        for _ in range(50):
            sensor.read()
        assert time.monotonic() - started < 0.5


# ---------------------------------------------------------------------------
# SyntheticEnvSensor
# ---------------------------------------------------------------------------


class TestSyntheticSensor:
    def test_same_seed_gives_an_identical_stream(self):
        left = [r.temperature_c for r in SyntheticEnvSensor(seed=99).stream(50)]
        right = [r.temperature_c for r in SyntheticEnvSensor(seed=99).stream(50)]
        assert left == right

    def test_different_seeds_diverge(self):
        left = [r.temperature_c for r in SyntheticEnvSensor(seed=1).stream(50)]
        right = [r.temperature_c for r in SyntheticEnvSensor(seed=2).stream(50)]
        assert left != right

    def test_readings_are_complete_and_physically_plausible(self):
        for reading in SyntheticEnvSensor(seed=4).stream(400):
            assert reading.is_complete
            assert -40.0 <= reading.temperature_c <= 80.0
            assert 0.0 <= reading.humidity_pct <= 100.0
            assert reading.timestamp > 0

    def test_climate_profiles_actually_differ(self):
        def mean_temperature(profile: str) -> float:
            values = [r.temperature_c for r in SyntheticEnvSensor(profile=profile, seed=8,
                                                                  anomaly_probability=0.0).stream(300)]
            return sum(values) / len(values)

        assert mean_temperature("arid") - mean_temperature("alpine") > 15.0

    def test_unknown_profile_falls_back_to_temperate(self):
        assert get_profile("does-not-exist").name == "temperate"
        assert set(CLIMATE_PROFILES) >= {"temperate", "coastal", "arid", "alpine"}

    def test_no_anomalies_when_probability_is_zero(self):
        sensor = SyntheticEnvSensor(seed=6, anomaly_probability=0.0)
        labels = {r.metadata["truth_label"] for r in sensor.stream(600)}
        assert labels == {EventType.NONE.value}

    def test_forced_episode_moves_the_readings_and_labels_them(self):
        sensor = SyntheticEnvSensor(seed=12, anomaly_probability=0.0)
        calm = [r.temperature_c for r in sensor.stream(60)]
        calm_mean = sum(calm) / len(calm)

        sensor.force_episode(EventType.SPIKE, length=6)
        during = list(sensor.stream(6))

        assert all(r.metadata["truth_label"] == "spike" for r in during)
        # The episode reaches full magnitude on its last sample.
        assert during[-1].temperature_c != pytest.approx(calm_mean, abs=2.0)

    def test_episode_ends_and_the_sensor_settles(self):
        sensor = SyntheticEnvSensor(seed=13, anomaly_probability=0.0)
        list(sensor.stream(20))
        sensor.force_episode(EventType.DROP, length=5)
        list(sensor.stream(5))
        assert sensor.active_episode is None

        after = list(sensor.stream(5))
        assert all(r.metadata["truth_label"] == "none" for r in after)

    def test_anomalies_do_appear_when_probability_is_high(self):
        sensor = SyntheticEnvSensor(seed=21, anomaly_probability=0.3, quiet_samples=2)
        labels = {r.metadata["truth_label"] for r in sensor.stream(800)}
        assert labels - {EventType.NONE.value}, "expected at least one anomaly"

    def test_metadata_records_the_climate(self):
        reading = SyntheticEnvSensor(profile="arid", seed=1).read()
        assert reading.metadata["climate"] == "arid"
        assert reading.source == "synthetic:arid"


class TestAnomalyShapes:
    def test_offsets_start_at_zero_and_peak_at_the_end(self):
        import random

        episode = sample_episode(random.Random(0), EventType.SPIKE, length=10)
        first = episode_offsets(episode, 0)
        last = episode_offsets(episode, 9)
        assert first == (0.0, 0.0)
        assert abs(last[0]) + abs(last[1]) > 0

    def test_a_temperature_spike_dries_the_air(self):
        import random

        rng = random.Random(0)
        # Draw until we get a temperature-driven episode.
        episode = sample_episode(rng, EventType.SPIKE)
        while episode.channel != "temperature":
            episode = sample_episode(rng, EventType.SPIKE)

        d_temp, d_humidity = episode_offsets(episode, episode.length - 1)
        assert d_temp > 0 and d_humidity < 0

    def test_drift_is_linear_and_spike_is_not(self):
        import random

        rng = random.Random(5)
        drift = sample_episode(rng, EventType.DRIFT, length=11)
        midpoint = episode_offsets(drift, 5)[0]
        endpoint = episode_offsets(drift, 10)[0]
        assert midpoint == pytest.approx(endpoint * 0.5, rel=0.02)

        spike = sample_episode(rng, EventType.SPIKE, length=11)
        spike_mid = abs(episode_offsets(spike, 5)[0])
        spike_end = abs(episode_offsets(spike, 10)[0])
        assert spike_mid > spike_end * 0.55, "a spike front rises faster than linearly"


# ---------------------------------------------------------------------------
# DHT22 -- driver behaviour, faked
# ---------------------------------------------------------------------------


class FakeDHTDevice:
    """Stands in for `adafruit_dht.DHT22`.

    `failures` transient RuntimeErrors are raised before the first success,
    mirroring the real part's checksum/timing glitches.
    """

    def __init__(self, pin, use_pulseio=False, failures=0, temperature=21.5,
                 humidity=48.0, return_none=False):
        self.pin = pin
        self.use_pulseio = use_pulseio
        self.remaining_failures = failures
        self._temperature = temperature
        self._humidity = humidity
        self.return_none = return_none
        self.exited = False
        self.attempts = 0

    def _sample(self, value):
        self.attempts += 1
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise RuntimeError("Checksum did not validate. Try again.")
        return None if self.return_none else value

    @property
    def temperature(self):
        return self._sample(self._temperature)

    @property
    def humidity(self):
        # The real driver reads both from one captured pulse train, so a
        # successful temperature read implies a successful humidity read.
        return None if self.return_none else self._humidity

    def exit(self):
        self.exited = True


@pytest.fixture
def fake_gpio(monkeypatch):
    """Install fake `board` and `adafruit_dht` modules and hand back a factory."""
    board = types.ModuleType("board")
    board.D4 = "GPIO4"
    board.D17 = "GPIO17"

    created: list[FakeDHTDevice] = []
    settings: dict = {"failures": 0, "return_none": False}

    def factory(pin, use_pulseio=False):
        device = FakeDHTDevice(
            pin,
            use_pulseio=use_pulseio,
            failures=settings["failures"],
            return_none=settings["return_none"],
        )
        created.append(device)
        return device

    adafruit_dht = types.ModuleType("adafruit_dht")
    adafruit_dht.DHT22 = factory

    monkeypatch.setitem(sys.modules, "board", board)
    monkeypatch.setitem(sys.modules, "adafruit_dht", adafruit_dht)
    return {"devices": created, "settings": settings}


class TestDHT22:
    def test_reads_cleanly_when_the_hardware_behaves(self, fake_gpio):
        sensor = DHT22Sensor(retry_delay_s=0.0)
        reading = sensor.read()

        assert reading.temperature_c == pytest.approx(21.5)
        assert reading.humidity_pct == pytest.approx(48.0)
        assert reading.source == "dht22"
        assert reading.metadata["attempts"] == 1
        assert fake_gpio["devices"][0].pin == "GPIO4"

    def test_transient_runtime_errors_are_retried(self, fake_gpio):
        """The DHT22's signature failure mode: retry, do not propagate."""
        fake_gpio["settings"]["failures"] = 3
        sensor = DHT22Sensor(retries=5, retry_delay_s=0.0)

        reading = sensor.read()
        assert reading.temperature_c == pytest.approx(21.5)
        assert reading.metadata["attempts"] == 4

    def test_gives_up_after_the_retry_budget(self, fake_gpio):
        fake_gpio["settings"]["failures"] = 99
        sensor = DHT22Sensor(retries=3, retry_delay_s=0.0)

        with pytest.raises(SensorReadError, match="3 consecutive reads"):
            sensor.read()

    def test_none_values_count_as_a_failed_read(self, fake_gpio):
        """The driver sometimes returns None instead of raising."""
        fake_gpio["settings"]["return_none"] = True
        sensor = DHT22Sensor(retries=2, retry_delay_s=0.0)

        with pytest.raises(SensorReadError):
            sensor.read()

    def test_non_runtime_errors_are_not_retried(self, fake_gpio, monkeypatch):
        sensor = DHT22Sensor(retries=5, retry_delay_s=0.0)
        sensor.open()

        class Exploding:
            @property
            def temperature(self):
                raise OSError("GPIO busy")

            def exit(self):
                pass

        sensor._device = Exploding()
        with pytest.raises(SensorReadError, match="unrecoverably"):
            sensor.read()

    def test_datasheet_interval_is_enforced_against_config(self, fake_gpio):
        """A config asking for a faster poll than 2s must be clamped, not obeyed."""
        sensor = DHT22Sensor(min_interval_s=0.1)
        assert sensor.min_interval_s == DHT22_MIN_INTERVAL_S

    def test_a_custom_pin_is_honoured(self, fake_gpio):
        sensor = DHT22Sensor(pin="D17", retry_delay_s=0.0)
        sensor.read()
        assert fake_gpio["devices"][0].pin == "GPIO17"

    def test_an_unknown_pin_name_fails_clearly(self, fake_gpio):
        sensor = DHT22Sensor(pin="D999")
        with pytest.raises(SensorError, match="D999"):
            sensor.open()

    def test_close_releases_the_pin_and_is_idempotent(self, fake_gpio):
        sensor = DHT22Sensor(retry_delay_s=0.0)
        sensor.read()
        device = fake_gpio["devices"][0]

        sensor.close()
        sensor.close()
        assert device.exited is True

    def test_missing_drivers_produce_an_actionable_error(self, monkeypatch):
        """On a laptop with no Blinka, the message must say what to do."""
        monkeypatch.setitem(sys.modules, "board", None)
        monkeypatch.setitem(sys.modules, "adafruit_dht", None)

        sensor = DHT22Sensor()
        with pytest.raises(SensorError, match="synthetic"):
            sensor.open()
