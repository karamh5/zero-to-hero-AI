"""Sensor packs.

Each pack registers itself with `core.registry` under a config-facing name.
Packs are imported through `registry.discover()` driven by `config.yaml`, not
by importing them here -- that is what keeps hardware-only packs from breaking
a dev machine at import time.
"""

from sensors.base import BaseSensor, SensorError, SensorReadError

__all__ = ["BaseSensor", "SensorError", "SensorReadError"]
