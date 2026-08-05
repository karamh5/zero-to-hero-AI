"""YAML config loading with dotted-path access.

Small on purpose. Everything downstream reads config through `Config.get`,
which takes a dotted path and a default, so a missing key is never a crash.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

# config.yaml lives at the project root, one level above this file's package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class Config:
    """Read-only view over the parsed config tree."""

    def __init__(self, data: dict[str, Any], path: Path | None = None) -> None:
        self._data = data or {}
        self.path = path

    def get(self, dotted: str, default: Any = None) -> Any:
        """Fetch `a.b.c`, returning `default` if any link is missing."""
        node: Any = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def section(self, dotted: str) -> dict[str, Any]:
        """Fetch a dict subtree, always returning a (deep) copy.

        Copying matters: these dicts are handed to pack constructors as
        `**options`, and packs must not be able to mutate shared config state.
        """
        value = self.get(dotted, {})
        return copy.deepcopy(value) if isinstance(value, dict) else {}

    def pack_options(self, kind: str) -> tuple[str, dict[str, Any]]:
        """Return (active pack name, its options) for 'sensor' or 'detector'."""
        active = self.get(f"{kind}.active")
        if not active:
            raise ValueError(f"config is missing required key '{kind}.active'")
        return active, self.section(f"{kind}.packs.{active}")

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Config(path={self.path}, keys={sorted(self._data)})"


def load_config(path: str | os.PathLike[str] | None = None) -> Config:
    """Load config.yaml. Falls back to the project-root default."""
    resolved = Path(path) if path else DEFAULT_CONFIG_PATH
    if not resolved.exists():
        raise FileNotFoundError(f"config file not found: {resolved}")
    with resolved.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config file {resolved} must contain a YAML mapping")
    return Config(data, resolved)
