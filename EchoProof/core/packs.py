"""Loading data packs from disk.

The engine reads packs through this module and never reaches into pack layout
itself. That keeps the swap in Phase 6 to a directory name.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.config import CRITERIA_DIR, PACKS_DIR, POLICY_DIR
from core.contracts import PolicySection


class PackError(RuntimeError):
    """Raised when a pack is missing or malformed."""


@dataclass(frozen=True)
class PolicyPack:
    """A loaded policy corpus plus the provenance that pins it."""

    pack_id: str
    sections: list[PolicySection]
    manifest: dict[str, Any]

    @property
    def version(self) -> str:
        """The hash every finding records as policy_pack_version."""
        return self.manifest["policy_pack_version"]

    @property
    def citation(self) -> str:
        return self.manifest.get("citation", self.pack_id)

    @property
    def hierarchy_separators(self) -> tuple[str, ...]:
        """Characters separating hierarchy levels in this corpus's identifiers.

        Pack data, because it describes the client's drafting conventions.
        Regulation F nests with parentheses; a corpus numbered CC-3.4.2 nests
        with dots. The engine reads this instead of assuming either.
        """
        scheme = self.manifest.get("section_id_scheme") or {}
        separators = scheme.get("hierarchy_separators")
        if isinstance(separators, list) and separators:
            return tuple(str(s) for s in separators)
        return ("(", "#")

    def by_id(self, section_id: str) -> PolicySection | None:
        return self._index.get(section_id)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "_index", {s.section_id: s for s in self.sections}
        )


def load_policy_pack(pack_id: str = "reg_f") -> PolicyPack:
    """Read a policy pack and its manifest."""
    directory = POLICY_DIR / pack_id
    sections_path = directory / "sections.jsonl"
    manifest_path = directory / "manifest.json"

    if not sections_path.exists() or not manifest_path.exists():
        raise PackError(
            f"policy pack '{pack_id}' is not built. Expected {sections_path} and "
            f"{manifest_path}. Run scripts/build_policy_pack_ecfr.py first."
        )

    sections = [
        PolicySection.from_dict(json.loads(line))
        for line in sections_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not sections:
        raise PackError(f"policy pack '{pack_id}' contains no sections")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return PolicyPack(pack_id=pack_id, sections=sections, manifest=manifest)


def load_jsonl_pack(kind: str, pack_id: str, filename: str) -> list[dict[str, Any]]:
    """Load a scenario or persona pack.

    Generic on purpose. Adding a vertical means adding pack files under a new
    directory, never editing this function, which is the engine/pack boundary
    CLAUDE.md requires.
    """
    path = PACKS_DIR / kind / pack_id / filename
    if not path.exists():
        raise PackError(f"{kind} pack '{pack_id}' not found at {path}")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise PackError(f"{kind} pack '{pack_id}' is empty")
    return rows


def load_scenarios(pack_id: str = "collections") -> list[dict[str, Any]]:
    return load_jsonl_pack("scenario", pack_id, "scenarios.jsonl")


def load_personas(pack_id: str = "collections") -> dict[str, dict[str, Any]]:
    return {
        p["persona_id"]: p
        for p in load_jsonl_pack("persona", pack_id, "personas.jsonl")
    }


def policy_index_dir(pack_id: str = "reg_f") -> Path:
    """Where the retriever caches vectors for this pack. Git-ignored."""
    return POLICY_DIR / pack_id / "index"


def load_criteria(name: str = "thresholds") -> dict[str, Any]:
    """Read a criteria pack file."""
    path = CRITERIA_DIR / f"{name}.json"
    if not path.exists():
        raise PackError(
            f"criteria file {path} is missing. Run scripts/eval_retrieval.py to "
            "calibrate and write it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def save_criteria(name: str, payload: dict[str, Any]) -> Path:
    """Write a criteria pack file."""
    CRITERIA_DIR.mkdir(parents=True, exist_ok=True)
    path = CRITERIA_DIR / f"{name}.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
