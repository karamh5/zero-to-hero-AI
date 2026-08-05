"""WildSensePipeline -- the loop that wires every module together.

    sensor.read()  ->  detector.update()  ->  event?
                                               |-> dashboard state
                                               |-> cloud snapshot
                                               `-> risk escalation
    risk provider  ->  polling policy    ->  how long to sleep

Everything this file touches is behind an interface. It never imports a
concrete sensor or detector -- both come out of the registry by name from
`config.yaml`. Adding a sensor pack does not change a line of this file.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque

import torch

from context.risk import PollingPolicy, RiskAssessment, build_risk_provider
from core.config import Config
from core.contracts import Event
from core.registry import create_detector, create_sensor, discover
from cloud.s3_sync import S3EventSync
from dashboard.state import STATE, DashboardState
from federation.simulation import FederationSimulation, NodeSpec, RoundResult
from sensors.base import SensorError, SensorReadError

log = logging.getLogger(__name__)


class WildSensePipeline:
    """Builds and runs one WildSense node from config."""

    def __init__(self, config: Config, state: DashboardState | None = None) -> None:
        self.config = config
        self.state = state or STATE
        self._stop = threading.Event()

        # 1. Load pack modules named in config so their decorators register them.
        discover(config.get("packs.discover", []))

        # 2. Build the active sensor and detector by name.
        sensor_name, sensor_options = config.pack_options("sensor")
        detector_name, detector_options = config.pack_options("detector")

        self.node_id = config.get("node.id", "wildsense-node")
        detector_options.setdefault("node_id", self.node_id)

        self.sensor = create_sensor(sensor_name, sensor_options)
        self.detector = create_detector(detector_name, detector_options)
        log.info(
            "Node '%s': sensor=%s detector=%s", self.node_id, sensor_name, detector_name
        )

        # 3. Contextual adaptation. The polling policy is clamped by the
        #    sensor's own hardware floor, not by whatever config asked for.
        self.risk_provider = build_risk_provider(
            config.get("context.provider", "mock_external"),
            config.section(f"context.providers.{config.get('context.provider', 'mock_external')}"),
        )
        self.polling = PollingPolicy(
            intervals=config.section("context.intervals"),
            sensor_min_interval_s=self.sensor.min_interval_s,
            max_interval_s=float(config.get("context.max_interval_s", 300.0)),
        )

        # 4. Cloud sync. Optional, non-fatal, never blocking.
        self.cloud = S3EventSync(**config.section("cloud"))

        # 5. Federation. Optional; runs simulated peer nodes in the background.
        self.federation: FederationSimulation | None = None
        if config.get("federation.enabled", False):
            self.federation = self._build_federation(config)

        # Recent detections feed the risk provider's escalation term.
        self._recent_events: deque[Event] = deque(maxlen=64)
        self._current_interval = self.polling.interval_for(
            self.risk_provider.assess([]).level
        )

    # -- construction helpers ---------------------------------------------

    def _build_federation(self, config: Config) -> FederationSimulation:
        specs = [
            NodeSpec(
                node_id=entry.get("node_id", f"node-{index}"),
                profile=entry.get("profile", "temperate"),
                seed=int(entry.get("seed", index)),
                anomaly_probability=float(entry.get("anomaly_probability", 0.06)),
            )
            for index, entry in enumerate(config.get("federation.nodes", []) or [])
        ]
        # Hand the fleet whatever this node already knows. Without this, round 1
        # averages three randomly-initialised models and hot-swaps a
        # chance-level result over a perfectly good trained detector.
        initial_weights = (
            self.detector.get_weights() if hasattr(self.detector, "get_weights") else None
        )

        return FederationSimulation(
            specs=specs or None,
            initial_weights=initial_weights,
            window_size=int(config.get("detector.packs.env_anomaly.window_size", 32)),
            hidden=int(config.get("detector.packs.env_anomaly.hidden", 64)),
            learning_rate=float(config.get("federation.learning_rate", 3e-3)),
            local_epochs=int(config.get("federation.local_epochs", 4)),
            samples_per_round=int(config.get("federation.samples_per_round", 150)),
            warmup_readings=int(config.get("federation.warmup_readings", 600)),
            round_interval_s=float(config.get("federation.round_interval_s", 20.0)),
            on_round=self._on_federated_round,
        )

    def _on_federated_round(
        self, result: RoundResult, weights: dict[str, torch.Tensor]
    ) -> None:
        """Push freshly averaged weights into the live detector.

        This closes the loop: the simulated fleet's learning actually improves
        the model this node is detecting with, rather than training in a
        vacuum next to it.

        The accuracy gate is the safety catch. With no pre-trained artifact to
        seed from, the first federated rounds are genuinely worse than chance
        is generous, and adopting them would degrade a working detector. A
        round has to clear the bar before the live node will listen to it.
        """
        if not bool(self.config.get("federation.update_detector", True)):
            return
        if not hasattr(self.detector, "set_weights"):
            return

        floor = float(self.config.get("federation.min_accuracy_to_adopt", 0.5))
        if result.global_accuracy < floor:
            log.info(
                "Round %d not adopted: global accuracy %.3f is below the %.2f floor.",
                result.round_number,
                result.global_accuracy,
                floor,
            )
        elif self.detector.set_weights(weights):
            log.info(
                "Detector adopted global model from round %d (accuracy %.3f)",
                result.round_number,
                result.global_accuracy,
            )

        self.state.set_federation(self.federation.status())

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Open the sensor and start the optional background services."""
        self.sensor.open()
        self.cloud.start()
        self.state.set_runtime(
            {
                "node_id": self.node_id,
                "sensor": self.sensor.name,
                "detector": self.detector.name,
                "mode": "synthetic" if self.sensor.name == "synthetic" else "hardware",
                "sensor_min_interval_s": self.sensor.min_interval_s,
            }
        )
        self.state.set_cloud(self.cloud.status())
        if self.federation is not None:
            self.state.set_federation({"enabled": True, "rounds_completed": 0, "nodes": []})
            self.federation.start()

    def stop(self) -> None:
        """Shut everything down. Safe to call more than once."""
        self._stop.set()
        if self.federation is not None:
            self.federation.stop()
        self.cloud.stop()
        try:
            self.sensor.close()
        except Exception as exc:  # noqa: BLE001 - teardown must not raise
            log.debug("Ignoring sensor close error: %s", exc)

    # -- the loop ----------------------------------------------------------

    def run_cycle(self) -> Event | None:
        """One read -> detect -> publish -> re-assess-risk cycle.

        Returns the event detected this cycle, if any. Never raises for an
        expected sensor failure -- a bad read costs one cycle, nothing more.
        """
        try:
            reading = self.sensor.read()
        except SensorReadError as exc:
            # Routine on a DHT22. Skip the cycle and try again next time.
            log.warning("Sensor read failed, skipping cycle: %s", exc)
            self._reassess_risk()
            return None
        except SensorError as exc:
            # Structural problem (bad wiring, missing driver): fatal.
            log.error("Sensor is unusable: %s", exc)
            raise

        self.state.add_reading(reading)
        event = self.detector.update(reading)

        if event is not None:
            log.info(
                "EVENT %-6s conf=%.2f  %.1fC / %.1f%%RH  (%s)",
                event.event_type.value,
                event.confidence,
                event.temperature_c if event.temperature_c is not None else float("nan"),
                event.humidity_pct if event.humidity_pct is not None else float("nan"),
                event.detail,
            )
            self._recent_events.append(event)
            self.state.add_event(event)
            self.cloud.publish(event)

        self.state.set_detector(self.detector.status())
        self.state.set_cloud(self.cloud.status())
        self._reassess_risk()
        return event

    def _reassess_risk(self) -> RiskAssessment:
        """Ask the context module for the risk, and set the next interval."""
        assessment = self.risk_provider.assess(list(self._recent_events))
        interval = self.polling.interval_for_assessment(assessment)

        if abs(interval - self._current_interval) > 1e-9:
            log.info(
                "Risk %s -> polling every %.1fs (was %.1fs)",
                assessment.level.value,
                interval,
                self._current_interval,
            )
        self._current_interval = interval
        self.state.set_risk(assessment.to_dict(), interval)
        return assessment

    def run(self, duration_s: float | None = None, max_cycles: int | None = None) -> int:
        """Run until stopped, or until a duration / cycle budget is reached.

        Returns the number of cycles completed.
        """
        self._stop.clear()
        started = time.monotonic()
        cycles = 0

        log.info(
            "WildSense running. Polling starts at %.1fs (sensor floor %.1fs).",
            self._current_interval,
            self.sensor.min_interval_s,
        )

        while not self._stop.is_set():
            self.run_cycle()
            cycles += 1

            if max_cycles is not None and cycles >= max_cycles:
                break
            if duration_s is not None and (time.monotonic() - started) >= duration_s:
                break

            if self.federation is not None:
                self.state.set_federation(self.federation.status())

            # Interruptible sleep: Ctrl-C and stop() take effect immediately
            # even on a 60-second low-risk interval.
            self._stop.wait(self._current_interval)

        return cycles
