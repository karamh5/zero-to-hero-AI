"""LocalTrainer -- fits the event classifier on one node's own readings.

This is the "local" half of federated learning. A node never ships readings
anywhere; it accumulates them, trains on them, and ships only weights. That is
the entire privacy and bandwidth argument for federation, and it is also just
practical for a solar-powered box on a bad LTE link.

Class balance is handled by keeping a separate bounded buffer per event type.
Left alone, a live stream is >95% `none`, and a model trained on that learns
to answer "none" to everything. Bounded per-class buffers give the trainer an
even diet without needing to store the whole history.
"""

from __future__ import annotations

import logging
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

import torch
from torch import nn

from core.contracts import EventType, Reading
from detectors.model import DEFAULT_WINDOW, EventClassifier

log = logging.getLogger(__name__)


@dataclass
class TrainResult:
    """Outcome of one local training run, plus the weights to be averaged."""

    node_id: str
    num_samples: int
    loss: float
    accuracy: float
    epochs: int
    state_dict: dict[str, torch.Tensor] = field(repr=False, default_factory=dict)

    def summary(self) -> dict:
        return {
            "node_id": self.node_id,
            "num_samples": self.num_samples,
            "loss": round(self.loss, 5),
            "accuracy": round(self.accuracy, 4),
            "epochs": self.epochs,
        }


