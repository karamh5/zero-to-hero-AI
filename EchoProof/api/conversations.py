"""The prepared conversation library.

Conversations are pack data, exactly like policy, scenario and persona packs:
`packs/conversation/<pack_id>/conversations.jsonl`. Each carries role-labelled
turns, so the engine can enforce that only agent turns are adjudicated.

`verified.json` beside them records what each conversation ACTUALLY produced
when it was last run through the real pipeline. The UI shows that recorded
outcome rather than the authored intent, and flags any conversation whose
observed outcome differs from what it was written to demonstrate. A prepared
library that promises outcomes it does not produce would be worse than having
none, because the one place it failed would be in front of an audience.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import PACKS_DIR

CONVERSATION_DIR = PACKS_DIR / "conversation"

# Presentation order for the verdict groups. Decisions first, then the
# abstentions in the order the thresholds produce them.
CATEGORY_ORDER = [
    "supported",
    "contradicted",
    "no_governing_rule",
    "retrieval_below_confidence",
    "conflicting_sections",
]

CATEGORY_LABEL = {
    "supported": "Supported",
    "contradicted": "Contradicted",
    "no_governing_rule": "No governing rule",
    "retrieval_below_confidence": "Retrieval below confidence",
    "conflicting_sections": "Conflicting sections",
}


def available_packs() -> list[str]:
    if not CONVERSATION_DIR.exists():
        return []
    return sorted(
        path.name
        for path in CONVERSATION_DIR.iterdir()
        if (path / "conversations.jsonl").exists()
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_pack(pack_id: str) -> list[dict[str, Any]]:
    path = CONVERSATION_DIR / pack_id / "conversations.jsonl"
    if not path.exists():
        return []
    return _read_jsonl(path)


def load_verified(pack_id: str) -> dict[str, Any]:
    path = CONVERSATION_DIR / pack_id / "verified.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get(pack_id: str, conversation_id: str) -> dict[str, Any] | None:
    for entry in load_pack(pack_id):
        if entry.get("conversation_id") == conversation_id:
            return entry
    return None


def describe(pack_id: str) -> dict[str, Any]:
    """One pack's conversations, grouped by their recorded outcome."""
    entries = load_pack(pack_id)
    verified = load_verified(pack_id)

    items: list[dict[str, Any]] = []
    for entry in entries:
        record = verified.get(entry["conversation_id"])
        turns = entry.get("turns", [])
        items.append(
            {
                "conversation_id": entry["conversation_id"],
                "title": entry.get("title", entry["conversation_id"]),
                "summary": entry.get("summary", ""),
                "authored_category": entry.get("category"),
                "turns": turns,
                "agent_turns": sum(
                    1 for t in turns if str(t.get("role", "")).lower() != "customer"
                ),
                "customer_turns": sum(
                    1 for t in turns if str(t.get("role", "")).lower() == "customer"
                ),
                "has_deterministic": bool(entry.get("deterministic")),
                # Everything below is the recorded result of really running it.
                "verified": record is not None,
                "observed_outcome": record.get("observed_headline") if record else None,
                "verdict_counts": record.get("verdict_counts", {}) if record else {},
                "findings": record.get("findings", []) if record else [],
                "claims": record.get("claims") if record else None,
                "verified_at": record.get("verified_at") if record else None,
                "run_id": record.get("run_id") if record else None,
                "matches_authored": record.get("matches_authored") if record else None,
            }
        )

    # Group by what was recorded, falling back to the authored category for
    # anything not yet verified, and say which is which.
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = item["observed_outcome"] or item["authored_category"] or "unverified"
        groups.setdefault(key, []).append(item)

    ordered = [
        {
            "category": category,
            "label": CATEGORY_LABEL.get(category, category.replace("_", " ")),
            "conversations": groups[category],
        }
        for category in CATEGORY_ORDER
        if category in groups
    ]
    for category in sorted(groups):
        if category not in CATEGORY_ORDER:
            ordered.append(
                {
                    "category": category,
                    "label": CATEGORY_LABEL.get(category, category.replace("_", " ")),
                    "conversations": groups[category],
                }
            )

    return {
        "pack_id": pack_id,
        "count": len(items),
        "verified_count": sum(1 for item in items if item["verified"]),
        "groups": ordered,
    }
