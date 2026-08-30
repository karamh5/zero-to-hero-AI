"""Federated learning: local training on-node, weight averaging across nodes.

Readings never leave a node. Only weights move.
"""

from federation.averager import FederatedAverager, NodeUpdate, weighted_average
from federation.local_trainer import LocalTrainer, TrainResult
from federation.simulation import (
    DEFAULT_NODE_SPECS,
    FederatedNode,
    FederationSimulation,
    NodeSpec,
    RoundResult,
)

__all__ = [
    "FederatedAverager",
    "NodeUpdate",
    "weighted_average",
    "LocalTrainer",
    "TrainResult",
    "FederationSimulation",
    "FederatedNode",
    "NodeSpec",
    "RoundResult",
    "DEFAULT_NODE_SPECS",
]
