"""Config, registry, model export, and the end-to-end synthetic pipeline.

The final class is the one that answers "does synthetic mode actually work":
it builds a real pipeline from a real config and runs real cycles.
"""

from __future__ import annotations

import json

import pytest
import torch

from core.config import DEFAULT_CONFIG_PATH, Config, load_config
from core.contracts import Event, EventType, Reading, utc_iso
from core.registry import (
    RegistryError,
    available_detectors,
    available_sensors,
    create_detector,
    create_sensor,
    discover,
)
from detectors.model import EventClassifier, export_torchscript, load_torchscript
from pipeline import WildSensePipeline


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


class TestContracts:
    def test_event_types_have_a_stable_index_order(self):
        """Reordering these silently invalidates every trained model."""
        assert [event.value for event in EventType.ordered()] == [
            "none", "spike", "drop", "drift"
        ]
        assert EventType.NONE.index == 0
        assert EventType.from_index(2) is EventType.DROP

    def test_reading_completeness(self):
        assert Reading(0.0, 20.0, 50.0).is_complete is True
        assert Reading(0.0, 20.0, None).is_complete is False
        assert Reading(0.0, None, None).is_complete is False

    def test_event_serialises_to_json(self):
        event = Event(
            timestamp=1_767_225_600.0,
            event_type=EventType.DRIFT,
            confidence=0.8123456,
            temperature_c=25.0,
            humidity_pct=40.0,
            z_temperature=4.123456,
            z_humidity=None,
        )
        payload = event.to_dict()
        json.dumps(payload)  # must not raise

        assert payload["event_type"] == "drift"
        assert payload["confidence"] == 0.8123
        assert payload["z_temperature"] == 4.123
        assert payload["z_humidity"] is None
        assert payload["iso_time"] == utc_iso(1_767_225_600.0)


# ---------------------------------------------------------------------------
# Config + registry -- the modularity claim
# ---------------------------------------------------------------------------


class TestConfig:
    def test_the_shipped_config_loads(self):
        config = load_config()
        assert config.path == DEFAULT_CONFIG_PATH
        assert config.get("sensor.active") == "synthetic"
        assert config.get("detector.active") == "env_anomaly"

    def test_dotted_lookup_with_defaults(self):
        config = Config({"a": {"b": {"c": 1}}})
        assert config.get("a.b.c") == 1
        assert config.get("a.b.missing", "fallback") == "fallback"
        assert config.get("nothing.at.all") is None

    def test_sections_are_copies_so_packs_cannot_mutate_shared_config(self):
        config = Config({"sensor": {"packs": {"synthetic": {"seed": 1}}}})
        section = config.section("sensor.packs.synthetic")
        section["seed"] = 999
        assert config.get("sensor.packs.synthetic.seed") == 1

    def test_pack_options_resolves_the_active_pack(self):
        config = Config({"sensor": {"active": "synthetic", "packs": {"synthetic": {"seed": 7}}}})
        name, options = config.pack_options("sensor")
        assert name == "synthetic"
        assert options == {"seed": 7}

    def test_missing_active_key_is_a_clear_error(self):
        with pytest.raises(ValueError, match="sensor.active"):
            Config({"sensor": {}}).pack_options("sensor")

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("no-such-config.yaml")


class TestRegistry:
    def test_shipped_packs_register_themselves(self):
        discover(["sensors.synthetic", "sensors.dht22", "detectors.env_anomaly"])
        assert "synthetic" in available_sensors()
        assert "dht22" in available_sensors()
        assert "env_anomaly" in available_detectors()

    def test_packs_are_built_by_config_name(self):
        discover(["sensors.synthetic"])
        sensor = create_sensor("synthetic", {"seed": 5, "profile": "arid"})
        assert sensor.name == "synthetic"
        assert sensor.profile.name == "arid"

    def test_an_unknown_pack_name_explains_itself(self):
        with pytest.raises(RegistryError, match="thermal"):
            create_sensor("thermal", {})

    def test_discover_survives_a_broken_module(self):
        """A hardware pack that cannot import on a laptop must not be fatal."""
        discover(["sensors.does_not_exist", "sensors.synthetic"])
        assert "synthetic" in available_sensors()

    def test_detectors_are_built_by_name(self):
        discover(["detectors.env_anomaly"])
        detector = create_detector("env_anomaly", {"model_path": None, "z_threshold": 2.0})
        assert detector.name == "env_anomaly"
        assert detector.z_threshold == 2.0


# ---------------------------------------------------------------------------
# Model + TorchScript export
# ---------------------------------------------------------------------------


