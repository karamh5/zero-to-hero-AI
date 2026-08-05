"""Detector packs.

Like sensors, detectors register themselves by name and are built from
`config.yaml`. `baseline.py` and `model.py` are the reusable pieces a future
detector pack can build on without reimplementing the statistics.
"""

from detectors.base import BaseDetector
from detectors.baseline import EwmaBaseline

__all__ = ["BaseDetector", "EwmaBaseline"]
