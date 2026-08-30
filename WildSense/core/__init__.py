"""WildSense core: data contracts, config loading, and the pack registry.

Nothing in `core` imports a sensor or detector implementation. The dependency
arrow points inward only.
"""

from core.contracts import Event, EventType, Reading, utc_iso
from core.config import Config, load_config

__all__ = ["Event", "EventType", "Reading", "utc_iso", "Config", "load_config"]
