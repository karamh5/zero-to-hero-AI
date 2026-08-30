"""FederationSimulation -- 3-5 simulated nodes doing real federated learning.

Only one physical WildSense node exists today, so the other nodes are
simulated. What is simulated is the *deployment*, not the learning: each node
has its own sensor, its own accumulated readings from its own climate, its own
private model copy, and trains concurrently in its own worker thread. The
weights that get averaged are real weights from real gradient descent.

Round structure (synchronous FedAvg):

    1. every node adopts the current global weights
    2. every node pulls fresh readings from its own sensor      [concurrent]
    3. every node runs a few local epochs on its own buffer     [concurrent]
    4. every node submits (weights, sample count) to the averager
    5. the coordinator merges them and evaluates the result

Step 5 scores the merged model on a held-out set spanning *all* climates. That
is the number worth watching: it shows the shared model getting better at
climates no single node ever saw, which is the only reason to federate at all.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

import torch
from torch import nn

from core.contracts import EventType
from detectors.model import DEFAULT_WINDOW, EventClassifier
from detectors.train import build_dataset
from federation.averager import FederatedAverager
from federation.local_trainer import LocalTrainer, TrainResult
from sensors.synthetic import SyntheticEnvSensor

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class NodeSpec:
    """Configuration for one simulated node."""

    node_id: str
    profile: str = "temperate"
    seed: int = 0
    #: Higher than the demo sensor's default so nodes accumulate enough
    #: non-`none` windows to learn from within a few rounds.
    anomaly_probability: float = 0.06


#: A believable small deployment: same species of node, very different weather.
DEFAULT_NODE_SPECS: list[NodeSpec] = [
    NodeSpec("node-coastal", profile="coastal", seed=11),
    NodeSpec("node-arid", profile="arid", seed=22),
    NodeSpec("node-alpine", profile="alpine", seed=33),
]


@dataclass
class RoundResult:
    """What happened during one federated round."""

    round_number: int
    node_results: list[TrainResult] = field(default_factory=list)
    total_samples: int = 0
    mean_local_loss: float = 0.0
    global_loss: float = 0.0
    global_accuracy: float = 0.0
    duration_s: float = 0.0
    aggregated: bool = False

    def to_dict(self) -> dict:
        return {
            "round": self.round_number,
            "aggregated": self.aggregated,
            "total_samples": self.total_samples,
            "mean_local_loss": round(self.mean_local_loss, 5),
            "global_loss": round(self.global_loss, 5),
            "global_accuracy": round(self.global_accuracy, 4),
            "duration_s": round(self.duration_s, 3),
            "nodes": [result.summary() for result in self.node_results],
        }


class FederatedNode:
    """One simulated node: its own sensor, its own buffer, its own model copy."""

    def __init__(
        self,
        spec: NodeSpec,
        window_size: int = DEFAULT_WINDOW,
        hidden: int = 64,
        learning_rate: float = 3e-3,
        local_epochs: int = 4,
        per_class_capacity: int = 300,
    ) -> None:
        self.spec = spec
        self.sensor = SyntheticEnvSensor(
            profile=spec.profile,
            seed=spec.seed,
            anomaly_probability=spec.anomaly_probability,
            quiet_samples=12,
            min_interval_s=0.0,  # simulated time; no wall-clock pacing
        )
        self.trainer = LocalTrainer(
            node_id=spec.node_id,
            window_size=window_size,
            hidden=hidden,
            learning_rate=learning_rate,
            epochs=local_epochs,
            per_class_capacity=per_class_capacity,
            seed=spec.seed,
        )

    def collect(self, count: int) -> int:
        """Pull `count` readings from this node's own sensor into its buffer."""
        return self.trainer.observe_stream(self.sensor.stream(count))

    def train(self, global_weights: dict[str, torch.Tensor] | None) -> TrainResult | None:
        """Adopt the global model, run local epochs, return the update."""
        if global_weights is not None:
            self.trainer.set_weights(global_weights)
        if not self.trainer.ready():
            log.debug(
                "%s not ready to train (%d windows: %s)",
                self.spec.node_id,
                self.trainer.buffered_samples,
                self.trainer.class_counts,
            )
            return None
        return self.trainer.fit()

    def status(self) -> dict:
        return {
            "node_id": self.spec.node_id,
            "climate": self.spec.profile,
            "buffered_windows": self.trainer.buffered_samples,
            "class_counts": self.trainer.class_counts,
        }


