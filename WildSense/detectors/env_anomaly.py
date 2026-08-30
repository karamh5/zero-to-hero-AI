"""EnvAnomalyDetector -- adaptive statistics gated with a learned classifier.

Two stages, with deliberately different jobs:

  Stage 1 (`baseline.py`)  Should we care at all?
      Rolling EWMA mean and variance per channel, at *two* timescales. A
      reading is interesting when its z-score against its own recent history
      crosses a threshold. There is no absolute temperature anywhere in this
      logic, which is the point: "hot" is defined relative to the last few
      minutes at this node.

      Two timescales, not one, because they detect different things:
        * the fast baseline (~39 samples) catches abrupt spikes and drops
        * the slow baseline (~500 samples) catches sustained drift, which a
          fast baseline is structurally incapable of seeing -- it is built to
          follow its input, so it absorbs a gradual ramp and every individual
          z-score stays near zero

  Stage 2 (`model.py`)     What kind of thing is it, and how sure are we?
      A small MLP over the last N readings names the event type and supplies
      a calibrated-ish confidence.

Stage 1 gates stage 2, never the other way round. If the model file is
missing, or torch cannot load it, or federation has not yet delivered
weights, the detector keeps working on statistics alone and says so in its
status. An edge node that goes silent because a model file is absent would be
a worse failure than a slightly coarser event label.
"""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path
from typing import Any

import torch

from core.config import PROJECT_ROOT
from core.contracts import Event, EventType, Reading
from core.registry import register_detector
from detectors.base import BaseDetector
from detectors.baseline import EwmaBaseline
from detectors.model import DEFAULT_WINDOW, EventClassifier, load_torchscript

log = logging.getLogger(__name__)