class TestModel:
    def test_the_model_is_small_enough_for_a_pi(self):
        model = EventClassifier(window=32, hidden=64)
        assert model.parameter_count() < 20_000

    def test_shapes_are_as_documented(self):
        model = EventClassifier(window=16, hidden=16)
        logits = model(torch.randn(5, 16, 2))
        assert logits.shape == (5, 4)

    def test_predict_returns_a_type_and_a_confidence(self):
        model = EventClassifier(window=16, hidden=16)
        event_type, confidence = model.predict(torch.randn(16, 2))
        assert event_type in EventType.ordered()
        assert 0.0 <= confidence <= 1.0

    def test_normalisation_makes_the_model_climate_invariant(self):
        """Shifting a window by a constant must not change what it looks like.

        This is the property that lets a model trained on desert nodes work on
        alpine ones -- and the reason federated averaging across dissimilar
        climates is coherent at all.
        """
        model = EventClassifier(window=16, hidden=16).eval()
        window = torch.randn(1, 16, 2) * 2.0 + 20.0
        shifted = window + 15.0  # same shape, 15 C hotter

        with torch.no_grad():
            assert torch.allclose(model(window), model(shifted), atol=1e-3)

    def test_magnitude_features_still_distinguish_calm_from_violent(self):
        """Shape-invariance must not make the model blind to amplitude."""
        model = EventClassifier(window=16, hidden=16).eval()
        shape = torch.randn(1, 16, 2)
        with torch.no_grad():
            calm = model(shape * 0.05 + 20.0)
            violent = model(shape * 8.0 + 20.0)
        assert not torch.allclose(calm, violent, atol=1e-3)

    def test_torchscript_export_round_trips(self, tmp_path):
        model = EventClassifier(window=16, hidden=16).eval()
        destination = export_torchscript(model, tmp_path / "model.ts.pt")
        assert destination.exists()

        loaded = load_torchscript(destination)
        window = torch.randn(3, 16, 2)
        with torch.no_grad():
            assert torch.allclose(model(window), loaded(window), atol=1e-5)

    def test_a_torchscript_detector_refuses_weight_hot_swaps(self, tmp_path):
        """Exported weights are frozen; the detector must say so, not pretend."""
        from detectors.env_anomaly import EnvAnomalyDetector

        model = EventClassifier(window=16, hidden=16).eval()
        path = export_torchscript(model, tmp_path / "model.ts.pt")

        detector = EnvAnomalyDetector(
            window_size=16, hidden=16, model_path=str(path), use_torchscript=True
        )
        assert detector.status()["model_kind"] == "torchscript"
        assert detector.set_weights(EventClassifier(window=16, hidden=16).state_dict()) is False


class TestTrainingData:
    def test_generated_windows_have_the_right_shape_and_balance(self):
        from detectors.train import build_dataset

        windows, labels = build_dataset("temperate", samples_per_class=20, window=16, seed=1)
        assert windows.shape == (80, 16, 2)
        assert labels.shape == (80,)
        assert sorted(labels.bincount().tolist()) == [20, 20, 20, 20]

    def test_anomalous_windows_move_more_than_calm_ones(self):
        from detectors.train import build_dataset

        windows, labels = build_dataset("temperate", samples_per_class=60, window=16, seed=2)
        spread = windows.std(dim=1)[:, 0]  # temperature spread within each window

        calm = spread[labels == EventType.NONE.index].mean()
        spikes = spread[labels == EventType.SPIKE.index].mean()
        assert spikes > calm * 2.0

    def test_a_short_training_run_beats_chance(self):
        from detectors.train import train_model

        model, metrics = train_model(
            profiles=["temperate", "arid"],
            samples_per_class=120,
            window=16,
            hidden=32,
            epochs=25,
            seed=0,
        )
        assert metrics["val_accuracy"] > 0.6, metrics
        assert model.parameter_count() < 20_000


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


class TestDashboardServer:
    def test_it_serves_and_reports_success(self):
        from dashboard.app import DashboardServer
        from urllib.request import urlopen

        server = DashboardServer(host="127.0.0.1", port=0)
        # Port 0 would let the OS choose, but then we would not know it; pick a
        # free one explicitly instead.
        import socket

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            server.port = probe.getsockname()[1]

        assert server.start(wait_timeout=15.0) is True
        try:
            with urlopen(f"http://127.0.0.1:{server.port}/api/health", timeout=5) as response:
                payload = json.loads(response.read())
            assert payload["status"] == "ok"
        finally:
            server.stop()

    # uvicorn calls sys.exit() on its own thread when the bind fails, which
    # pytest surfaces as an unhandled thread exception. That IS the behaviour
    # under test, so the warning is expected noise.
    @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
    def test_a_taken_port_reports_failure_instead_of_pretending(self):
        """Regression test: it used to print a URL that answered nothing."""
        import socket

        from dashboard.app import DashboardServer

        blocker = socket.socket()
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        taken_port = blocker.getsockname()[1]

        try:
            server = DashboardServer(host="127.0.0.1", port=taken_port)
            assert server.start(wait_timeout=8.0) is False
        finally:
            blocker.close()