class FederationSimulation:
    """Coordinates rounds across simulated nodes.

    Two ways to drive it:
      * `run(rounds=N)` -- synchronous, deterministic; used by the tests.
      * `start()` / `stop()` -- background thread running a round every
        `round_interval_s`; used by the live pipeline.

    Args:
        specs: node definitions. 3-5 is the sensible range.
        samples_per_round: readings each node collects before training.
        warmup_readings: readings collected per node before round 1, so the
            first round already has a balanced buffer to learn from.
        round_interval_s: seconds between rounds in background mode.
        on_round: callback invoked after each successful aggregation with
            (RoundResult, global weights). The pipeline uses this to hot-swap
            the live detector's model.
    """

    def __init__(
        self,
        specs: list[NodeSpec] | None = None,
        window_size: int = DEFAULT_WINDOW,
        hidden: int = 64,
        learning_rate: float = 3e-3,
        local_epochs: int = 4,
        samples_per_round: int = 150,
        warmup_readings: int = 600,
        round_interval_s: float = 20.0,
        min_updates: int | None = None,
        validation_samples_per_class: int = 60,
        seed: int = 0,
        initial_weights: dict[str, torch.Tensor] | None = None,
        on_round: Callable[[RoundResult, dict[str, torch.Tensor]], None] | None = None,
    ) -> None:
        # `None` means "use the defaults"; an explicitly empty list is an error,
        # not a silent fallback.
        self.specs = list(DEFAULT_NODE_SPECS if specs is None else specs)
        if not self.specs:
            raise ValueError("federation needs at least one node spec")

        self.window_size = int(window_size)
        self.samples_per_round = int(samples_per_round)
        self.warmup_readings = int(warmup_readings)
        self.round_interval_s = float(round_interval_s)
        self.on_round = on_round
        self.seed = int(seed)

        self.nodes = [
            FederatedNode(
                spec,
                window_size=window_size,
                hidden=hidden,
                learning_rate=learning_rate,
                local_epochs=local_epochs,
            )
            for spec in self.specs
        ]
        self.averager = FederatedAverager(
            min_updates=min_updates if min_updates is not None else len(self.nodes)
        )
        if initial_weights is not None:
            # Start the fleet from an already-trained model instead of random
            # noise, so round 1 improves the live detector rather than
            # temporarily replacing it with a chance-level one.
            self.averager.seed(initial_weights)
            log.info("Federation seeded from the node's existing model weights.")

        # Held-out data spanning every node's climate, used to score the
        # merged model. Built once; seeds are offset from the nodes' own so
        # nodes cannot have trained on these exact windows.
        self._val_x, self._val_y = self._build_validation(validation_samples_per_class)
        self._eval_model = EventClassifier(window=self.window_size, hidden=hidden)
        self._criterion = nn.CrossEntropyLoss()

        self._primed = False
        self._results: list[RoundResult] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- setup -------------------------------------------------------------

    def _build_validation(self, samples_per_class: int) -> tuple[torch.Tensor, torch.Tensor]:
        windows: list[torch.Tensor] = []
        labels: list[torch.Tensor] = []
        for offset, spec in enumerate(self.specs):
            chunk_x, chunk_y = build_dataset(
                spec.profile,
                samples_per_class=samples_per_class,
                window=self.window_size,
                seed=90_000 + spec.seed + offset,
            )
            windows.append(chunk_x)
            labels.append(chunk_y)
        return torch.cat(windows), torch.cat(labels)

    def prime(self) -> None:
        """Fill every node's buffer before the first round. Idempotent."""
        if self._primed:
            return
        log.info(
            "Priming %d federated nodes with %d readings each...",
            len(self.nodes),
            self.warmup_readings,
        )
        with ThreadPoolExecutor(max_workers=len(self.nodes)) as pool:
            list(pool.map(lambda node: node.collect(self.warmup_readings), self.nodes))
        for node in self.nodes:
            log.info(
                "  %-14s climate=%-9s windows=%s",
                node.spec.node_id,
                node.spec.profile,
                node.trainer.class_counts,
            )
        self._primed = True

    # -- rounds ------------------------------------------------------------

    def run_round(self) -> RoundResult:
        """Execute one full federated round. Nodes train concurrently."""
        self.prime()
        started = time.perf_counter()
        global_weights = self.averager.global_weights()

        def work(node: FederatedNode) -> TrainResult | None:
            # Each node runs this in its own worker thread: collect from its
            # own sensor, then fit its own copy of the model.
            node.collect(self.samples_per_round)
            return node.train(global_weights)

        with ThreadPoolExecutor(max_workers=len(self.nodes)) as pool:
            outcomes = list(pool.map(work, self.nodes))

        node_results = [result for result in outcomes if result is not None]
        for result in node_results:
            self.averager.submit(
                result.node_id, result.state_dict, result.num_samples, result.loss
            )

        merged = self.averager.aggregate()
        result = RoundResult(
            round_number=self.averager.round_number,
            node_results=node_results,
            total_samples=sum(item.num_samples for item in node_results),
            mean_local_loss=(
                sum(item.loss for item in node_results) / len(node_results)
                if node_results
                else 0.0
            ),
            duration_s=time.perf_counter() - started,
            aggregated=merged is not None,
        )

        if merged is not None:
            result.global_loss, result.global_accuracy = self.evaluate(merged)
            log.info(
                "Round %d: global loss %.4f, global accuracy %.3f across %d climates",
                result.round_number,
                result.global_loss,
                result.global_accuracy,
                len(self.specs),
            )
            if self.on_round is not None:
                try:
                    self.on_round(result, merged)
                except Exception as exc:  # noqa: BLE001 - a bad callback must not stop training
                    log.warning("on_round callback raised (%s)", exc)

        with self._lock:
            self._results.append(result)
        return result

    def run(self, rounds: int = 3) -> list[RoundResult]:
        """Run `rounds` rounds synchronously and return their results."""
        return [self.run_round() for _ in range(max(1, int(rounds)))]

    @torch.no_grad()
    def evaluate(self, weights: dict[str, torch.Tensor]) -> tuple[float, float]:
        """Score a set of weights on the held-out multi-climate validation set."""
        self._eval_model.load_state_dict(weights)
        self._eval_model.eval()
        logits = self._eval_model(self._val_x)
        loss = float(self._criterion(logits, self._val_y).item())
        accuracy = float((logits.argmax(dim=1) == self._val_y).float().mean().item())
        return loss, accuracy

    @torch.no_grad()
    def per_class_accuracy(self, weights: dict[str, torch.Tensor]) -> dict[str, float]:
        """Validation accuracy per event type for a set of weights."""
        self._eval_model.load_state_dict(weights)
        self._eval_model.eval()
        predictions = self._eval_model(self._val_x).argmax(dim=1)
        out: dict[str, float] = {}
        for event in EventType.ordered():
            mask = self._val_y == event.index
            total = int(mask.sum().item())
            out[event.value] = (
                round(float((predictions[mask] == event.index).float().mean().item()), 4)
                if total
                else 0.0
            )
        return out

    # -- background mode ---------------------------------------------------

    def start(self) -> None:
        """Run rounds forever on a daemon thread, every `round_interval_s`."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="wildsense-federation", daemon=True
        )
        self._thread.start()
        log.info(
            "Federation started: %d nodes, a round every %.0fs",
            len(self.nodes),
            self.round_interval_s,
        )

    def _loop(self) -> None:
        # Prime once up front so the first round is not delayed by warmup.
        try:
            self.prime()
        except Exception as exc:  # noqa: BLE001
            log.error("Federation priming failed: %s", exc)
            return

        while not self._stop.is_set():
            try:
                self.run_round()
            except Exception as exc:  # noqa: BLE001 - never kill the thread
                log.exception("Federated round failed: %s", exc)
            # Interruptible sleep, so stop() returns promptly.
            self._stop.wait(self.round_interval_s)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the background thread to finish the current round and exit."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    # -- introspection -----------------------------------------------------

    @property
    def results(self) -> list[RoundResult]:
        with self._lock:
            return list(self._results)

    def status(self) -> dict:
        """Snapshot for the dashboard."""
        with self._lock:
            recent = self._results[-1] if self._results else None
        return {
            "enabled": True,
            "rounds_completed": self.averager.round_number,
            "round_interval_s": self.round_interval_s,
            "nodes": [node.status() for node in self.nodes],
            "latest_round": recent.to_dict() if recent else None,
            "history": [
                {
                    "round": item.round_number,
                    "global_loss": round(item.global_loss, 5),
                    "global_accuracy": round(item.global_accuracy, 4),
                }
                for item in (self._results[-20:] if self._results else [])
            ],
        }
