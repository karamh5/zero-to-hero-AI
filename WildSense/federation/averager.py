"""FederatedAverager -- the FedAvg server side.

Implements sample-count-weighted averaging (McMahan et al., 2017):

    w_global = sum_k (n_k / n_total) * w_k

Weighting by `n_k` is not cosmetic. A node that has seen 500 windows should
count for more than one that has seen 40, otherwise a barely-trained node
drags the global model backwards every round.

Thread safety is real here, not decorative: nodes submit concurrently from
worker threads while the coordinator may be reading the current global
weights, so all shared state sits behind one lock.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

import torch

from federation.local_trainer import clone_state_dict

log = logging.getLogger(__name__)


@dataclass
class NodeUpdate:
    """One node's contribution to a round."""

    node_id: str
    num_samples: int
    loss: float
    state_dict: dict[str, torch.Tensor] = field(repr=False, default_factory=dict)


def weighted_average(updates: list[NodeUpdate]) -> dict[str, torch.Tensor]:
    """Sample-count-weighted mean of the submitted state dicts.

    Raises:
        ValueError: if there are no updates, if the total sample count is zero,
            or if the submitted models do not share an identical parameter set
            (which would silently produce a nonsense model).
    """
    if not updates:
        raise ValueError("cannot average zero updates")

    total = sum(update.num_samples for update in updates)
    if total <= 0:
        raise ValueError("cannot average updates with zero total samples")

    reference_keys = set(updates[0].state_dict)
    for update in updates[1:]:
        if set(update.state_dict) != reference_keys:
            raise ValueError(
                f"node '{update.node_id}' submitted a model with a different "
                "architecture than its peers"
            )

    averaged: dict[str, torch.Tensor] = {}
    for key in updates[0].state_dict:
        accumulator = torch.zeros_like(updates[0].state_dict[key], dtype=torch.float32)
        for update in updates:
            weight = update.num_samples / total
            accumulator += update.state_dict[key].to(torch.float32) * weight
        averaged[key] = accumulator.to(updates[0].state_dict[key].dtype)
    return averaged


class FederatedAverager:
    """Collects node updates and merges them into a global model.

    Usage per round:
        averager.submit(...)  x N   (from node threads, concurrently)
        averager.aggregate()        (from the coordinator)

    `aggregate()` clears the pending updates, so rounds cannot bleed together.
    """

    def __init__(self, min_updates: int = 2) -> None:
        self.min_updates = max(1, int(min_updates))
        self._lock = threading.Lock()
        self._pending: list[NodeUpdate] = []
        self._global: dict[str, torch.Tensor] | None = None
        self._round = 0
        self._history: list[dict] = []

    # -- node side ---------------------------------------------------------

    def submit(
        self,
        node_id: str,
        state_dict: dict[str, torch.Tensor],
        num_samples: int,
        loss: float = 0.0,
    ) -> None:
        """Register one node's weights for the current round. Thread-safe."""
        update = NodeUpdate(
            node_id=node_id,
            num_samples=int(num_samples),
            loss=float(loss),
            state_dict=clone_state_dict(state_dict),
        )
        with self._lock:
            self._pending.append(update)

    # -- coordinator side --------------------------------------------------

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    @property
    def round_number(self) -> int:
        with self._lock:
            return self._round

    @property
    def history(self) -> list[dict]:
        with self._lock:
            return list(self._history)

    def global_weights(self) -> dict[str, torch.Tensor] | None:
        """A copy of the current global model, or None before the first round."""
        with self._lock:
            return clone_state_dict(self._global) if self._global is not None else None

    def seed(self, state_dict: dict[str, torch.Tensor]) -> None:
        """Install starting weights without counting it as a round.

        Federation that begins from random initialisation spends its first
        rounds worse than an already-trained model, so seeding from a
        pre-trained artifact means round 1 refines a good model rather than
        replacing it with a bad one. This mirrors a real deployment: ship
        nodes with trained weights, then fine-tune federatively in the field.
        """
        with self._lock:
            self._global = clone_state_dict(state_dict)

    def aggregate(self) -> dict[str, torch.Tensor] | None:
        """Merge the pending updates into a new global model.

        Returns None (and keeps the updates pending) when fewer than
        `min_updates` nodes have reported -- a straggler should delay a round,
        not silently produce a single-node "average".
        """
        with self._lock:
            if len(self._pending) < self.min_updates:
                log.debug(
                    "Aggregation deferred: %d/%d updates present",
                    len(self._pending),
                    self.min_updates,
                )
                return None
            updates, self._pending = self._pending, []

        averaged = weighted_average(updates)

        with self._lock:
            self._global = averaged
            self._round += 1
            entry = {
                "round": self._round,
                "nodes": [update.node_id for update in updates],
                "total_samples": sum(update.num_samples for update in updates),
                "mean_local_loss": round(
                    sum(update.loss for update in updates) / len(updates), 5
                ),
            }
            self._history.append(entry)
            round_number = self._round

        log.info(
            "Federated round %d complete: %d nodes, %d samples, mean local loss %.4f",
            round_number,
            len(updates),
            entry["total_samples"],
            entry["mean_local_loss"],
        )
        return clone_state_dict(averaged)

    def reset(self) -> None:
        with self._lock:
            self._pending.clear()
            self._global = None
            self._round = 0
            self._history.clear()