@register_detector("env_anomaly")
class EnvAnomalyDetector(BaseDetector):
    """Detects environmental anomalies relative to a rolling baseline.

    Args:
        alpha: EWMA forgetting factor. 0.05 ~= a 39-sample memory.
        z_threshold: how many standard deviations from baseline counts as an
            event. 3.5 is roughly one false positive per 2000 quiet samples
            for well-behaved noise.
        warmup_samples: readings to observe before any detection is allowed.
            Should comfortably exceed the window size.
        window_size: readings fed to the classifier. Must match the trained
            model's window.
        temp_min_std / humidity_min_std: variance floors, in sensor units.
            Defaults sit just above DHT22 quantisation noise (0.1 C, 0.1 %RH)
            so a very flat stretch cannot manufacture huge z-scores.
        sustained_samples: consecutive over-threshold readings after which the
            statistical fallback calls it a DRIFT rather than a SPIKE/DROP.
        clip_z: winsorising limit on how far one reading may move a baseline.
            See `EwmaBaseline.observe` -- without it, a single large spike
            inflates the variance for a hundred-plus samples and blinds the
            detector to everything that follows it.
        slow_alpha_ratio: the slow baselines use `alpha * slow_alpha_ratio`.
            0.08 gives roughly a 500-sample memory against a 39-sample one.
        drift_z_threshold: deviation from the *slow* baseline that counts as a
            sustained drift. Higher than `z_threshold` because the slow
            baseline naturally lags any real diurnal cycle.
        refractory_samples: after emitting, stay quiet for this many readings
            while the same condition persists. Without it a single drift
            episode emits one event -- and one S3 snapshot -- per reading for
            as long as the slow baseline stays displaced. Set to 0 to emit on
            every triggering reading.
        model_path: TorchScript (.ts.pt) or state_dict (.pt) artifact.
            Relative paths resolve against the project root.
        use_torchscript: load the TorchScript artifact instead of the eager
            model. Lighter at the edge, but weights cannot then be hot-swapped
            by federation.
        node_id: stamped onto every emitted Event.
    """

    name = "env_anomaly"

    def __init__(
        self,
        alpha: float = 0.05,
        z_threshold: float = 3.5,
        warmup_samples: int = 40,
        window_size: int = DEFAULT_WINDOW,
        temp_min_std: float = 0.20,
        humidity_min_std: float = 0.60,
        sustained_samples: int = 6,
        clip_z: float | None = 4.0,
        slow_alpha_ratio: float = 0.08,
        drift_z_threshold: float = 3.5,
        refractory_samples: int = 15,
        model_path: str | None = "artifacts/event_classifier.pt",
        use_torchscript: bool = False,
        hidden: int = 64,
        node_id: str = "wildsense-node",
    ) -> None:
        self.z_threshold = float(z_threshold)
        self.drift_z_threshold = float(drift_z_threshold)
        self.warmup_samples = int(warmup_samples)
        self.window_size = int(window_size)
        self.sustained_samples = int(sustained_samples)
        self.refractory_samples = max(0, int(refractory_samples))
        self.node_id = node_id

        # Fast baselines catch abrupt excursions.
        self._temp = EwmaBaseline(alpha=alpha, min_std=temp_min_std, clip_z=clip_z)
        self._humidity = EwmaBaseline(alpha=alpha, min_std=humidity_min_std, clip_z=clip_z)

        # Slow baselines catch sustained drift. A single fast EWMA cannot: it
        # is designed to follow its input, so a gradual ramp is absorbed into
        # the baseline and every individual z-score stays near zero. Measuring
        # the same signal against a much longer memory is what makes a slow
        # drift visible at all.
        slow_alpha = max(1e-4, float(alpha) * float(slow_alpha_ratio))
        self._temp_slow = EwmaBaseline(alpha=slow_alpha, min_std=temp_min_std, clip_z=clip_z)
        self._humidity_slow = EwmaBaseline(
            alpha=slow_alpha, min_std=humidity_min_std, clip_z=clip_z
        )

        self._window: deque[list[float]] = deque(maxlen=self.window_size)
        self._observed = 0
        self._consecutive = 0
        self._since_emit = 0

        # Model state. `_model_ready` is the flag that decides whether stage 2
        # runs at all -- an untrained network must never be trusted.
        self._model: Any = None
        self._model_ready = False
        self._is_torchscript = False
        self._hidden = int(hidden)
        self._load_model(model_path, use_torchscript)

    # -- model management --------------------------------------------------

    def _load_model(self, model_path: str | None, use_torchscript: bool) -> None:
        # Always hold an eager model so federation has something to update,
        # even when no artifact exists on disk yet.
        self._model = EventClassifier(window=self.window_size, hidden=self._hidden)

        if not model_path:
            log.info("No model path configured; running on statistics only.")
            return

        resolved = Path(model_path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / resolved

        if not resolved.exists():
            log.warning(
                "Event classifier not found at %s -- running on statistics only. "
                "Run `python -m detectors.train` to create it.",
                resolved,
            )
            return

        try:
            if use_torchscript:
                self._model = load_torchscript(resolved)
                self._is_torchscript = True
            else:
                state = torch.load(resolved, map_location="cpu", weights_only=True)
                self._model.load_state_dict(state)
                self._model.eval()
            self._model_ready = True
            log.info(
                "Loaded event classifier from %s (%s)",
                resolved,
                "TorchScript" if use_torchscript else "state_dict",
            )
        except Exception as exc:  # noqa: BLE001 - a bad artifact must not be fatal
            log.warning(
                "Could not load event classifier from %s (%s) -- running on "
                "statistics only.",
                resolved,
                exc,
            )
            self._model = EventClassifier(window=self.window_size, hidden=self._hidden)
            self._model_ready = False

    def get_weights(self) -> dict[str, torch.Tensor] | None:
        """The current model weights, or None if there is no trained model.

        Federation uses this to start from what this node already knows rather
        than from random initialisation.
        """
        if self._is_torchscript or not self._model_ready:
            return None
        return {key: value.detach().clone().cpu() for key, value in self._model.state_dict().items()}

    def set_weights(self, state_dict: dict[str, torch.Tensor]) -> bool:
        """Install new model weights, e.g. from a federated averaging round.

        Returns False (and changes nothing) when the detector is running a
        TorchScript artifact, whose weights are frozen at export time.
        """
        if self._is_torchscript:
            log.debug("Ignoring weight update: detector is running TorchScript.")
            return False
        try:
            self._model.load_state_dict(state_dict)
            self._model.eval()
            self._model_ready = True
            log.info("Detector model weights updated from federation.")
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("Rejected federated weights (%s)", exc)
            return False

    # -- BaseDetector ------------------------------------------------------

    @property
    def is_warm(self) -> bool:
        return self._observed >= self.warmup_samples

    def reset(self) -> None:
        for baseline in (self._temp, self._humidity, self._temp_slow, self._humidity_slow):
            baseline.reset()
        self._window.clear()
        self._observed = 0
        self._consecutive = 0
        self._since_emit = 0

    def update(self, reading: Reading) -> Event | None:
        """Fold one reading into the baselines and decide whether it is an event."""
        if not reading.is_complete:
            # A future sensor pack may supply only one channel; that is not an
            # error, this detector simply has nothing to say about it.
            log.debug("Skipping incomplete reading from %s", reading.source)
            return None

        temperature = float(reading.temperature_c)
        humidity = float(reading.humidity_pct)

        # Score against the pre-update baselines, then absorb into all four.
        z_temperature = self._temp.observe(temperature)
        z_humidity = self._humidity.observe(humidity)
        # Note: this scores the raw reading against the slow baseline. An
        # EWMA-crossover variant (fast mean vs slow mean) was measured and was
        # strictly worse -- at matched false-positive rates it gave 12-14%
        # drift recall against 18-25% for this formulation -- because
        # smoothing the fast side also delays it past the end of the ramp.
        z_temperature_slow = self._temp_slow.observe(temperature)
        z_humidity_slow = self._humidity_slow.observe(humidity)

        self._window.append([temperature, humidity])
        self._observed += 1

        if not self.is_warm:
            return None

        fast_severity = max(abs(z_temperature), abs(z_humidity))
        slow_severity = max(abs(z_temperature_slow), abs(z_humidity_slow))

        abrupt = fast_severity >= self.z_threshold
        sustained = slow_severity >= self.drift_z_threshold

        if not (abrupt or sustained):
            self._consecutive = 0
            self._since_emit = 0
            return None

        self._consecutive += 1
        self._since_emit += 1

        # Debounce. An ongoing condition is ONE event, not one per reading.
        # The slow baseline in particular stays displaced for hundreds of
        # samples after a real drift, so without this a single episode emits a
        # detection -- and an S3 snapshot -- on every single cycle. Measured on
        # a 230s demo run: 36 events for 4 actual episodes.
        #
        # Emit on the leading edge, then stay quiet until either the condition
        # clears or `refractory_samples` readings pass, so a genuinely
        # long-running event still re-reports periodically instead of going
        # silent forever.
        is_leading_edge = self._consecutive == 1
        if not is_leading_edge and self._since_emit <= self.refractory_samples:
            return None
        self._since_emit = 0

        event_type, confidence, source = self._classify(
            z_temperature, z_humidity, fast_severity, abrupt, sustained
        )

        # Report the excursion that actually triggered, so the numbers in the
        # event log explain why it fired.
        reported_temp_z = z_temperature if abrupt else z_temperature_slow
        reported_humidity_z = z_humidity if abrupt else z_humidity_slow
        timescale = "fast" if abrupt else "slow"
        baseline = self._temp if abrupt else self._temp_slow
        humidity_baseline = self._humidity if abrupt else self._humidity_slow

        return Event(
            timestamp=reading.timestamp,
            event_type=event_type,
            confidence=confidence,
            temperature_c=temperature,
            humidity_pct=humidity,
            z_temperature=reported_temp_z,
            z_humidity=reported_humidity_z,
            node_id=self.node_id,
            detector=self.name,
            detail=(
                f"{event_type.value} via {source} ({timescale} baseline): "
                f"z_temp={reported_temp_z:+.2f} (baseline {baseline.mean:.1f}C), "
                f"z_hum={reported_humidity_z:+.2f} "
                f"(baseline {humidity_baseline.mean:.1f}%), "
                f"{self._consecutive} consecutive"
            ),
        )

    # -- classification ----------------------------------------------------

    def _classify(
        self,
        z_temperature: float,
        z_humidity: float,
        severity: float,
        abrupt: bool,
        sustained: bool,
    ) -> tuple[EventType, float, str]:
        """Name the event type. Prefers the model, falls back to statistics."""
        if self._model_ready and len(self._window) == self.window_size:
            try:
                window = torch.tensor([list(self._window)], dtype=torch.float32)
                with torch.no_grad():
                    probabilities = torch.softmax(self._model(window), dim=1)[0]
                index = int(torch.argmax(probabilities).item())
                predicted = EventType.from_index(index)
                confidence = float(probabilities[index].item())

                # Stage 1 already decided something happened. If stage 2 says
                # "nothing", trust the statistics for the label but report the
                # disagreement through a reduced confidence.
                if predicted is EventType.NONE:
                    fallback, _, _ = self._statistical_class(
                        z_temperature, z_humidity, None, abrupt, sustained
                    )
                    return fallback, min(confidence, 0.5), "statistics (model unsure)"
                return predicted, confidence, "model"
            except Exception as exc:  # noqa: BLE001 - inference must never kill the loop
                log.warning("Classifier inference failed (%s); using statistics.", exc)

        return self._statistical_class(z_temperature, z_humidity, severity, abrupt, sustained)

    def _statistical_class(
        self,
        z_temperature: float,
        z_humidity: float,
        severity: float | None,
        abrupt: bool,
        sustained: bool,
    ) -> tuple[EventType, float, str]:
        """Label the event from z-scores alone.

        Drift is anything the slow baseline noticed but the fast one did not
        (a ramp gradual enough that no single reading looks wrong), or a long
        run of consecutive over-threshold readings -- both mean something
        persistent is dragging the baseline rather than a momentary excursion.
        """
        if severity is None:
            severity = max(abs(z_temperature), abs(z_humidity))

        if (sustained and not abrupt) or self._consecutive >= self.sustained_samples:
            event_type = EventType.DRIFT
        else:
            # Whichever channel is more extreme decides the direction. A
            # humidity surge is an upward excursion, hence SPIKE.
            dominant = z_temperature if abs(z_temperature) >= abs(z_humidity) else z_humidity
            event_type = EventType.SPIKE if dominant > 0 else EventType.DROP

        # Map severity onto 0.5-1.0: at the threshold we are barely convinced,
        # at three times the threshold we are certain.
        threshold = self.z_threshold if abrupt else self.drift_z_threshold
        confidence = 0.5 + 0.5 * min(1.0, (severity - threshold) / (2.0 * threshold))
        return event_type, round(max(0.5, confidence), 4), "statistics"

    # -- introspection -----------------------------------------------------

    def status(self) -> dict:
        return {
            "name": self.name,
            "warm": self.is_warm,
            "observed": self._observed,
            "warmup_samples": self.warmup_samples,
            "z_threshold": self.z_threshold,
            "drift_z_threshold": self.drift_z_threshold,
            "model_ready": self._model_ready,
            "model_kind": "torchscript" if self._is_torchscript else "eager",
            "temperature_baseline": self._temp.snapshot(),
            "humidity_baseline": self._humidity.snapshot(),
            "temperature_baseline_slow": self._temp_slow.snapshot(),
            "humidity_baseline_slow": self._humidity_slow.snapshot(),
        }
