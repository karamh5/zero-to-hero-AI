"""The one canonical hashing function in EchoProof.

Everything that needs an identity uses this module: the policy corpus document
hash, prompt hashes, content-addressed evidence artifacts, and the evidence
chain itself. Having exactly one implementation is the point. Two subtly
different JSON serialisers would produce two different hashes for the same
logical input, and SPEC section 7 defines reproducibility as "same stored
inputs regenerate the same verdict, verified by recomputed hash". That property
is only worth anything if the hash is computed the same way everywhere.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Bump only if the serialisation rules below change. Every stored hash becomes
# incomparable across a bump, which is exactly why it is recorded alongside
# them rather than left implicit.
HASH_SCHEME = "sha256/canonical-json/v1"


def canonical_json(value: Any) -> str:
    """Serialise to JSON in a form that is stable across runs and machines.

    `sort_keys` removes dict ordering as a source of hash drift. The compact
    separators remove whitespace. `ensure_ascii` removes any dependence on the
    filesystem or console encoding, which matters because the policy corpus
    contains section symbols and typographic quotes.
    """
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        default=_fallback,
    )


def _fallback(obj: Any) -> Any:
    """Serialise the few non-JSON types that legitimately reach the hasher."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "value"):  # str-backed enums
        return obj.value
    raise TypeError(f"canonical_json cannot serialise {type(obj).__name__}")


def hash_text(text: str) -> str:
    """Hash a raw string. Used for prompts and verbatim policy text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_object(value: Any) -> str:
    """Hash any JSON-serialisable object through the canonical form."""
    return hash_text(canonical_json(value))


def chain_hash(previous_hash: str, entry: Any) -> str:
    """Compute an evidence-chain hash.

    Entry N's hash covers entry N-1's hash, which is what makes the log
    tamper-evident: editing any earlier entry invalidates every hash after it.
    The genesis entry passes an empty string as `previous_hash`.
    """
    return hash_text(previous_hash + "\n" + canonical_json(entry))


def short(digest: str, length: int = 12) -> str:
    """Truncate a digest for display. Never use this for comparison."""
    return digest[:length]