@pytest.fixture
def fast_config(tmp_path) -> Config:
    """The shipped config, retuned for a fast hardware-free test run."""
    data = load_config().as_dict()
    data["sensor"]["active"] = "synthetic"
    data["sensor"]["packs"]["synthetic"].update(
        {"anomaly_probability": 0.08, "quiet_samples": 6, "seed": 4242}
    )
    data["detector"]["packs"]["env_anomaly"].update({"warmup_samples": 30, "model_path": None})
    data["context"]["intervals"] = {k: 0.0 for k in ("low", "moderate", "high", "extreme")}
    data["federation"]["enabled"] = False
    data["dashboard"]["enabled"] = False
    data["cloud"]["local_fallback_dir"] = str(tmp_path / "events")
    return Config(data, DEFAULT_CONFIG_PATH)


class TestPipelineEndToEnd:
    def test_sensor_to_detector_to_state(self, fast_config):
        from dashboard.state import DashboardState

        state = DashboardState()
        pipeline = WildSensePipeline(fast_config, state=state)
        try:
            pipeline.start()
            pipeline.run(max_cycles=400)
        finally:
            pipeline.stop()

        snapshot = state.snapshot()
        assert snapshot["counters"]["readings"] == 400
        assert snapshot["counters"]["events"] > 0, "400 cycles should surface anomalies"
        assert snapshot["runtime"]["mode"] == "synthetic"
        assert snapshot["detector"]["warm"] is True
        assert snapshot["risk"]["level"] in {"low", "moderate", "high", "extreme"}
        assert snapshot["poll_interval_s"] >= 0.0
        json.dumps(snapshot)  # the dashboard must be able to serve this

    def test_event_snapshots_reach_the_cloud_fallback(self, fast_config, tmp_path):
        pipeline = WildSensePipeline(fast_config)
        try:
            pipeline.start()
            pipeline.run(max_cycles=400)
        finally:
            pipeline.stop()

        written = list((tmp_path / "events").rglob("*.json"))
        assert written, "detected events should be snapshotted somewhere"
        payload = json.loads(written[0].read_text(encoding="utf-8"))
        assert payload["event_type"] in {"spike", "drop", "drift"}

    def test_the_polling_interval_tracks_the_risk_level(self, fast_config):
        data = fast_config.as_dict()
        data["context"]["intervals"] = {
            "low": 60.0, "moderate": 30.0, "high": 5.0, "extreme": 2.0
        }
        pipeline = WildSensePipeline(Config(data, DEFAULT_CONFIG_PATH))
        try:
            pipeline.start()
            for _ in range(50):
                pipeline.run_cycle()
                assessment = pipeline._reassess_risk()
                expected = pipeline.polling.interval_for(assessment.level)
                assert pipeline._current_interval == expected
        finally:
            pipeline.stop()

    def test_a_sensor_read_failure_costs_one_cycle_not_the_run(self, fast_config):
        from sensors.base import SensorReadError

        pipeline = WildSensePipeline(fast_config)
        pipeline.start()
        try:
            real_read = pipeline.sensor.read
            calls = {"n": 0}

            def flaky_read():
                calls["n"] += 1
                if calls["n"] % 3 == 0:
                    raise SensorReadError("simulated DHT22 checksum failure")
                return real_read()

            pipeline.sensor.read = flaky_read  # type: ignore[method-assign]
            for _ in range(60):
                pipeline.run_cycle()  # must not raise
        finally:
            pipeline.stop()

        assert calls["n"] == 60

    def test_a_future_sensor_pack_is_a_config_change_only(self, fast_config):
        """The modularity claim, exercised rather than asserted in prose."""
        from core.registry import register_sensor
        from sensors.base import BaseSensor

        @register_sensor("test_thermal_pack")
        class ThermalPack(BaseSensor):
            name = "test_thermal_pack"

            def __init__(self, hotspot_c: float = 60.0) -> None:
                super().__init__(min_interval_s=0.0)
                self.hotspot_c = hotspot_c

            def _read_once(self) -> Reading:
                return Reading.now(
                    temperature_c=self.hotspot_c, humidity_pct=30.0, source=self.name
                )

        data = fast_config.as_dict()
        data["sensor"]["active"] = "test_thermal_pack"
        data["sensor"]["packs"]["test_thermal_pack"] = {"hotspot_c": 55.0}

        pipeline = WildSensePipeline(Config(data, DEFAULT_CONFIG_PATH))
        try:
            pipeline.start()
            pipeline.run(max_cycles=5)
        finally:
            pipeline.stop()

        assert isinstance(pipeline.sensor, ThermalPack)
        assert pipeline.sensor.hotspot_c == 55.0