def clone_state_dict(state: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Detached CPU copy, so weights crossing thread boundaries never alias."""
    return {key: value.detach().clone().cpu() for key, value in state.items()}


class LocalTrainer:
    """Accumulates readings for one node and trains a private copy of the model.

    Args:
        node_id: identifier used in logs and round summaries.
        window_size: readings per training window. Must match the detector.
        hidden: hidden width; must match every other node for averaging to work.
        learning_rate: Adam step size for local epochs.
        epochs: local epochs per federated round. Small on purpose -- many
            short local runs averaged often beats few long ones (they diverge).
        batch_size: local minibatch size.
        per_class_capacity: bounded buffer size per event type.
        min_samples: refuse to train below this many buffered windows.
        seed: makes local training reproducible.
    """

    def __init__(
        self,
        node_id: str = "node",
        window_size: int = DEFAULT_WINDOW,
        hidden: int = 64,
        learning_rate: float = 3e-3,
        epochs: int = 4,
        batch_size: int = 32,
        per_class_capacity: int = 300,
        min_samples: int = 40,
        seed: int = 0,
    ) -> None:
        self.node_id = node_id
        self.window_size = int(window_size)
        self.learning_rate = float(learning_rate)
        self.epochs = int(epochs)
        self.batch_size = int(batch_size)
        self.min_samples = int(min_samples)
        self.seed = int(seed)

        self.model = EventClassifier(window=self.window_size, hidden=hidden)
        self._criterion = nn.CrossEntropyLoss()
        self._rng = random.Random(seed)

        # Rolling raw readings, from which windows are cut.
        self._recent: deque[list[float]] = deque(maxlen=self.window_size)
        # One bounded buffer per class keeps the training set balanced.
        self._by_class: dict[int, deque[list[list[float]]]] = {
            event.index: deque(maxlen=per_class_capacity) for event in EventType.ordered()
        }

    # -- data accumulation -------------------------------------------------

    def observe(self, reading: Reading, label: EventType) -> bool:
        """Add one labelled reading. Returns True once it completed a window.

        In this simulation the label is the synthetic sensor's ground truth.
        On real hardware it would come from the detector's statistical stage,
        which is weak supervision -- the statistics teach the model, and the
        model then sharpens the statistics' event labels.
        """
        if not reading.is_complete:
            return False

        self._recent.append([float(reading.temperature_c), float(reading.humidity_pct)])
        if len(self._recent) < self.window_size:
            return False

        # The window's label is the label of its most recent reading, which is
        # the same convention `train.py` uses when it builds synthetic windows.
        self._by_class[label.index].append([list(point) for point in self._recent])
        return True

    def observe_stream(self, readings: Iterable[Reading]) -> int:
        """Feed many readings, labelling each from its `truth_label` metadata."""
        completed = 0
        for reading in readings:
            label_name = reading.metadata.get("truth_label", EventType.NONE.value)
            if self.observe(reading, EventType(label_name)):
                completed += 1
        return completed

    @property
    def buffered_samples(self) -> int:
        return sum(len(buffer) for buffer in self._by_class.values())

    @property
    def class_counts(self) -> dict[str, int]:
        return {
            event.value: len(self._by_class[event.index]) for event in EventType.ordered()
        }

    def ready(self) -> bool:
        """True when there is enough data, spanning enough classes, to train.

        Requiring at least two classes matters: cross-entropy on a single-class
        buffer just teaches the model to always answer that class.
        """
        populated = sum(1 for buffer in self._by_class.values() if buffer)
        return self.buffered_samples >= self.min_samples and populated >= 2

    def dataset(self) -> tuple[torch.Tensor, torch.Tensor]:
        """Materialise the buffered windows as tensors, shuffled."""
        windows: list[list[list[float]]] = []
        labels: list[int] = []
        for index, buffer in self._by_class.items():
            for window in buffer:
                windows.append(window)
                labels.append(index)

        if not windows:
            empty = torch.zeros((0, self.window_size, 2), dtype=torch.float32)
            return empty, torch.zeros((0,), dtype=torch.int64)

        order = list(range(len(windows)))
        self._rng.shuffle(order)
        return (
            torch.tensor([windows[i] for i in order], dtype=torch.float32),
            torch.tensor([labels[i] for i in order], dtype=torch.int64),
        )

    # -- weights -----------------------------------------------------------

    def get_weights(self) -> dict[str, torch.Tensor]:
        return clone_state_dict(self.model.state_dict())

    def set_weights(self, state: dict[str, torch.Tensor]) -> None:
        """Adopt the global model. Called at the start of every round."""
        self.model.load_state_dict(clone_state_dict(state))

    # -- training ----------------------------------------------------------

    def fit(self, epochs: int | None = None) -> TrainResult:
        """Run local epochs over the buffered data and return the new weights."""
        epochs = self.epochs if epochs is None else int(epochs)
        windows, labels = self.dataset()

        if windows.shape[0] == 0:
            return TrainResult(self.node_id, 0, 0.0, 0.0, 0, self.get_weights())

        # No global torch seeding here on purpose: nodes fit concurrently in
        # worker threads, and `torch.manual_seed` is process-global. Local
        # determinism comes from `self._rng` (which orders the data) and from
        # the fact that nothing in this model's forward pass is stochastic.
        optimiser = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)

        self.model.train()
        final_loss = 0.0
        for _ in range(epochs):
            epoch_loss = 0.0
            batches = 0
            for start in range(0, windows.shape[0], self.batch_size):
                batch_x = windows[start : start + self.batch_size]
                batch_y = labels[start : start + self.batch_size]

                optimiser.zero_grad()
                loss = self._criterion(self.model(batch_x), batch_y)
                loss.backward()
                optimiser.step()

                epoch_loss += float(loss.item())
                batches += 1
            final_loss = epoch_loss / max(batches, 1)

        accuracy = self.evaluate(windows, labels)[1]
        log.debug(
            "%s: local fit on %d windows -> loss %.4f, accuracy %.3f",
            self.node_id,
            windows.shape[0],
            final_loss,
            accuracy,
        )
        return TrainResult(
            node_id=self.node_id,
            num_samples=int(windows.shape[0]),
            loss=final_loss,
            accuracy=accuracy,
            epochs=epochs,
            state_dict=self.get_weights(),
        )

    @torch.no_grad()
    def evaluate(
        self, windows: torch.Tensor, labels: torch.Tensor
    ) -> tuple[float, float]:
        """Return (mean loss, accuracy) for the given data under current weights."""
        if windows.shape[0] == 0:
            return 0.0, 0.0
        self.model.eval()
        logits = self.model(windows)
        loss = float(self._criterion(logits, labels).item())
        accuracy = float((logits.argmax(dim=1) == labels).float().mean().item())
        return loss, accuracy
