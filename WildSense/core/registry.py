"""Plugin registry -- the mechanism that makes WildSense modular for real.

A sensor or detector announces itself with a decorator:

    @register_sensor("dht22")
    class DHT22Sensor(BaseSensor):
        ...

`config.yaml` then names that key, and the pipeline builds the object by key.
The pipeline never imports `DHT22Sensor` (or any other pack) directly, so
adding a thermal-camera pack is:

    1. write `sensors/thermal.py` with `@register_sensor("thermal")`
    2. add its module path to `packs.discover` in config.yaml
    3. set `sensor.active: thermal`

No core file changes. That is the whole point.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, TypeVar

log = logging.getLogger(__name__)

# Registries are plain dicts keyed by the config-facing name.
_SENSORS: dict[str, type] = {}
_DETECTORS: dict[str, type] = {}

T = TypeVar("T", bound=type)


class RegistryError(KeyError):
    """Raised when config names a pack that was never registered."""


def _make_decorator(registry: dict[str, type], kind: str) -> Callable[[str], Callable[[T], T]]:
    def decorator(name: str) -> Callable[[T], T]:
        def wrap(cls: T) -> T:
            if name in registry and registry[name] is not cls:
                raise RegistryError(f"{kind} '{name}' is already registered")
            registry[name] = cls
            log.debug("Registered %s pack '%s' -> %s", kind, name, cls.__name__)
            return cls

        return wrap

    return decorator


register_sensor = _make_decorator(_SENSORS, "sensor")
register_detector = _make_decorator(_DETECTORS, "detector")


def _build(registry: dict[str, type], kind: str, name: str, options: dict[str, Any] | None):
    if name not in registry:
        available = ", ".join(sorted(registry)) or "<none>"
        raise RegistryError(
            f"No {kind} pack registered under '{name}'. Available: {available}. "
            f"Did you forget to list its module in `packs.discover` in config.yaml?"
        )
    return registry[name](**(options or {}))


def create_sensor(name: str, options: dict[str, Any] | None = None):
    """Instantiate a registered sensor pack by its config name."""
    return _build(_SENSORS, "sensor", name, options)


def create_detector(name: str, options: dict[str, Any] | None = None):
    """Instantiate a registered detector pack by its config name."""
    return _build(_DETECTORS, "detector", name, options)


def available_sensors() -> list[str]:
    return sorted(_SENSORS)


def available_detectors() -> list[str]:
    return sorted(_DETECTORS)


def discover(module_paths: list[str]) -> None:
    """Import pack modules so their decorators run.

    Import failures are logged and skipped rather than raised. This is what
    lets a dev machine load the config that lists `sensors.dht22` without
    having the Raspberry Pi GPIO libraries installed -- the DHT22 pack simply
    is not available, and config that asks for it will fail with a clear
    RegistryError instead of an ImportError traceback at startup.
    """
    for path in module_paths:
        try:
            importlib.import_module(path)
        except Exception as exc:  # noqa: BLE001 - intentionally broad
            log.warning("Pack module '%s' could not be imported (%s)", path, exc)
